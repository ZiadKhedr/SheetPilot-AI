# Sales-based stock planning

SheetPilot estimates how quickly each product sells and how long its on-hand quantity may last. This is deterministic trailing-average analysis, not an AI-invented quantity or a guaranteed forecast.

## Inputs and evidence

Only confirmed inventory and sales mappings with a current, confirmed exact product-ID relationship are used. Sales require valid dates, either directly mapped or inherited through a confirmed order-header link. Quantity analysis does not require a currency, although purchase quotes and monetary analytics still do.

For each inventory product, related sales are indexed by table and product. Overlapping mappings of the same product/quantity source cells are deduplicated; conflicting views are blocked. Formula/error rows and other rows rejected by normalization never become trusted demand inputs. Explicitly different sales/stock units block calculation. Missing units require the user's comparable-unit acknowledgement before a policy is enabled.

## Calendar-window calculation

The default preview ends at the latest usable reviewed sale date; an explicit scenario/stock-snapshot date can be selected. It is never silently treated as today's live stock. Dates must be between 1900-01-01 and today.

The requested lookback is clipped to the first available sale in the related source history. The actual inclusive day count is displayed. Zero-sale calendar days inside that span are included in the denominator.

- Daily sales = dated units in the observation window / observed calendar days.
- Days remaining = on-hand quantity / daily sales.
- Estimated depletion date = scenario date + rounded-up days remaining.
- Proposed reorder point = ceil(units × (lead days + safety days) / observed days).
- Proposed target = ceil(units × (lead days + safety days + extra coverage days) / observed days).
- If on-hand is below the proposed reorder point, suggested order = ceil(max(0, target − on-hand)); otherwise zero.

Whole base-unit rounding is explicit. Pack sizes, supplier MOQ, incoming purchase orders and unit conversion are not implemented.

Example: 40 units over 10 calendar days = 4/day. Stock 8 gives 2 days of cover. Lead time 2 days + buffer 1 day gives reorder point 12; adding 4 coverage days gives target 28 and an order recommendation of 20 units.

No positive recent sales produces no depletion date or purchase recommendation. A product with no matched history is not assumed to have zero demand. Limited history may show a provisional estimate, but cannot supply a replenishment threshold. Replenishment use requires at least 7 observed days, 3 positive dated sales rows, 2 positive sales days, no undated matched rows, supported quantity precision/range and matching explicit units when supplied.

## Preview versus reviewed policy

Default assumptions (30-day lookback, 7-day lead, 3-day buffer, 14 extra coverage days) are labeled as editable scenarios, not Excel values. GET and preview do not save settings, approve relationships or create orders.

To enable a policy, the user must explicitly confirm a scenario date, acknowledge alignment with the stock snapshot/comparable units, and submit the expected policy revision. The owner can disable it. Read-only tokens cannot change policy. The policy and actor are audited.

A confirmed policy supplies calculated thresholds only where source thresholds are missing and demand evidence is sufficient. Source thresholds always take precedence. Originals, reviewed mappings and normalized source facts remain unchanged. Policy edits do not require remapping business identifiers.

Purchasing still requires a unique reviewed supplier quote, explicit matching currency, current relationships and separate purchase approval. Pending actions retain the planning parameters, observed window, units/rate, policy revision, snapshot acknowledgement and source examples. The Excel Execution sheet records the demand basis and Source Trace includes sampled sales lineage. All source workbook versions remain in the action for reproduction. Policy revisions enter action fingerprints; policy changes invalidate older pending proposals.

## API

- `GET /api/workspaces/{id}/demand`: current policy or default scenario; read-only.
- `POST .../demand/preview`: supplied `window_days`, `lead_time_days`, `safety_days`, `review_period_days`, `as_of`; no writes.
- `PUT .../demand/policy`: same parameters plus `expected_revision`, `enabled`, `stock_snapshot_confirmed`; requires owner/mutation access.

Analytics contains the planning table and assumption/review controls. Inventory Agent results include consumption estimates and limitations; detailed evidence stays in the API/action audit, with at most 100 demand summaries in the model context and an explicit truncation flag.

## Limits

A historical dataset produces a historical scenario. Sparse or incomplete records, stockouts suppressing observed sales, returns, promotions, seasonality, new products, inbound orders and structural changes can invalidate a trailing average. The app flags limited evidence and does not claim to predict these effects. Actual stock snapshot alignment and unit comparability require user review. Supplier MOQ/lead-time catalog meanings are retained by mapping, but the current planner uses explicitly reviewed scenario assumptions rather than choosing an ambiguous supplier quote automatically.
