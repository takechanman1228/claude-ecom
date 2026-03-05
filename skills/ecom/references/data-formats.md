# Supported Data Formats

<!-- Updated: 2026-03-04 -->

## Orders CSV

### Shopify Export Format

Auto-detected when columns include `Name`, `Created at`, `Financial Status`.

| Shopify Column | Internal Name | Required | Type |
|---------------|---------------|----------|------|
| Name | order_id | Yes | string |
| Created at | order_date | Yes | datetime |
| Total | amount | Yes | numeric |
| Email | customer_id | Yes | string |
| Discount Amount | discount | No | numeric |
| Financial Status | financial_status | No | string |
| Shipping | shipping | No | numeric |
| Billing City | city | No | string |
| Lineitem name | product_name | No | string |
| Lineitem quantity | quantity | No | integer |
| Lineitem price | item_price | No | numeric |
| Lineitem sku | sku | No | string |

### Generic Order Format

Used when Shopify columns are not detected.

| Column | Required | Type | Description |
|--------|----------|------|-------------|
| order_id | Yes | string | Unique order identifier |
| order_date | Yes | datetime | Order timestamp (any parseable format) |
| amount | Yes | numeric | Order total (or line-item amount) |
| customer_id | Yes | string | Customer identifier (email, ID, etc.) |
| discount | No | numeric | Discount amount applied |
| category | No | string | Product category |
| channel | No | string | Acquisition channel |
| device | No | string | Device type (mobile/desktop/tablet) |
| sku | No | string | Product SKU |
| product_name | No | string | Product name |
| quantity | No | integer | Item quantity |
| item_price | No | numeric | Unit price |
| cost | No | numeric | Cost of goods |
| city | No | string | Customer city |
| region | No | string | Customer region/state |

## Products CSV

### Shopify Product Export

Auto-detected when columns include `Handle`, `Title`, `Variant Price`.

| Shopify Column | Internal Name | Required | Type |
|---------------|---------------|----------|------|
| Handle | product_id | Yes | string |
| Title | name | Yes | string |
| Variant Price | price | Yes | numeric |
| Variant SKU | sku | No | string |
| Vendor | vendor | No | string |
| Type | category | No | string |
| Tags | tags | No | string |
| Variant Inventory Qty | stock_quantity | No | integer |

### Generic Product Format

| Column | Required | Type | Description |
|--------|----------|------|-------------|
| product_id | Yes | string | Unique product identifier |
| name | Yes | string | Product name |
| price | Yes | numeric | Current selling price |
| category | Yes | string | Product category |
| cost | No | numeric | Cost of goods |
| stock_quantity | No | integer | Current stock level |
| created_at | No | datetime | Product creation date |
| sku | No | string | SKU code |
| vendor | No | string | Supplier/vendor name |

## Inventory CSV

| Column | Required | Type | Description |
|--------|----------|------|-------------|
| sku | Yes | string | SKU identifier |
| quantity_on_hand | Yes | integer | Current stock quantity |
| reorder_point | No | integer | Reorder trigger level |
| lead_time_days | No | integer | Supplier lead time |
| cost | No | numeric | Unit cost |
| days_on_hand | No | integer | Days since last receipt |
| location | No | string | Warehouse/location |

## Data Quality Requirements

| Aspect | Minimum | Recommended |
|--------|---------|-------------|
| Date range | 90 days | 12+ months |
| Order count | 100 | 1,000+ |
| Customer ID coverage | 80% | 95%+ |
| SKU coverage | 70% | 90%+ |
| Date format | Any pandas-parseable | ISO 8601 |

## Encoding & Parsing

- Encoding: UTF-8 (default), UTF-8-BOM, Shift_JIS auto-detected
- Delimiter: comma (default), tab and semicolon auto-detected
- Date parsing: pandas `to_datetime` with `infer_datetime_format=True`
- Numeric parsing: commas in numbers handled via `errors="coerce"`

---

## Shopify Admin API (v0.2.0+)

Data imported via `ecom shopify sync` using Bulk Operations (GraphQL).

### API → Normalized Schema Mapping

#### Orders (`normalize_orders`)

| API Field | Internal Name | Type | Notes |
|-----------|---------------|------|-------|
| `name` | order_id | string | e.g. "#1001" |
| `createdAt` | order_date | datetime (UTC) | ISO 8601 |
| `customer.email` | customer_id | string | SHA-256 hashed by default |
| `totalPriceSet.shopMoney.amount` | gross_revenue | numeric | |
| `totalDiscountsSet.shopMoney.amount` | discount_amount | numeric | |
| `totalShippingPriceSet.shopMoney.amount` | shipping_amount | numeric | |
| `totalTaxSet.shopMoney.amount` | tax_amount | numeric | |
| (computed) | net_revenue | numeric | gross - discount |
| `totalPriceSet.shopMoney.currencyCode` | currency | string | |
| `financialStatus` | financial_status | string | lowercased |
| `fulfillmentStatus` | fulfillment_status | string | lowercased |

Guest orders (null customer) receive a deterministic pseudo-ID: `guest_<sha256(order_gid)[:12]>`.

#### Order Line Items (`normalize_order_items`)

| API Field | Internal Name | Type |
|-----------|---------------|------|
| parent `name` | order_id | string |
| `variant.id` | product_id, variant_id | string |
| `variant.sku` | sku | string |
| `title` | title | string |
| `quantity` | quantity | integer |
| `variant.price` | unit_price | numeric |
| `originalTotalSet.shopMoney.amount` | line_revenue | numeric |
| `totalDiscountSet.shopMoney.amount` | line_discount | numeric |

#### Products (`normalize_products`)

| API Field | Internal Name | Type |
|-----------|---------------|------|
| `id` (Product GID) | product_id | string |
| `variants[].id` | variant_id | string |
| `variants[].sku` | sku | string |
| `title` | title | string |
| `productType` | category | string |
| `variants[].price` | price | numeric |
| `variants[].compareAtPrice` | compare_at | numeric |
| `variants[].inventoryItem.unitCost.amount` | cost | numeric |
| `vendor` | vendor | string |
| `tags` | tags | string (comma-joined) |

#### Inventory (`normalize_inventory`)

| API Field | Internal Name | Type |
|-----------|---------------|------|
| `sku` | sku | string |
| `inventoryLevels[].location.id` | location_id | string |
| `inventoryLevels[].quantities[0].quantity` | on_hand | integer |

### Compatibility Bridge (`build_orders_compat`)

The `build_orders_compat()` function merges normalized orders and line items
into the flat schema expected by all existing analysis modules:

| Output Column | Source |
|---------------|--------|
| order_id | orders.order_id |
| order_date | orders.order_date |
| amount | items.line_revenue |
| customer_id | orders.customer_id |
| discount | items.line_discount |
| shipping | orders.shipping_amount |
| sku | items.sku |
| product_name | items.title |
| quantity | items.quantity |
| item_price | items.unit_price |

### Storage Format

Synced data is stored in `.claude-ecom/data/` as:
- `orders.parquet` / `orders.csv` (Parquet preferred, CSV fallback)
- `order_items.parquet` / `order_items.csv`
- `products.parquet` / `products.csv`
- `inventory.parquet` / `inventory.csv`
- `sync_state.json` (last sync timestamp, record counts)

---

## Canonical Analytics Schema
<!-- v0.4: added per DR2 research -->

Standard table definitions used across multiple checks. Use these as the reference schema when mapping client data.

### Core Commerce Tables

#### orders
| Column | Type | Description |
|--------|------|-------------|
| order_id | string | Unique order identifier |
| customer_id | string | Customer identifier |
| order_ts | timestamp | Order timestamp |
| net_revenue | float | Revenue after discounts and returns |
| gross_revenue | float | Revenue before returns |
| discount_amount | float | Total discount applied |
| coupon_code | string | Coupon code used (nullable) |
| channel | string | Acquisition channel |
| device_type | string | desktop / mobile / tablet |
| city | string | Customer city (nullable) |
| region | string | Customer region (nullable) |
| financial_status | string | paid / refunded / partially_refunded |

#### order_items
| Column | Type | Description |
|--------|------|-------------|
| order_id | string | FK to orders |
| sku | string | Product SKU |
| product_id | string | Product identifier |
| category_id | string | Product category |
| qty | int | Quantity ordered |
| unit_price | float | Price per unit |
| discount_amount | float | Item-level discount |
| cogs | float | Cost of goods sold (nullable) |
| is_bundle | boolean | Whether item is a bundle |

#### returns
| Column | Type | Description |
|--------|------|-------------|
| return_id | string | Unique return identifier |
| order_id | string | FK to orders |
| sku | string | Returned SKU |
| return_ts | timestamp | Return timestamp |
| reason | string | Return reason code |
| refund_amount | float | Refund amount |

#### inventory_snapshots
| Column | Type | Description |
|--------|------|-------------|
| date | date | Snapshot date |
| sku | string | Product SKU |
| on_hand_qty | int | Units on hand |
| available_to_sell_qty | int | Units available for sale |
| cost_per_unit | float | Unit cost |

#### products
| Column | Type | Description |
|--------|------|-------------|
| sku | string | Product SKU |
| product_id | string | Product identifier |
| category_id | string | Category |
| price | float | Current selling price |
| created_ts | timestamp | Product creation date |
| status | string | active / archived / draft |
| is_consumable | boolean | Consumable flag |
| avg_rating | float | Average review rating |
| review_count | int | Number of reviews |

### Cross-Check Conventions

- **ABC ranking:** Computed on trailing 90-day revenue. A = top 20% of revenue (typically ~5% of SKUs), B = next 30%, C = bottom 50%.
- **Cohort definition:** Group customers by first-order month (`cohort_month`).
- **Trailing windows:** Default to 90 days unless specified (e.g., `rev_90d`, `orders_last_90d`).
- **Gross profit:** `net_revenue - cogs` at item level, aggregated up.

### Minimum Sample Sizes

| Analysis | Minimum Records | Minimum Time Span |
|----------|-----------------|-------------------|
| Revenue trend (R01-R04) | 100 orders | 3 months |
| Seasonality (R02) | 500 orders | 12 months |
| Cohort retention (C02-C04) | 200 customers/cohort | 6 cohorts |
| Price elasticity (PR06) | 3 price changes/SKU | 90 days |
| Forecast accuracy (R15) | 90 daily observations | 3 months |

### Timezone Handling

- Store all timestamps in UTC internally
- Apply store timezone for day/hour analysis (R06)
- Cohort month boundaries use store timezone
- Session timestamps should align with order timestamps (same timezone source)
