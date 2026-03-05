"""Tests for claude_ecom.config."""

import os
import pytest

from claude_ecom.config import ShopifyConfig, load_config, save_config, _ensure_gitignore


@pytest.fixture
def sample_config():
    return ShopifyConfig(
        store_domain="test-store.myshopify.com",
        access_token="shpat_test_token_123",
        api_version="2025-01",
        timezone="America/New_York",
        currency="USD",
        allow_pii=False,
    )


class TestShopifyConfig:
    def test_graphql_url(self, sample_config):
        url = sample_config.graphql_url
        assert url == "https://test-store.myshopify.com/admin/api/2025-01/graphql.json"

    def test_graphql_url_with_https_prefix(self):
        cfg = ShopifyConfig(
            store_domain="https://test-store.myshopify.com",
            access_token="tok",
        )
        assert cfg.graphql_url == "https://test-store.myshopify.com/admin/api/2025-01/graphql.json"


class TestSaveAndLoad:
    def test_round_trip(self, tmp_path, sample_config):
        config_path = tmp_path / "config.toml"
        save_config(sample_config, path=config_path)

        loaded = load_config(path=config_path)
        assert loaded.store_domain == sample_config.store_domain
        assert loaded.access_token == sample_config.access_token
        assert loaded.api_version == sample_config.api_version
        assert loaded.timezone == sample_config.timezone
        assert loaded.currency == sample_config.currency
        assert loaded.allow_pii == sample_config.allow_pii

    def test_save_creates_parent_dirs(self, tmp_path, sample_config):
        config_path = tmp_path / "deep" / "nested" / "config.toml"
        save_config(sample_config, path=config_path)
        assert config_path.exists()

    def test_env_var_overrides_file_token(self, tmp_path, sample_config, monkeypatch):
        config_path = tmp_path / "config.toml"
        save_config(sample_config, path=config_path)

        monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "env_override_token")
        loaded = load_config(path=config_path)
        assert loaded.access_token == "env_override_token"

    def test_load_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No config file found"):
            load_config(path=tmp_path / "nonexistent.toml")

    def test_load_missing_token_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            '[shopify]\nstore_domain = "test.myshopify.com"\n'
        )
        with pytest.raises(ValueError, match="No access token"):
            load_config(path=config_path)

    def test_global_save(self, tmp_path, sample_config, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        result = save_config(sample_config, global_=True)
        assert ".claude-ecom" in str(result)
        assert result.exists()


class TestEnsureGitignore:
    def test_creates_gitignore_if_missing(self, tmp_path):
        _ensure_gitignore(tmp_path)
        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()
        assert ".claude-ecom/" in gitignore.read_text()

    def test_appends_to_existing_gitignore(self, tmp_path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n")
        _ensure_gitignore(tmp_path)
        content = gitignore.read_text()
        assert "node_modules/" in content
        assert ".claude-ecom/" in content

    def test_no_duplicate_entry(self, tmp_path):
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".claude-ecom/\n")
        _ensure_gitignore(tmp_path)
        content = gitignore.read_text()
        assert content.count(".claude-ecom/") == 1

    def test_gitignore_injection_on_save(self, tmp_path, sample_config):
        save_config(sample_config, path=tmp_path / ".claude-ecom" / "config.toml")
        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()
        assert ".claude-ecom/" in gitignore.read_text()
