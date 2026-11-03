# Semantic mapping and relationship review

The catalog contains **53 meanings and nine business entities**, plus `unknown`.

| Entity | Grain / use |
|---|---|
| sales | Sales line items; feeds sales revenue and units |
| orders | Order/invoice headers; reviewed date/customer context, never added to line revenue |
| inventory | Current stock snapshots; thresholds optional for analytics, required for replenishment |
| products | Product catalog/master records |
| suppliers | Product-specific supplier quotes for the existing procurement workflow |
| supplier_directory | Supplier master/contact records, without assuming a product quote |
| customers | Customer/account master records |
| purchases | Purchase lines, retained separately from sales |
| payments | Payments/receipts, retained separately from sales |

`GET /api/catalog` returns definitions, groups, and entity requirements. Important distinctions include actual selling price/list price, per-unit discount/line discount/rate, line revenue/order total, opening stock/current stock/reservations, and transactional quantity/aggregate units sold. Unmapped columns remain custom fields. Recognizing a meaning does not implement its business rules: taxes, minimum order quantities, lead times, payments and multi-warehouse operations do not drive automatic actions.

## Meta evidence and efficiency

- Missing/distinct counts, cell types, formula/error counts, and representative values.
- Up to eight evenly spaced, row-aligned examples rather than independently sampled columns.
- Workbook/sheet/range, current header and bounded alternative header candidates.
- Deterministic arithmetic checks comparing actual and list prices against observed line totals.
- Read-only context from other mappings and source identifier-overlap candidates.
- Explicit definitions, business-grain distinctions and ambiguity/custom-field instructions.

Up to four tables are analyzed per call, split earlier when combined width exceeds 40 columns; a wider single table is analyzed alone, up to 30 selected tables per request. Summaries are size bounded. All batches validate before any proposal is saved. Every requested table must occur exactly once; foreign/duplicate columns, repeated canonical meanings, unsupported headers and invented currency settings are rejected. One repair call is allowed for invalid output; transport/authentication failures do not trigger another mapping prompt. No rule fallback is disguised as AI.

Completions use an 8,192-token allowance and explicit `medium` reasoning. Meta counts private reasoning and visible output against the same allowance ([official reasoning documentation](https://dev.meta.ai/docs/reasoning)). A `length` stop discards the entire partial reply and retries the same request once at 16,384 tokens. It never continues a partial JSON document or executes partial tool calls. Other unfinished response types, content restrictions and authentication failures do not trigger this token retry. An exhausted token retry is not passed into schema repair. A schema repair can separately encounter one length retry, so there are at most four completion generations per mapping batch; existing bounded transport retries are separate. Evidence is requested as short, source-specific sentences to reduce output size. If a later batch still fails, earlier proposals remain unsaved and the error says no mapping changes were applied.

Confirmed mappings are skipped by default. **Reanalyze this table with Meta** explicitly returns that selected mapping to proposal status, invalidates related decisions, and rematerializes the mirror from remaining reviewed tables. Concurrent human edits reject the AI update transaction.

## Review controls

Grouped/searchable meanings include definitions and field-level evidence/confidence/alternatives. Confidence is an uncalibrated estimate. Profiles and source arithmetic remain visible. Changing a header fetches the actual new labels/samples and clears old assignments. Save a draft, explicitly confirm, or exclude a table.

Choose a currency column or a reviewed table currency, never both. Explicit monetary-header suffixes such as `sale_unit_price_gbp` can propose GBP. Country names and `$` alone never imply a currency. A proposed setting does not affect analytics until confirmation. Lineage identifies it as a reviewed table setting rather than a source cell.

Stock without reorder points remains available for analytics, shows **Threshold missing**, and cannot produce replenishment decisions. Thresholds are never inferred from opening stock, sales totals or arbitrary percentages.

## Relationship discovery and use

Discovery compares business identifiers inside one workbook and between files: product, order, customer, supplier, purchase-order, warehouse and payment IDs, and barcodes. Previews may use provisional mappings or exact multilingual header hints. Overlapping source regions are not joined to themselves.

Proposals expose both source columns, overlap, coverage in both directions, duplicate-key counts, unmatched IDs, examples and cardinality. Many-to-many matches stay weak evidence. Diagnostics explain missing identifiers or nonmatching values instead of returning an unexplained empty list. Up to 100 active tables are supported per discovery request.

Both source mappings must be confirmed with the proposed identifier meanings and current revisions before accepting an exact link. Discovery never approves anything. Accept/reject decisions persist only at the same mapping revisions. Mapping changes invalidate related decisions. Confirming a mapping automatically refreshes existing relationship previews at the new revisions, without accepting them. Legacy stale links expose an explicit refresh action; the UI computes blockers from current mappings rather than cached discovery messages.

Case/Unicode/whitespace-normalized-only matches are labeled **preview only** and cannot be confirmed as operational joins. Leading zeroes and punctuation are not stripped. No fuzzy name match silently substitutes for a business identifier.

Only reviewed, current, exact joins enrich missing context: sales lines may inherit date/customer/currency from a unique order header; sales/inventory may inherit descriptive attributes from a unique product-catalog row. Lineage records the source row and relationship. Ambiguous matches neither multiply records nor inherit context. Header totals and payments never count as sales-line revenue. Rejection or stale revisions remove inherited context on rematerialization.

Sales can also inherit product names and descriptive attributes from a uniquely matching reviewed inventory row. Inventory costs, currencies, thresholds, and stock quantities are not inherited into sales. Missing currency diagnostics expose the affected sales table and explicit header hint; the analytics page links to that mapping. The currency shortcut fills a draft only and requires mapping confirmation. Threshold-free inventory is shown as unassessed, with an explanation of the missing minimum-stock rule.

## API additions

- `GET /api/workspaces/{workspace}/tables/{table}/preview?header_row=N`: read-only profiles and aligned evidence.
- `POST .../analyze-meta`: optional `{table_ids: [...], include_confirmed: false}` selection.
- `PUT .../tables/{table}`: optional `constants: {currency: "GBP"}`; optimistic revision is mandatory.
- `POST .../relationships/discover`: returns proposals; workspace state also exposes `relationship_report` diagnostics.

## Data and limits

Originals remain immutable. No mapping or relationship self-confirms. Meta mapping sends bounded workbook-derived samples to the configured official Meta endpoint; use only data you are authorized to share. Offline label suggestions are identified as rules. Synthetic fixtures verify the new behavior, not perfect arbitrary-file comprehension. Complex multirow headers, fuzzy business identities, arbitrary foreign-key inference, cross-currency calculations and general-purpose join editing remain outside this implementation.
