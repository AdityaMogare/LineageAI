### Key Architectural Decisions

1. **LangGraph for Orchestration**
   - State machine is explicit and testable
   - `interrupt()` primitive handles human-in-the-loop cleanly
   - Cyclic edges (retry loop) are first-class

2. **DuckDB for Validation**
   - Local, embeddable, no production data needed
   - Runs actual SQL, not just parser checks
   - Catches real errors: ambiguous columns, type mismatches, GROUP BY issues

3. **Type-Mapping Layer (Critical)**
   - DataHub may return Snowflake/BigQuery types (VARIANT, SUPER, nested STRUCT)
   - Map to DuckDB equivalents or fail gracefully
   - Seeded stubs with profile-informed sample rows (not just empty tables)
   - This catches errors like WHERE clauses returning zero rows

4. **Bounded Retry Loop**
   - Max 3 retries before fallback to human
   - Structured error parsing (line, type, suggestion) for LLM to consume
   - Prevents infinite loops and API cost runaway

5. **Write-Back to DataHub**
   - On approval: create DataHub dataset entry for new model
   - Set lineage to input tables
   - Tag "agent-generated" + link PR URL for audit trail
   - Keeps metadata graph current and trustworthy

---

## 6. STACK & TOOLS

### Backend Stack
- **LangGraph** (≥0.1.0): State machine, graph execution, interrupts
- **FastAPI** (≥0.100): REST API server
- **Python 3.11+**: Primary language
- **dbt-core** (latest): SQL compilation + execution
- **DuckDB**: In-process SQL engine for validation
- **DataHub Python SDK** + **DataHub MCP Server**: Metadata retrieval & write-back
- **OpenAI or Anthropic API**: LLM calls (GPT-4 or Claude 3.5)
- **PyGithub or GitHub REST API**: PR creation

### Frontend Stack
- **React** (≥18.2) with **Vite**: UI framework
- **TailwindCSS or similar**: Styling
- **TypeScript**: Type safety

### Development & Deployment
- **Cursor IDE**: Agent-assisted coding (with MCP connections)
- **Docker**: Local DataHub instance
- **GitHub**: Version control + MCP repository
- **Git Hooks / Pre-commit**: Code quality checks

### Open Source Requirements
- Apache 2.0 license at repo root (visible in About section)
- Public repository (all code open source)

---

## 7. ARCHITECTURAL REFINEMENTS & CONSTRAINTS

### Validation Strategy (Not Just Parse, But Execution)
- `dbt parse` only resolves Jinja and refs — does NOT catch logical errors
- Must run `dbt run` (or `dbt build`) against stubbed DuckDB tables
- This catches: ambiguous columns, type mismatches, GROUP BY errors, JOIN logic

### Type Mapping Edge Cases
- **Problem:** DataHub returns Snowflake `VARIANT`, BigQuery `SUPER`, Hive nested structs
- **Solution:** 
  - Map common types 1:1 (VARCHAR → TEXT, INT64 → INTEGER)
  - For unmappable types: either fail gracefully with user message, or cast to JSON/STRING
  - Document mappings in `type_mapping.py` module

### DuckDB Stub Seeding
- Don't use empty tables — seed with 10-100 profile-informed sample rows
- Reason: Catches errors like WHERE clauses returning zero rows, missing data scenarios
- Safely generate samples without real data: use faker + schema constraints

### Retry Termination
- After 3 failed attempts, don't loop forever
- Route to human with: original prompt, last error, code draft
- Human decides whether to fix and resubmit or give up

### DataHub MCP Latency & Caching
- Cache retrieved schemas in state for the duration of one request
- Don't re-query for every retry (saves latency, ensures consistency)
- Fresh query only if user submits new prompt

### dbt Run Sandboxing
- Run dbt in isolated temp directory (not app's working directory)
- Capture stdout/stderr separately for error parsing
- Clean up temp dirs after validation to avoid disk bloat

---

## 8. JUDGING CRITERIA ALIGNMENT

**Use of DataHub:** ✅ 
- Context Retriever pulls ground-truth schemas, relationships, lineage
- Agent reasons over that metadata to generate correct code
- Agent writes back to graph on approval (bonus: contributes to graph, not just reads)

**Technical Execution:** ✅ 
- Self-healing validation loop: deterministic, compiler-level
- Cyclic LangGraph state machine: explicit error handling
- End-to-end demo: unvalidated requests become production-ready dbt PRs

**Originality:** ✅ 
- Combining LangGraph cyclic reasoning + dbt compilation + DataHub context is novel
- Not available out-of-box from any single tool
- Extends dbt & DataHub but not rebuilding them

**Real-World Usefulness:** ✅ 
- Data engineers actually spend days on this
- Solves "stale catalog" problem
- Could reduce time-to-PR from days to minutes

**Submission Quality:** ✅ 
- Clear README with setup instructions
- Recorded video showing self-healing in action (intentionally trigger 1 retry)
- examples/ folder with sample generated models + validation logs
- Apache 2.0 license visible

**Bonus (Open-Source Contribution):** ✅ (Optional)
- Could contribute custom DataHub connector / skill if time permits
- Or document improvements to MCP Server integration

---

## 9. KNOWN RISKS & GOTCHAS

1. **Type Mapping Complexity**
   - DataHub can return platform-specific types that don't map cleanly to DuckDB
   - Risk: Validation fails because of type incompatibility, not actual logic error
   - Mitigation: Build type-mapping layer first; test against variety of schemas

2. **dbt Execution Overhead**
   - Spinning up dbt + DuckDB for each validation adds latency
   - Risk: Demo feels slow; iterative debugging becomes tedious
   - Mitigation: Profile early; consider caching compiled dbt manifests; run validation in background thread

3. **Error Parsing Brittleness**
   - dbt error messages vary by error type and are context-dependent
   - Risk: Parser misses some error types, LLM doesn't know how to fix
   - Mitigation: Write comprehensive test harness with 10+ known-error dbt outputs; iterate parser

4. **DataHub MCP Server Downtime**
   - If DataHub MCP is slow/unavailable during demo, retrieval times out
   - Risk: Demo fails live
   - Mitigation: Keep pre-recorded demo video as fallback; mock DataHub responses for demo

5. **GitHub API Rate Limiting**
   - GitHub has rate limits; PR creation hits multiple endpoints
   - Risk: Rapid testing hits limits
   - Mitigation: Use GitHub test organization; read rate limit headers; cache PR creations

6. **LLM Prompt Instability**
   - LLM may still refuse to generate SQL even with good context
   - Risk: Generator node hangs or returns malformed output
   - Mitigation: Structured output (JSON schema); retry with different temp; guardrails in prompt

7. **State Explosion in LangGraph**
   - Long feedback loops can create very large state objects
   - Risk: Serialization/memory issues
   - Mitigation: Clear old validation errors from state after retry; checkpoint periodically

8. **Demo Video Timing**
   - <3 min video must show: prompt → self-healing (1 retry) → approval → PR → DataHub update
   - Risk: Fits tightly; any latency breaks the flow
   - Mitigation: Practice script; pre-stage data; use pre-seeded DataHub instance

---

## 10. 21-DAY ROADMAP (DETAILED BREAKDOWN)

### Week 1: Foundation (Days 1–7)

**Day 1 — Environment Setup & DataHub Seeding**
- Spin up DataHub Quickstart locally (Docker)
- Seed 4–5 realistic tables with schemas:
  - `orders` (id, customer_id, amount, created_at)
  - `customers` (customer_id, email, region, created_at)
  - `products` (product_id, name, category, price)
  - `order_items` (order_id, product_id, quantity)
- Add FK relationships in DataHub UI
- Test DataHub MCP Server responses manually

**Day 2 — Repo Scaffolding**
- Init FastAPI backend + React (Vite) frontend
- LangGraph project structure: `graph.py`, `state.py`, `nodes/`
- Package structure: