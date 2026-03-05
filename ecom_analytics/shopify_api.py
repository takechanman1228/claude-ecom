"""Shopify Admin API client using Bulk Operations."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

from ecom_analytics.config import ShopifyConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GraphQL queries for Bulk Operations
# ---------------------------------------------------------------------------

ORDERS_QUERY = """\
{
  orders%(filter)s {
    edges {
      node {
        id
        name
        createdAt
        totalPriceSet { shopMoney { amount currencyCode } }
        totalDiscountsSet { shopMoney { amount } }
        totalShippingPriceSet { shopMoney { amount } }
        totalTaxSet { shopMoney { amount } }
        displayFinancialStatus
        displayFulfillmentStatus
        customer { id email }
        lineItems {
          edges {
            node {
              id
              title
              quantity
              variant {
                id
                sku
                price
              }
              originalTotalSet { shopMoney { amount } }
              totalDiscountSet { shopMoney { amount } }
            }
          }
        }
      }
    }
  }
}
"""

PRODUCTS_QUERY = """\
{
  products {
    edges {
      node {
        id
        title
        productType
        vendor
        tags
        variants {
          edges {
            node {
              id
              sku
              price
              compareAtPrice
              inventoryItem {
                unitCost { amount }
              }
            }
          }
        }
      }
    }
  }
}
"""

INVENTORY_QUERY = """\
{
  inventoryItems {
    edges {
      node {
        id
        sku
        inventoryLevels {
          edges {
            node {
              id
              quantities(names: ["available"]) {
                quantity
              }
              location {
                id
              }
            }
          }
        }
      }
    }
  }
}
"""

# Bulk operation mutations
BULK_SUBMIT_MUTATION = """\
mutation bulkOperationRunQuery($query: String!) {
  bulkOperationRunQuery(query: $query) {
    bulkOperation {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
"""

BULK_POLL_QUERY = """\
{
  currentBulkOperation {
    id
    status
    errorCode
    objectCount
    fileSize
    url
  }
}
"""


@dataclass
class BulkOperationResult:
    """Result of a completed bulk operation."""

    operation_id: str
    status: str
    object_count: int
    file_size: int
    url: str | None


class ShopifyAPIError(Exception):
    """Raised on Shopify API errors."""


class ShopifyClient:
    """Thin httpx wrapper for Shopify Admin GraphQL API."""

    def __init__(self, config: ShopifyConfig, timeout: float = 30.0):
        if httpx is None:
            raise ImportError(
                "httpx is required for Shopify API access. "
                "Install with: pip install ecom-analytics[api]"
            )
        self._config = config
        self._client = httpx.Client(
            base_url=config.graphql_url,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": config.access_token,
            },
            timeout=timeout,
        )

    def graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query with rate-limit retry."""
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        max_retries = 3
        for attempt in range(max_retries):
            resp = self._client.post("", json=payload)

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", "2"))
                logger.warning("Rate limited, retrying after %.1fs", retry_after)
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            data = resp.json()

            if "errors" in data:
                raise ShopifyAPIError(
                    f"GraphQL errors: {json.dumps(data['errors'])}"
                )

            return data

        raise ShopifyAPIError("Max retries exceeded due to rate limiting")

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class BulkRunner:
    """Orchestrates Shopify Bulk Operations lifecycle."""

    def __init__(
        self,
        client: ShopifyClient,
        state_dir: str | Path | None = None,
        timeout_minutes: int = 60,
    ):
        self._client = client
        self._state_dir = Path(state_dir) if state_dir else None
        self._timeout_minutes = timeout_minutes

    def _submit(self, query: str) -> str:
        """Submit a bulk operation and return the operation GID."""
        result = self._client.graphql(
            BULK_SUBMIT_MUTATION, variables={"query": query}
        )

        op_data = result["data"]["bulkOperationRunQuery"]
        errors = op_data.get("userErrors", [])
        if errors:
            raise ShopifyAPIError(
                f"Bulk operation submit errors: {json.dumps(errors)}"
            )

        op = op_data["bulkOperation"]
        op_id = op["id"]
        logger.info("Bulk operation submitted: %s (status: %s)", op_id, op["status"])

        if self._state_dir:
            self._save_running_op(op_id)

        return op_id

    def _poll_until_done(
        self,
        op_id: str,
        interval: float = 10.0,
        progress_cb: Callable[[str, int], None] | None = None,
    ) -> BulkOperationResult:
        """Poll until the bulk operation completes."""
        deadline = time.time() + self._timeout_minutes * 60

        while time.time() < deadline:
            result = self._client.graphql(BULK_POLL_QUERY)
            op = result["data"]["currentBulkOperation"]

            if op is None:
                raise ShopifyAPIError(
                    "No current bulk operation found. It may have been cancelled."
                )

            status = op["status"]
            obj_count = op.get("objectCount", 0) or 0

            if progress_cb:
                progress_cb(status, obj_count)

            if status == "COMPLETED":
                self._clear_running_op()
                return BulkOperationResult(
                    operation_id=op["id"],
                    status=status,
                    object_count=obj_count,
                    file_size=op.get("fileSize", 0) or 0,
                    url=op.get("url"),
                )
            elif status in ("FAILED", "CANCELED"):
                self._clear_running_op()
                raise ShopifyAPIError(
                    f"Bulk operation {status}: error={op.get('errorCode')}"
                )

            logger.debug("Polling: status=%s, objects=%d", status, obj_count)
            time.sleep(interval)

        raise ShopifyAPIError(
            f"Bulk operation timed out after {self._timeout_minutes} minutes"
        )

    def _download_and_parse(self, url: str) -> list[dict]:
        """Download JSONL from the bulk operation URL and parse it."""
        if httpx is None:
            raise ImportError("httpx required")

        with httpx.stream("GET", url) as resp:
            resp.raise_for_status()
            raw = resp.read()

        return list(parse_jsonl_stream(raw))

    def run(
        self,
        query: str,
        progress_cb: Callable[[str, int], None] | None = None,
    ) -> list[dict]:
        """End-to-end: submit → poll → download → parse.

        If a previous operation is still running (from ``running_op.json``),
        resumes polling instead of submitting a new one.
        """
        existing_op = self._load_running_op()
        if existing_op:
            logger.info("Resuming polling for existing operation: %s", existing_op)
            op_id = existing_op
        else:
            op_id = self._submit(query)

        result = self._poll_until_done(op_id, progress_cb=progress_cb)

        if result.url is None:
            logger.info("Bulk operation returned no data (0 objects)")
            return []

        return self._download_and_parse(result.url)

    # -- State persistence for interrupted syncs --

    def _state_file(self) -> Path | None:
        if self._state_dir is None:
            return None
        return self._state_dir / "running_op.json"

    def _save_running_op(self, op_id: str) -> None:
        sf = self._state_file()
        if sf:
            sf.parent.mkdir(parents=True, exist_ok=True)
            sf.write_text(json.dumps({"operation_id": op_id}))

    def _load_running_op(self) -> str | None:
        sf = self._state_file()
        if sf and sf.exists():
            data = json.loads(sf.read_text())
            return data.get("operation_id")
        return None

    def _clear_running_op(self) -> None:
        sf = self._state_file()
        if sf and sf.exists():
            sf.unlink()


def parse_jsonl_stream(raw: bytes) -> Iterator[dict]:
    """Parse Shopify Bulk Operation JSONL output.

    Each line is a JSON object. Child rows contain a ``__parentId`` field
    linking them to their parent's ``id`` (GID).
    """
    for line in raw.split(b"\n"):
        line = line.strip()
        if line:
            yield json.loads(line)


def build_parent_child_map(rows: list[dict]) -> dict[str, dict]:
    """Organize JSONL rows into parent records with children attached.

    Shopify Bulk Operations emit parent rows followed by child rows.
    Child rows have ``__parentId`` pointing to the parent's ``id`` GID.

    Returns a dict keyed by parent GID, where each value is the parent
    record with a ``_children`` list of child dicts.
    """
    parents: dict[str, dict] = {}
    children: list[dict] = []

    for row in rows:
        if "__parentId" in row:
            children.append(row)
        else:
            gid = row.get("id", "")
            row["_children"] = []
            parents[gid] = row

    for child in children:
        parent_id = child["__parentId"]
        if parent_id in parents:
            parents[parent_id]["_children"].append(child)
        else:
            # Nested child (grandchild) — find parent of parent
            for p in parents.values():
                for c in p["_children"]:
                    if c.get("id") == parent_id:
                        c.setdefault("_children", []).append(child)
                        break

    return parents


def build_orders_query(since: str | None = None) -> str:
    """Build the orders bulk query with optional date filter."""
    if since:
        filter_str = f'(query: "created_at:>=\'{since}\'")'
    else:
        filter_str = ""
    return ORDERS_QUERY % {"filter": filter_str}
