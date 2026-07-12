"""Vault-backed ``CredentialResolver``: resolve a ``credentials_ref`` to (login, password).

Supplier credentials live only in Vault (hard rule 6); the DB stores just the ``credentials_ref``
(a KV path like ``suppliers/brain/<account>``). The connector fetches them at auth time and never
persists them. hvac is synchronous, so reads are offloaded to a thread to keep the event loop free.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import structlog

from sa_core.errors import ConfigurationError

if TYPE_CHECKING:
    from connector_brain.settings import Settings

log = structlog.get_logger(__name__)


def build_vault_client(settings: Settings) -> Any:
    """Construct an authenticated hvac client from settings (token auth; injected in k8s)."""
    import hvac  # noqa: PLC0415 -- keep the heavy client import local to the adapter

    client = hvac.Client(url=settings.vault_addr, token=settings.vault_token)
    return client


class VaultCredentialResolver:
    """Resolves supplier credentials from a Vault KV v2 secret. Secrets never persist."""

    def __init__(self, *, client: Any, mount_point: str) -> None:
        self._client = client
        self._mount_point = mount_point

    async def resolve(self, credentials_ref: str) -> tuple[str, str]:
        if not credentials_ref:
            raise ConfigurationError("account has no credentials_ref; cannot resolve credentials")
        data = await asyncio.to_thread(self._read_secret, credentials_ref)
        try:
            return str(data["login"]), str(data["password"])
        except KeyError as exc:
            raise ConfigurationError(
                f"Vault secret at {credentials_ref!r} is missing key {exc.args[0]!r} "
                "(expected 'login' and 'password')"
            ) from exc

    def _read_secret(self, path: str) -> dict[str, Any]:
        response = self._client.secrets.kv.v2.read_secret_version(
            path=path, mount_point=self._mount_point, raise_on_deleted_version=True
        )
        data: dict[str, Any] = response["data"]["data"]
        return data
