"""Outlook/Office 365 provider using Microsoft Graph API."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

import httpx
from msal import ConfidentialClientApplication

from app.infrastructure.external.email.protocols import (
    EmailMessage,
    EmailProviderConfig,
)
from app.shared.telemetry.logging import get_logger
from app.shared.utils.datetime import utc_now

logger = get_logger(__name__)


class OutlookProvider:
    """Outlook/Office 365 provider using Microsoft Graph API."""

    def __init__(self, *, http_client: httpx.AsyncClient | None = None) -> None:
        self._access_token: str | None = None
        self._config: EmailProviderConfig | None = None
        self._graph_url = "https://graph.microsoft.com/v1.0"
        self._shared_http = http_client

    @asynccontextmanager
    async def _http_cm(self):
        """Yield shared HTTP client or a short-lived one (connection reuse when shared)."""
        if self._shared_http is not None:
            yield self._shared_http
            return
        async with httpx.AsyncClient() as client:
            yield client

    async def connect(self, config: EmailProviderConfig) -> None:
        """Connect to Microsoft Graph using OAuth credentials."""
        self._config = config
        client_id = config.credentials.get("client_id")
        client_secret = config.credentials.get("client_secret")
        tenant_id = config.credentials.get("tenant_id")
        refresh_token = config.credentials.get("refresh_token")
        if not all([client_id, client_secret, tenant_id]):
            raise ValueError("client_id, client_secret, tenant_id required")
        app = ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        if refresh_token:
            result = app.acquire_token_by_refresh_token(
                refresh_token,
                scopes=["https://graph.microsoft.com/.default"],
            )
        else:
            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"],
            )
        if "access_token" in result:
            self._access_token = result["access_token"]
            logger.info("Connected to Microsoft Graph: %s", config.email_address)
        else:
            raise RuntimeError(
                f"Failed to acquire token: {result.get('error_description')}"
            )

    async def disconnect(self) -> None:
        """Disconnect."""
        self._access_token = None
        logger.info("Disconnected from Microsoft Graph")

    async def fetch_messages(
        self,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[EmailMessage]:
        """Fetch messages via Graph API with pagination."""
        if not self._access_token:
            raise RuntimeError("Not connected to Microsoft Graph")
        messages: list[EmailMessage] = []
        next_link: str | None = None
        params: dict[str, Any] = {"$orderby": "receivedDateTime DESC"}
        if limit:
            params["$top"] = min(limit, 1000)
        else:
            params["$top"] = 1000
        if since:
            params["$filter"] = f"receivedDateTime ge {since.isoformat()}"
        async with self._http_cm() as client:
            while True:
                if next_link:
                    response = await client.get(
                        next_link,
                        headers={"Authorization": f"Bearer {self._access_token}"},
                    )
                else:
                    response = await client.get(
                        f"{self._graph_url}/me/messages",
                        headers={"Authorization": f"Bearer {self._access_token}"},
                        params=params,
                    )
                response.raise_for_status()
                data = response.json()
                for item in data.get("value", []):
                    try:
                        messages.append(self._parse_outlook_message(item))
                    except Exception as e:
                        logger.error("Error parsing Outlook message: %s", e)
                next_link = data.get("@odata.nextLink")
                if not next_link:
                    break
                if limit and len(messages) >= limit:
                    messages = messages[:limit]
                    break
        logger.info("Fetched %s messages from Outlook", len(messages))
        return messages

    def _parse_outlook_message(self, item: dict[str, Any]) -> EmailMessage:
        """Parse Graph API message into EmailMessage."""
        ts = item["receivedDateTime"].replace("Z", "+00:00")
        timestamp = datetime.fromisoformat(ts)
        to_addresses = [
            r["emailAddress"]["address"] for r in item.get("toRecipients", [])
        ]
        return EmailMessage(
            message_id=item["id"],
            thread_id=item.get("conversationId"),
            from_address=item["from"]["emailAddress"]["address"],
            to_addresses=to_addresses,
            subject=item.get("subject", ""),
            timestamp=timestamp,
            labels=item.get("categories", []),
            is_read=item.get("isRead", False),
            is_starred=item.get("flag", {}).get("flagStatus") == "flagged",
            has_attachments=item.get("hasAttachments", False),
            provider_metadata={
                "outlook_id": item["id"],
                "conversation_id": item.get("conversationId"),
                "categories": item.get("categories", []),
            },
        )

    async def setup_webhook(self, callback_url: str) -> dict[str, Any]:
        """Setup Graph webhook subscription."""
        if not self._access_token:
            raise RuntimeError("Not connected to Microsoft Graph")
        expiration = (
            utc_now().replace(hour=0, minute=0, second=0) + timedelta(days=3)
        ).isoformat() + "Z"
        subscription = {
            "changeType": "created",
            "notificationUrl": callback_url,
            "resource": "/me/mailFolders/inbox/messages",
            "expirationDateTime": expiration,
            "clientState": "timeline-secret-value",
        }
        async with self._http_cm() as client:
            response = await client.post(
                f"{self._graph_url}/subscriptions",
                headers={"Authorization": f"Bearer {self._access_token}"},
                json=subscription,
            )
            response.raise_for_status()
            result = response.json()
        logger.info("Outlook webhook setup: %s", result)
        return result

    async def remove_webhook(self) -> None:
        """No-op (call Graph to delete subscription if needed)."""
        if not self._access_token:
            return
        logger.info("Outlook webhook removed")

    @property
    def supports_webhooks(self) -> bool:
        return True

    @property
    def supports_incremental_sync(self) -> bool:
        return True
