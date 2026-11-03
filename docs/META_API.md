# Official Meta API integration

Verified against official documentation on 2026-11-02:
- Overview: https://dev.meta.ai/docs/overview
- Quickstart: https://dev.meta.ai/docs/quickstart
- Chat Completions: https://dev.meta.ai/docs/protocols/chat-completions
- Structured output: https://dev.meta.ai/docs/structured-output
- Tool calling: https://dev.meta.ai/docs/tool-calling
- Account-visible model catalog: https://dev.meta.ai/docs/api-reference/models/list-models
- Errors: https://dev.meta.ai/docs/error-handling

Configuration: MODEL_API_KEY in ignored .env; META_MODEL defaults to muse-spark-1.3. All inference calls go to the official https://api.meta.ai/v1 endpoint. The browser never receives this key.

Provider verification first requests GET /models and confirms the configured model is listed, then performs an actual small structured generation. A stored verification fingerprint is invalidated if the key/model changes. Configured and generation-verified are separate UI states.

Semantic mapping sends bounded source summaries: up to 30 unreviewed tables, column indices/labels, four small samples per column, structural coordinates and warnings. Full workbook binaries are not sent to Meta. Users initiate this operation with Analyze with Meta. All proposals remain unconfirmed until reviewed.

The HTTPX client uses Chat Completions and strict response_format.json_schema, then validates again with Pydantic and source-column/table checks. It rejects unknown tables, duplicate columns/fields, invalid responses and truncated completions. Only tool_choice=auto is used; unsupported forced modes are not sent.

The Orchestrator plans with Meta and can call exactly three typed tools: sales_analysis, inventory_analysis, draft_purchase_orders. Those represent Sales, Inventory and Procurement specialists. The loop is capped at five turns and eight calls; unknown tools and invalid arguments are rejected. There is no arbitrary SQL, Python, filesystem or approval tool. Deterministic tools calculate quantities and money. Only concise final summaries and actual tool results enter the user-visible trace; private reasoning is not exposed.

On November 4, 2026 the official catalog, structured generation and both live agent workflows were reverified. The sales tool now accepts a list of explicit filters (or an empty list), and inventory accepts zero or one product ID. The local backend renders business claims from completed tool results. If Meta returns prose before getting evidence, one bounded retry is allowed. Failed reverification clears the connection badge. A product-specific question for A001 returned the reviewed USD 270.00 with its source rows.

401/403/404 and bad-request responses produce sanitized errors without raw provider bodies. Transient statuses retry at most twice with bounded backoff; long Retry-After values return a retry-later error. Timeouts never silently trigger a fake response.

Test MockTransport responses exist only in unit tests for error/contract coverage. Guided tools are an explicitly labeled deterministic product path, not a simulated AI service. Live tests require an opt-in variable because they call the real API and may consume credits.
