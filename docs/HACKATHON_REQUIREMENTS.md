# SHEETPILOT AI — META AI HACKATHON MASTER BUILD PROMPT

## YOUR ROLE

Act as an autonomous, highly experienced software engineering team specializing in:

- Full-stack development
- AI agents and LLM integration
- Data engineering
- Excel automation
- Software architecture
- UI/UX design
- Testing and deployment

You are building a real, functional product for the Meta AI Hackathon.

The developer is participating solo. Optimize for a technically impressive, polished, reliable hackathon submission rather than attempting to build a complete enterprise ERP.

Do not stop at planning, scaffolding, or writing documentation. Implement, run, test, debug, and improve the application.

## 1. PRODUCT VISION

**Product name:** SheetPilot AI

**Tagline:** Your Spreadsheets. Your AI Workforce.

SheetPilot AI transforms existing business Excel workbooks into intelligent, AI-powered business operations without forcing companies to migrate away from Excel.

Companies upload their existing spreadsheets, even when the files have unfamiliar structures, column names, and layouts.

The platform automatically examines the workbook structure, uses Meta AI to interpret business semantics, discovers relationships between datasets, generates relevant dashboards, and coordinates AI agents that can recommend and execute approved business actions.

### Core Differentiators

1. Self-adapting Excel understanding
2. Cross-workbook business intelligence
3. Meta-powered AI agent collaboration
4. Human-controlled autonomous actions
5. Excel-preserving workflow

Do not claim that every arbitrary Excel workbook can be understood perfectly. Detect and clearly communicate ambiguities.

## 2. EXISTING PROJECT

Phase 1 — Excel Structure Analyzer — has already been implemented in the repository.

Before making changes:

- Inspect the entire repository.
- Identify the working Phase 1 modules.
- Run existing tests.
- Review existing architecture and dependencies.
- Reuse existing functionality where appropriate.
- Preserve working code.
- Document any limitations discovered.

Do not rebuild Phase 1 unnecessarily.

## 3. PRIMARY HACKATHON OBJECTIVE

Implement this complete end-to-end workflow:

1. User uploads Sales, Inventory, and Suppliers Excel workbooks.
2. The system detects worksheets, tables, headers, and columns.
3. Meta AI identifies business entities and column meanings.
4. The system proposes relationships between workbooks.
5. User reviews uncertain mappings.
6. The system generates a business dashboard from validated data.
7. User asks an AI agent to analyze business operations.
8. Inventory Agent identifies products requiring replenishment.
9. Procurement Agent prepares purchase order drafts.
10. User approves or rejects a proposed action.
11. Approved actions generate a correctly modified or additional Excel output.
12. The system displays the actual execution history.

This workflow is the primary definition of success.

Every step must be connected to real backend functionality.

## 4. TECHNOLOGY STACK

Frontend:
- React
- TypeScript
- Tailwind CSS
- A modern component library
- Recharts or equivalent

Backend:
- Python
- FastAPI
- Pydantic
- Pandas
- OpenPyXL

AI:
- Official Meta Model API
- Prefer Muse Spark if actually available and supported
- Verify the exact model identifier and endpoint from official documentation and the account's actual access
- Use Meta AI as the primary reasoning provider
- Implement robust structured-output validation
- Implement tool-calling orchestration compatible with the selected API
- OpenAI Agents SDK may be used only if verified compatible with the selected Meta provider; otherwise implement a lightweight agent orchestrator

Database:
- SQLite for a reliable hackathon MVP, with a clear migration path to PostgreSQL

Development:
- Docker Compose
- Pytest
- Frontend tests
- Playwright for end-to-end browser testing

Avoid unnecessary infrastructure and dependencies.

## 5. EXCEL INTELLIGENCE ENGINE

Extend Phase 1 to support:

- Unfamiliar workbook structures
- Multiple worksheets
- Multiple tables per worksheet
- English and Arabic column names
- Headers in unexpected rows
- Missing data
- Duplicate records
- Mixed data types
- Formulas
- Merged cells
- Hidden worksheets
- Irregular table layouts

Preserve original workbook structures and metadata.

Create structured analysis reports containing detected regions, candidate header rows, inferred field types, warnings, and source cell references.

## 6. META AI SEMANTIC INTELLIGENCE

Implement AI-powered business understanding.

The AI should identify:

- Sales records
- Products
- Inventory quantities
- Suppliers
- Product identifiers
- Prices
- Costs
- Dates
- Reorder thresholds
- Relationships between business entities

Use a canonical semantic model that supports custom fields.

The LLM must receive relevant structured summaries, not blindly receive enormous workbook contents.

AI outputs must be validated against strict schemas.

When uncertain, present the mapping for user confirmation.

Provide actual evidence for relationship suggestions, such as overlapping product identifiers and matching values.

## 7. CROSS-FILE DATA INTEGRATION

Allow the platform to connect information from multiple workbooks.

Example:

Sales.xlsx contains `Item Code`.

Inventory.xlsx contains `SKU`.

Suppliers.xlsx contains `Product Reference`.

The system should recognize that these columns may represent the same business identifier, verify possible matches, and propose the relationship.

Do not automatically accept weak relationships.

Create a normalized operational data representation while preserving references to the original Excel sources.

## 8. BUSINESS DASHBOARD

Build a polished, responsive SaaS interface.

Required pages:

- Overview Dashboard
- Excel File Manager
- Workbook Structure Explorer
- AI Mapping Review
- Business Analytics
- Agent Workspace
- Approval Center
- Activity Timeline

Display relevant information based on actually available data, including:

- Revenue
- Sales trends
- Top-selling products
- Inventory levels
- Low-stock products
- Suggested purchase orders
- Data quality alerts

Do not display unsupported, invented, or hardcoded KPIs.

Use professional UI design with good typography, spacing, interactive charts, loading indicators, and meaningful empty states.

## 9. AI AGENT SYSTEM

Implement four logical agents:

### Orchestrator Agent

Interprets user requests, chooses appropriate specialist agents, and coordinates tool execution.

### Sales Agent

Analyzes sales data, sales trends, product performance, and historical demand.

### Inventory Agent

Analyzes quantities, stock levels, reorder thresholds, and stockout risks.

### Procurement Agent

Identifies appropriate suppliers and prepares purchase order drafts based on validated business data.

All agents must operate through typed, validated backend tools.

Never grant agents unrestricted database queries, arbitrary Python execution, or direct filesystem modification capabilities.

Use the LLM for interpreting requests and planning actions.

Use deterministic Python logic for quantities, money calculations, and workbook modifications.

Provide observable agent execution traces and concise decision summaries without exposing private internal reasoning.

## 10. ACTIONS AND APPROVAL SYSTEM

Implement a complete approval workflow.

Every proposed action should include:

- Action type
- Proposed changes
- Affected records
- Relevant source files
- Business justification
- Validation results
- Approval status

Users must be able to approve or reject the action.

Approval must trigger actual backend execution.

Rejecting an action must produce no workbook changes.

Implement idempotency protection so repeated approval does not duplicate a purchase order.

Keep audit records for every action.

## 11. EXCEL WRITE-BACK

For the hackathon MVP, prioritize a real, reliable local Excel workflow.

When an action is approved:

- Verify the source workbook and version.
- Validate the proposed change.
- Preserve original uploaded files.
- Generate a modified copy or additional workbook as appropriate.
- Preserve unrelated worksheets and formulas wherever technically supported.
- Record exact modifications.
- Allow the user to download the generated workbook.

Do not claim live bidirectional OneDrive or SharePoint synchronization unless it has actually been implemented and tested.

## 12. TEST DATA

Create two distinct fictional companies with different Excel schemas.

Company A: Electronics Distribution

Files:
- Sales.xlsx
- Inventory.xlsx
- Suppliers.xlsx

Company B: Restaurant Supply Business

Files:
- Orders.xlsx
- Stock.xlsx
- Vendors.xlsx

Use different:
- Column names
- Table positions
- Worksheet layouts
- Naming conventions
- File structures

Include realistic records, intentional data quality problems, and valid cross-file relationships.

Document the expected outputs.

The goal is to verify that the application does not depend on hardcoded column names or one dataset.

## 13. IMPLEMENTATION STRATEGY

Use vertical-slice development.

### Milestone 1 — Working Excel Upload

Connect the existing Phase 1 analyzer to the backend and frontend.

Verify that a user can upload and inspect an unfamiliar workbook.

### Milestone 2 — Meta AI Understanding

Integrate the actual Meta Model API.

Implement semantic mapping, mapping review, and relationship proposals.

### Milestone 3 — Business Intelligence

Build validated cross-file data integration and dashboard calculations.

### Milestone 4 — Agentic Workflow

Implement the Orchestrator, Sales, Inventory, and Procurement agent capabilities.

### Milestone 5 — Approval and Excel Action

Implement purchase order generation, approval, safe Excel output, and audit history.

### Milestone 6 — UI and Demo Polish

Improve the interface, loading states, error handling, and demo presentation.

### Milestone 7 — Comprehensive Validation

Run unit, integration, and end-to-end tests. Fix critical defects.

After each milestone:
- Run relevant tests.
- Fix failures.
- Make a Git commit.
- Update a progress checklist.
- Keep the project runnable.

Do not wait for user approval between ordinary implementation milestones.

## 14. MANDATORY TESTS

Implement tests for:

- Workbook structure recognition
- Semantic mapping validation
- Cross-workbook relationship discovery
- Accurate inventory calculations
- Accurate sales calculations
- API errors and invalid AI responses
- Approval and rejection flows
- Unauthorized or conflicting modifications
- Excel file preservation
- Purchase order generation
- Frontend/backend integration

Test the complete workflow using Company A.

Then repeat the relevant ingestion, mapping, and analytics tests with Company B without modifying the application to fit its schema.

Record actual results.

## 15. FINAL DELIVERABLES

Provide:

1. Complete working source code.
2. Functional frontend.
3. Functional FastAPI backend.
4. Verified Meta AI integration.
5. Excel Intelligence Engine.
6. Cross-file business analytics.
7. Working agents.
8. Approval workflow.
9. Excel output generation.
10. Two demo datasets.
11. Automated tests and results.
12. Docker Compose configuration.
13. README with setup and startup commands.
14. Architecture documentation.
15. Known limitations.
16. A 3-minute hackathon demonstration script.
17. A concise judge-facing project description.

## 16. CRITICAL EXECUTION RULES

- No fake AI calls.
- No hardcoded demo answers.
- No mock backend pretending to be functional.
- No invented data insights.
- No silently changing original workbooks.
- No exposed API keys.
- No claiming untested features work.
- No spending excessive effort on optional enterprise features.
- No stopping at documentation or scaffolding.

If something cannot be implemented, document the limitation and deliver the strongest working alternative.

## 17. DEFINITION OF DONE

The project is demo-ready only when:

- The application starts successfully.
- A user can upload unfamiliar Excel files.
- The real Meta AI provider performs semantic analysis.
- The user can confirm ambiguous mappings.
- The dashboard displays verified calculations.
- Agents can complete the replenishment workflow.
- An action can be approved or rejected.
- An approved action produces a valid Excel output.
- The activity log accurately records execution.
- The main workflow passes an end-to-end test.
- The application can be demonstrated from a clean startup.

Do not equate a successful build with a successful end-to-end demonstration.

## FINAL INSTRUCTION

You have full autonomy for ordinary implementation decisions within the existing repository.

Start by inspecting the current Phase 1 code, checking the test suite, and validating the Meta Model API integration.

Then implement the application milestone by milestone until the core end-to-end workflow is complete and verified.

Prioritize a working, impressive, competition-ready product over unnecessary complexity.

Begin implementation now.