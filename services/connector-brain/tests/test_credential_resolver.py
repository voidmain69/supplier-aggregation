"""Unit tests for _credential_resolver: pick Vault, dev fallback, or fail loudly."""

from __future__ import annotations

import pytest
from connector_brain.adapters.brain_client import StaticCredentialResolver
from connector_brain.adapters.vault_credentials import VaultCredentialResolver
from connector_brain.settings import Settings
from connector_brain.sync_consumer import _credential_resolver

from sa_core.errors import ConfigurationError


def test_credential_resolver__vault_addr_set__returns_vault_resolver() -> None:
    settings = Settings(vault_addr="http://vault:8200", vault_token="toor")
    assert isinstance(_credential_resolver(settings), VaultCredentialResolver)


def test_credential_resolver__dev_creds_set__returns_static_resolver() -> None:
    settings = Settings(dev_login="brain-user", dev_password="s3cret")
    assert isinstance(_credential_resolver(settings), StaticCredentialResolver)


def test_credential_resolver__vault_wins_over_dev_creds() -> None:
    settings = Settings(
        vault_addr="http://vault:8200",
        vault_token="toor",
        dev_login="brain-user",
        dev_password="s3cret",
    )
    assert isinstance(_credential_resolver(settings), VaultCredentialResolver)


def test_credential_resolver__nothing_configured__raises() -> None:
    with pytest.raises(ConfigurationError, match="no supplier credential source"):
        _credential_resolver(Settings())
