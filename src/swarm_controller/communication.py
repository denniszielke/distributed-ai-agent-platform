"""Communication layer using Azure Storage Queues and Blob containers."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueClient, QueueServiceClient

from .models import SwarmMessage

logger = logging.getLogger(__name__)

QUEUE_CONTROLLER_INBOX = "swarm-controller-inbox"
QUEUE_AGGREGATOR_INBOX = "swarm-aggregator-inbox"
BLOB_CONTAINER_SHARED = "swarm-shared-files"


class CommunicationLayer:
    """Azure Storage backed communication between agents and the controller."""

    def __init__(
        self,
        storage_connection_string: Optional[str] = None,
        storage_account_url: Optional[str] = None,
    ) -> None:
        conn_str = storage_connection_string or os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        account_url = storage_account_url or os.environ.get("AZURE_STORAGE_ACCOUNT_URL")

        if conn_str:
            self._queue_service = QueueServiceClient.from_connection_string(conn_str)
            self._blob_service = BlobServiceClient.from_connection_string(conn_str)
        elif account_url:
            credential = DefaultAzureCredential()
            self._queue_service = QueueServiceClient(account_url=account_url, credential=credential)
            self._blob_service = BlobServiceClient(account_url=account_url, credential=credential)
        else:
            logger.warning(
                "No Azure Storage connection configured. "
                "Set AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_URL."
            )
            self._queue_service = None  # type: ignore[assignment]
            self._blob_service = None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Queue operations
    # ------------------------------------------------------------------

    def ensure_queues(self) -> None:
        """Create the required queues if they do not exist."""
        if self._queue_service is None:
            return
        for q in (QUEUE_CONTROLLER_INBOX, QUEUE_AGGREGATOR_INBOX):
            try:
                self._queue_service.create_queue(q)
                logger.info("Created queue %s", q)
            except Exception:
                logger.debug("Queue %s already exists", q)

    def send_message(self, queue_name: str, message: SwarmMessage) -> None:
        if self._queue_service is None:
            logger.warning("Storage not configured – message not sent")
            return
        client: QueueClient = self._queue_service.get_queue_client(queue_name)
        client.send_message(message.model_dump_json())
        logger.info("Sent message %s to queue %s", message.id, queue_name)

    def receive_messages(self, queue_name: str, max_messages: int = 10) -> list[SwarmMessage]:
        if self._queue_service is None:
            return []
        client: QueueClient = self._queue_service.get_queue_client(queue_name)
        raw = client.receive_messages(max_messages=max_messages, visibility_timeout=30)
        messages: list[SwarmMessage] = []
        for msg in raw:
            try:
                parsed = SwarmMessage.model_validate_json(msg.content)
                messages.append(parsed)
                client.delete_message(msg)
            except Exception:
                logger.exception("Failed to parse queue message")
        return messages

    def send_to_controller(self, message: SwarmMessage) -> None:
        self.send_message(QUEUE_CONTROLLER_INBOX, message)

    def send_to_aggregator(self, message: SwarmMessage) -> None:
        self.send_message(QUEUE_AGGREGATOR_INBOX, message)

    # ------------------------------------------------------------------
    # Blob operations
    # ------------------------------------------------------------------

    def ensure_blob_container(self) -> None:
        if self._blob_service is None:
            return
        try:
            self._blob_service.create_container(BLOB_CONTAINER_SHARED)
            logger.info("Created blob container %s", BLOB_CONTAINER_SHARED)
        except Exception:
            logger.debug("Blob container %s already exists", BLOB_CONTAINER_SHARED)

    def upload_blob(self, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        if self._blob_service is None:
            logger.warning("Storage not configured – blob not uploaded")
            return ""
        container = self._blob_service.get_container_client(BLOB_CONTAINER_SHARED)
        blob = container.get_blob_client(blob_name)
        blob.upload_blob(data, overwrite=True, content_settings={"content_type": content_type})
        logger.info("Uploaded blob %s", blob_name)
        return blob.url

    def download_blob(self, blob_name: str) -> bytes:
        if self._blob_service is None:
            return b""
        container = self._blob_service.get_container_client(BLOB_CONTAINER_SHARED)
        blob = container.get_blob_client(blob_name)
        return blob.download_blob().readall()
