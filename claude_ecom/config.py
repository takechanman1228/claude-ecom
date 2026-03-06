"""Configuration management for Shopify Admin API integration."""
# NOTE: Not used by the current review flow. Kept for future integration.

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]


_DEFAULT_API_VERSION = "2025-01"
_CONFIG_DIR = ".claude-ecom"
_CONFIG_FILE = "config.toml"


@dataclass
class ShopifyConfig:
    """Shopify Admin API configuration."""

    store_domain: str  # e.g. "my-store.myshopify.com"
    access_token: str
    api_version: str = _DEFAULT_API_VERSION
    timezone: str = "UTC"
    currency: str = "USD"
    allow_pii: bool = False

    @property
    def graphql_url(self) -> str:
        domain = self.store_domain.rstrip("/")
        if not domain.startswith("https://"):
            domain = f"https://{domain}"
        return f"{domain}/admin/api/{self.api_version}/graphql.json"


def load_config(path: str | Path | None = None) -> ShopifyConfig:
    """Load Shopify config from TOML file.

    Resolution order:
    1. Explicit *path* argument
    2. Local: ``<cwd>/.claude-ecom/config.toml``
    3. Global: ``~/.claude-ecom/config.toml``

    ``SHOPIFY_ACCESS_TOKEN`` env var always overrides the file token.
    """
    if tomllib is None:
        raise ImportError(
            "tomllib (Python 3.11+) or 'tomli' package required. Install with: pip install claude-ecom[api]"
        )

    candidates: list[Path] = []
    if path is not None:
        candidates.append(Path(path))
    else:
        candidates.append(Path.cwd() / _CONFIG_DIR / _CONFIG_FILE)
        candidates.append(Path.home() / _CONFIG_DIR / _CONFIG_FILE)

    config_path: Path | None = None
    for p in candidates:
        if p.is_file():
            config_path = p
            break

    if config_path is None:
        searched = ", ".join(str(c) for c in candidates)
        raise FileNotFoundError(
            f"No config file found. Searched: {searched}\nRun 'ecom shopify setup' to create one."
        )

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    shopify = data.get("shopify", data)

    token = os.environ.get("SHOPIFY_ACCESS_TOKEN", shopify.get("access_token", ""))
    if not token:
        raise ValueError("No access token found in config or SHOPIFY_ACCESS_TOKEN env var.")

    return ShopifyConfig(
        store_domain=shopify["store_domain"],
        access_token=token,
        api_version=shopify.get("api_version", _DEFAULT_API_VERSION),
        timezone=shopify.get("timezone", "UTC"),
        currency=shopify.get("currency", "USD"),
        allow_pii=shopify.get("allow_pii", False),
    )


def save_config(
    cfg: ShopifyConfig,
    path: str | Path | None = None,
    *,
    global_: bool = False,
) -> Path:
    """Write config to TOML file.

    Parameters
    ----------
    cfg : ShopifyConfig
        Configuration to save.
    path : str | Path | None
        Explicit output path. If *None*, uses local or global default.
    global_ : bool
        If *True* and *path* is None, write to ``~/.claude-ecom/config.toml``.

    Returns
    -------
    Path
        The path where the config was written.
    """
    if path is not None:
        out = Path(path)
    elif global_:
        out = Path.home() / _CONFIG_DIR / _CONFIG_FILE
    else:
        out = Path.cwd() / _CONFIG_DIR / _CONFIG_FILE

    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "[shopify]",
        f'store_domain = "{cfg.store_domain}"',
        f'access_token = "{cfg.access_token}"',
        f'api_version = "{cfg.api_version}"',
        f'timezone = "{cfg.timezone}"',
        f'currency = "{cfg.currency}"',
        f"allow_pii = {'true' if cfg.allow_pii else 'false'}",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")

    if not global_:
        _ensure_gitignore(out.parent.parent)

    return out


def _ensure_gitignore(project_root: Path) -> None:
    """Add ``.claude-ecom/`` to the nearest ``.gitignore`` if not present."""
    gitignore = project_root / ".gitignore"
    entry = ".claude-ecom/"

    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if entry in content:
            return
        if not content.endswith("\n"):
            content += "\n"
        content += f"{entry}\n"
        gitignore.write_text(content, encoding="utf-8")
    else:
        gitignore.write_text(f"{entry}\n", encoding="utf-8")
