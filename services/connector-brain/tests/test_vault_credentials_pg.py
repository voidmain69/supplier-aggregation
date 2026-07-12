"""VaultCredentialResolver against a real Vault (testcontainers). Integration — Docker only.

Proves the resolver reads supplier login/password from a KV v2 secret at ``credentials_ref``
and turns a missing secret/key into an actionable ConfigurationError.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import hvac
import pytest
from connector_brain.adapters.vault_credentials import VaultCredentialResolver

from sa_core.errors import ConfigurationError

pytestmark = pytest.mark.integration

MOUNT = "secret"  # KV v2 mount Vault dev-mode provisions by default


@pytest.fixture
def vault_client() -> Iterator[Any]:
    from testcontainers.vault import VaultContainer  # noqa: PLC0415

    with VaultContainer() as vault:
        client = hvac.Client(url=vault.get_connection_url(), token=vault.root_token)
        yield client


async def test_resolve__existing_secret__returns_login_and_password(vault_client: Any) -> None:
    vault_client.secrets.kv.v2.create_or_update_secret(
        path="suppliers/brain/acc1",
        secret={"login": "brain-user", "password": "s3cret"},
        mount_point=MOUNT,
    )
    resolver = VaultCredentialResolver(client=vault_client, mount_point=MOUNT)

    login, password = await resolver.resolve("suppliers/brain/acc1")

    assert (login, password) == ("brain-user", "s3cret")


async def test_resolve__secret_missing_password__raises_configuration_error(
    vault_client: Any,
) -> None:
    vault_client.secrets.kv.v2.create_or_update_secret(
        path="suppliers/brain/acc2", secret={"login": "only-login"}, mount_point=MOUNT
    )
    resolver = VaultCredentialResolver(client=vault_client, mount_point=MOUNT)

    with pytest.raises(ConfigurationError, match="password"):
        await resolver.resolve("suppliers/brain/acc2")


async def test_resolve__empty_ref__raises_configuration_error(vault_client: Any) -> None:
    resolver = VaultCredentialResolver(client=vault_client, mount_point=MOUNT)

    with pytest.raises(ConfigurationError, match="credentials_ref"):
        await resolver.resolve("")
