"""IMAP email provider (iCloud, Yahoo, custom servers)."""

import email
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import aioimaplib

from app.infrastructure.external.email.protocols import EmailMessage, EmailProviderConfig
from app.shared.telemetry.logging import get_logger
from app.shared.utils.datetime import utc_now

logger = get_logger(__name__)


class IMAPProvider:
    """IMAP provider for universal email access."""

    def __init__(self) -> None:
        self._client: aioimaplib.IMAP4_SSL | None = None
        self._config: EmailProviderConfig | None = None

    async def connect(self, config: EmailProviderConfig) -> None:
        """Connect to IMAP server."""
        self._config = config
        params = config.connection_params or {}
        imap_server = params.get("imap_server")
        imap_port = params.get("imap_port", 993)
        if not imap_server:
            raise ValueError("imap_server required in connection_params")
        username = config.credentials.get("username", config.email_address)
        password = config.credentials.get("password")
        if not password:
            raise ValueError("password required in credentials")
        logger.info("Connecting to IMAP server: %s:%s", imap_server, imap_port)
        self._client = aioimaplib.IMAP4_SSL(host=imap_server, port=imap_port)
        await self._client.wait_hello_from_server()
        await self._client.login(username, password)
        logger.info("Successfully connected to IMAP: %s", username)

    async def disconnect(self) -> None:
        """Disconnect from IMAP."""
        if self._client:
            await self._client.logout()
            self._client = None
            logger.info("Disconnected from IMAP server")

    async def fetch_messages(
        self,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[EmailMessage]:
        """Fetch messages from INBOX (since date, optional limit)."""
        if not self._client:
            raise RuntimeError("Not connected to IMAP server")
        await self._client.select("INBOX")
        if since:
            date_str = since.strftime("%d-%b-%Y")
            search_criteria = f"SINCE {date_str}"
        else:
            search_criteria = "ALL"
        _, msg_ids = await self._client.search(search_criteria)
        msg_id_list = msg_ids[0].split()
        if limit and len(msg_id_list) > limit:
            msg_id_list = msg_id_list[-limit:]
        messages = []
        for msg_id in msg_id_list:
            try:
                msg = await self._fetch_and_parse_message(msg_id)
                if msg:
                    messages.append(msg)
            except Exception as e:
                logger.error("Error fetching message %s: %s", msg_id, e)
        logger.info("Fetched %s messages from IMAP", len(messages))
        return messages

    async def _fetch_and_parse_message(self, msg_id: bytes) -> EmailMessage | None:
        """Fetch and parse a single message."""
        _, msg_data = await self._client.fetch(msg_id, "(RFC822 FLAGS)")
        if not msg_data or not msg_data[1]:
            return None
        email_message = email.message_from_bytes(msg_data[1])
        message_id = email_message.get("Message-ID", f"imap-{msg_id.decode()}")
        from_address = email_message.get("From", "")
        to_addresses = [
            addr.strip() for addr in email_message.get("To", "").split(",")
        ]
        subject = email_message.get("Subject", "")
        date_str = email_message.get("Date")
        timestamp = (
            parsedate_to_datetime(date_str) if date_str else utc_now()
        )
        flags_str = msg_data[0].decode() if msg_data[0] else ""
        is_read = "\\Seen" in flags_str
        is_starred = "\\Flagged" in flags_str
        has_attachments = any(
            part.get_content_disposition() == "attachment"
            for part in email_message.walk()
        )
        return EmailMessage(
            message_id=message_id,
            thread_id=email_message.get("In-Reply-To"),
            from_address=from_address,
            to_addresses=to_addresses,
            subject=subject,
            timestamp=timestamp,
            labels=["INBOX"],
            is_read=is_read,
            is_starred=is_starred,
            has_attachments=has_attachments,
            provider_metadata={"imap_uid": msg_id.decode(), "flags": flags_str},
        )

    async def setup_webhook(self, callback_url: str) -> dict[str, Any]:
        """IMAP does not support webhooks."""
        raise NotImplementedError("IMAP does not support webhooks")

    async def remove_webhook(self) -> None:
        """No-op for IMAP."""
        pass

    @property
    def supports_webhooks(self) -> bool:
        return False

    @property
    def supports_incremental_sync(self) -> bool:
        return True
