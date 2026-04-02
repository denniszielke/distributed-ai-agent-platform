"""AI Search integration for storing and retrieving agent execution plans."""

from __future__ import annotations

import logging
import os
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

INDEX_NAME = "agent-execution-plans"
EMBEDDING_DIMENSIONS = 1536


class ExecutionPlanSearchStore:
    """Azure AI Search backed store for agent execution plans."""

    def __init__(
        self,
        search_endpoint: Optional[str] = None,
        search_key: Optional[str] = None,
        openai_endpoint: Optional[str] = None,
        openai_key: Optional[str] = None,
        embedding_deployment: Optional[str] = None,
    ) -> None:
        self._search_endpoint = search_endpoint or os.environ.get("AZURE_AI_SEARCH_ENDPOINT", "")
        self._search_key = search_key or os.environ.get("AZURE_AI_SEARCH_KEY", "")
        self._openai_endpoint = openai_endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        self._openai_key = openai_key or os.environ.get("AZURE_OPENAI_API_KEY", "")
        self._embedding_deployment = embedding_deployment or os.environ.get(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002"
        )

        if self._search_endpoint and self._search_key:
            credential = AzureKeyCredential(self._search_key)
            self._index_client = SearchIndexClient(
                endpoint=self._search_endpoint, credential=credential
            )
            self._search_client = SearchClient(
                endpoint=self._search_endpoint,
                index_name=INDEX_NAME,
                credential=credential,
            )
        else:
            logger.warning("AI Search not configured")
            self._index_client = None  # type: ignore[assignment]
            self._search_client = None  # type: ignore[assignment]

        if self._openai_endpoint and self._openai_key:
            self._openai = AzureOpenAI(
                azure_endpoint=self._openai_endpoint,
                api_key=self._openai_key,
                api_version=os.environ.get("AZURE_OPENAI_VERSION", "2024-02-01"),
            )
        else:
            self._openai = None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def create_index(self) -> None:
        """Create the AI Search index with the correct schema."""
        if self._index_client is None:
            return

        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SearchableField(name="query", type=SearchFieldDataType.String),
            SearchableField(name="description", type=SearchFieldDataType.String),
            SearchableField(name="intent", type=SearchFieldDataType.String),
            SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="complexity", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="score", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
            SearchField(
                name="query_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=EMBEDDING_DIMENSIONS,
                vector_search_profile_name="default-vector-profile",
            ),
        ]

        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="default-vector-profile",
                    algorithm_configuration_name="default-hnsw",
                ),
            ],
            algorithms=[
                HnswAlgorithmConfiguration(name="default-hnsw"),
            ],
        )

        index = SearchIndex(
            name=INDEX_NAME,
            fields=fields,
            vector_search=vector_search,
        )

        self._index_client.create_or_update_index(index)
        logger.info("Created/updated index %s", INDEX_NAME)

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def _get_embedding(self, text: str) -> list[float]:
        if self._openai is None:
            return [0.0] * EMBEDDING_DIMENSIONS
        response = self._openai.embeddings.create(
            input=text,
            model=self._embedding_deployment,
        )
        return response.data[0].embedding

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def upsert_plan(self, plan: dict) -> None:
        """Insert or update an execution plan in the index."""
        if self._search_client is None:
            return
        doc = dict(plan)
        doc["query_vector"] = self._get_embedding(doc.get("query", ""))
        self._search_client.upload_documents(documents=[doc])
        logger.info("Upserted execution plan %s", doc.get("id"))

    def search_similar_plans(self, query: str, top: int = 5) -> list[dict]:
        """Search for execution plans similar to the given query."""
        if self._search_client is None:
            return []

        vector = self._get_embedding(query)
        vector_query = VectorizedQuery(
            vector=vector,
            k_nearest_neighbors=top,
            fields="query_vector",
        )

        results = self._search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            top=top,
        )

        plans: list[dict] = []
        for r in results:
            plans.append(
                {
                    "id": r["id"],
                    "query": r["query"],
                    "description": r["description"],
                    "intent": r["intent"],
                    "category": r.get("category"),
                    "complexity": r.get("complexity"),
                    "score": r.get("score"),
                }
            )
        return plans
