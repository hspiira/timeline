"""Gmail provider using Gmail API with batch and history support."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.infrastructure.external.email.protocols import EmailMessage, EmailProviderConfig
from app.shared.telemetry.logging import get_logger
from app.shared.utils.datetime import from_timestamp_ms_utc

logger = get_logger(__name__)

BATCH_SIZE = 100
DEFAULT_MAX_MESSAGES = 10000


class HistoryChangeType(str, Enum):
    """Types of changes from Gmail History API."""

    MESSAGE_ADDED = "messageAdded"
    MESSAGE_DELETED = "messageDeleted"
    LABELS_ADDED = "labelsAdded"
    LABELS_REMOVED = "labelsRemoved"


@dataclass
class HistoryChange:
    """A change from Gmail History API."""

    change_type: HistoryChangeType
    message_id: str
    gmail_id: str
    thread_id: str | None = None
    labels: list[str] | None = None
    message: EmailMessage | None = None


class HistoryExpiredError(Exception):
    """Raised when Gmail history ID has expired (410)."""


class GmailProvider:
    """Gmail provider using Gmail API with batch and history."""

    def __init__(self) -> None:
        self._service: Any = None
        self._config: EmailProviderConfig | None = None

    async def connect(self, config: EmailProviderConfig) -> None:
        """Connect to Gmail API using OAuth credentials."""
        self._config = config
        creds = Credentials(
            token=config.credentials.get("access_token"),
            refresh_token=config.credentials.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config.credentials.get("client_id"),
            client_secret=config.credentials.get("client_secret"),
        )
        self._service = await asyncio.to_thread(
            build, "gmail", "v1", credentials=creds
        )
        logger.info("Connected to Gmail API: %s", config.email_address)

    async def disconnect(self) -> None:
        """Disconnect from Gmail API."""
        self._service = None
        logger.info("Disconnected from Gmail API")

    async def fetch_messages(
        self,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[EmailMessage]:
        """Fetch messages with pagination and batch get."""
        if not self._service:
            raise RuntimeError("Not connected to Gmail API")
        effective_limit = limit if limit is not None else DEFAULT_MAX_MESSAGES
        query = ""
        if since:
            query = f"after:{int(since.timestamp())}"
        all_message_ids: list[str] = []
        page_token: str | None = None
        while True:
            request = self._service.users().messages().list(
                userId="me",
                q=query,
                maxResults=500,
                pageToken=page_token,
            )
            results = await asyncio.to_thread(request.execute)
            message_ids = [m["id"] for m in results.get("messages", [])]
            remaining = effective_limit - len(all_message_ids)
            all_message_ids.extend(message_ids[:remaining])
            if len(all_message_ids) >= effective_limit:
                break
            page_token = results.get("nextPageToken")
            if not page_token:
                break
        messages = await self._fetch_messages_batch(all_message_ids)
        logger.info("Fetched %s messages from Gmail", len(messages))
        return messages

    async def _fetch_messages_batch(self, message_ids: list[str]) -> list[EmailMessage]:
        """Fetch multiple messages via batch API."""
        if not message_ids:
            return []
        messages = []
        for batch_start in range(0, len(message_ids), BATCH_SIZE):
            batch_ids = message_ids[batch_start : batch_start + BATCH_SIZE]
            batch_results: dict[str, dict] = {}

            def add_callback(msg_id: str):
                def cb(
                    request_id: str,
                    response: dict[str, Any],
                    exception: Exception | None,
                ) -> None:
                    if exception:
                        logger.warning("Gmail batch item %s: %s", msg_id, exception)
                    else:
                        batch_results[msg_id] = response

                return cb

            batch = self._service.new_batch_http_request()
            for msg_id in batch_ids:
                batch.add(
                    self._service.users().messages().get(
                        userId="me", id=msg_id, format="full"
                    ),
                    callback=add_callback(msg_id),
                )
            await asyncio.to_thread(batch.execute)
            for msg_id in batch_ids:
                if msg_id in batch_results:
                    try:
                        parsed = self._parse_message(batch_results[msg_id], msg_id)
                        if parsed:
                            messages.append(parsed)
                    except Exception as e:
                        logger.warning("Parse message %s: %s", msg_id, e)
        return messages

    def _parse_message(self, msg: dict[str, Any], msg_id: str) -> EmailMessage | None:
        """Parse Gmail API message into EmailMessage."""
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        timestamp = from_timestamp_ms_utc(int(msg["internalDate"]))
        label_ids = msg.get("labelIds", [])
        return EmailMessage(
            message_id=headers.get("Message-ID", msg_id),
            thread_id=msg.get("threadId"),
            from_address=headers.get("From", ""),
            to_addresses=[
                a.strip() for a in headers.get("To", "").split(",")
            ],
            subject=headers.get("Subject", ""),
            timestamp=timestamp,
            labels=label_ids,
            is_read="UNREAD" not in label_ids,
            is_starred="STARRED" in label_ids,
            has_attachments=any(
                p.get("filename") for p in msg["payload"].get("parts", [])
            ),
            provider_metadata={
                "gmail_id": msg_id,
                "thread_id": msg.get("threadId"),
                "label_ids": label_ids,
            },
        )

    async def setup_webhook(self, callback_url: str) -> dict[str, Any]:
        """Setup Gmail push (watch). callback_url used as topicName."""
        if not self._service:
            raise RuntimeError("Not connected to Gmail API")
        body = {"labelIds": ["INBOX"], "topicName": callback_url}
        request = self._service.users().watch(userId="me", body=body)
        response = await asyncio.to_thread(request.execute)
        logger.info("Gmail webhook setup: %s", response)
        return response

    async def remove_webhook(self) -> None:
        """Stop Gmail watch."""
        if not self._service:
            return
        request = self._service.users().stop(userId="me")
        await asyncio.to_thread(request.execute)
        logger.info("Gmail webhook removed")

    @property
    def supports_webhooks(self) -> bool:
        return True

    @property
    def supports_incremental_sync(self) -> bool:
        return True

    async def get_current_history_id(self) -> str:
        """Return current history ID from profile (for incremental sync)."""
        if not self._service:
            raise RuntimeError("Not connected to Gmail API")
        request = self._service.users().getProfile(userId="me")
        profile = await asyncio.to_thread(request.execute)
        history_id = profile.get("historyId")
        if not history_id:
            raise RuntimeError("Gmail profile did not return historyId")
        return str(history_id)

    async def fetch_history_changes(
        self,
        start_history_id: str,
        history_types: list[str] | None = None,
    ) -> tuple[list[HistoryChange], str]:
        """Fetch changes since history ID. Returns (changes, new_history_id).

        Raises:
            HistoryExpiredError: If history ID expired (410).
        """
        if not self._service:
            raise RuntimeError("Not connected to Gmail API")
        if history_types is None:
            history_types = ["messageAdded", "messageDeleted"]
        changes: list[HistoryChange] = []
        new_history_id = start_history_id
        page_token: str | None = None
        try:
            while True:
                params: dict[str, Any] = {
                    "userId": "me",
                    "startHistoryId": start_history_id,
                    "historyTypes": history_types,
                    "maxResults": 500,
                }
                if page_token:
                    params["pageToken"] = page_token
                request = self._service.users().history().list(**params)
                result = await asyncio.to_thread(request.execute)
                if "historyId" in result:
                    new_history_id = result["historyId"]
                for record in result.get("history", []):
                    for added in record.get("messagesAdded", []):
                        m = added.get("message", {})
                        gid = m.get("id")
                        if gid:
                            changes.append(
                                HistoryChange(
                                    change_type=HistoryChangeType.MESSAGE_ADDED,
                                    message_id=m.get("id", ""),
                                    gmail_id=gid,
                                    thread_id=m.get("threadId"),
                                    labels=m.get("labelIds"),
                                )
                            )
                    for deleted in record.get("messagesDeleted", []):
                        m = deleted.get("message", {})
                        gid = m.get("id")
                        if gid:
                            changes.append(
                                HistoryChange(
                                    change_type=HistoryChangeType.MESSAGE_DELETED,
                                    message_id=m.get("id", ""),
                                    gmail_id=gid,
                                    thread_id=m.get("threadId"),
                                )
                            )
                page_token = result.get("nextPageToken")
                if not page_token:
                    break
            return changes, new_history_id
        except HttpError as e:
            if e.resp.status in (404, 410):
                raise HistoryExpiredError(
                    f"Gmail history ID {start_history_id} has expired."
                ) from e
            raise

    async def fetch_messages_for_changes(
        self,
        changes: list[HistoryChange],
    ) -> list[HistoryChange]:
        """Fetch full message details for MESSAGE_ADDED changes; attach to change.message."""
        ids = [
            c.gmail_id
            for c in changes
            if c.change_type == HistoryChangeType.MESSAGE_ADDED
        ]
        if not ids:
            return changes
        fetched = await self._fetch_messages_batch(ids)
        by_id: dict[str, EmailMessage] = {}
        for msg in fetched:
            gid = msg.provider_metadata.get("gmail_id") if msg.provider_metadata else None
            if gid:
                by_id[gid] = msg
        for c in changes:
            if c.change_type == HistoryChangeType.MESSAGE_ADDED:
                c.message = by_id.get(c.gmail_id)
        return changes
