# PROJECT BRIEF: Autonomous Context-Aware dbt Developer Agent
## Prepared for Detailed Implementation Planning with Kimi K3

---

## 1. EXECUTIVE SUMMARY

**Project Name:** Autonomous Context-Aware dbt Developer Agent

**Hackathon:** Build with DataHub: The Agent Hackathon (Devpost)
- **Track:** Metadata-Aware Code Generation & Development
- **Deadline:** August 10, 2026 @ 2:00 PM PDT (21 days from July 21, 2026)
- **Prize Pool:** $20,500 total; Grand Prize: $6,000
- **Judges:** Engineers from DataHub, Pinterest, OpenAI, Cloudflight, and others

**One-Liner:** An AI agent that generates production-ready dbt models by grounding itself in DataHub's metadata graph, validating code through actual dbt compilation, and self-healing errors before a human ever sees the output.

---

## 2. PROBLEM STATEMENT

### The Current Workflow Pain
Data engineers spend 2-5 days on routine data requests:
1. Manually explore schemas across multiple tables
2. Look up foreign key relationships
3. Check for PII or governance restrictions
4. Write SQL (often hallucinating column names)
5. Test it, discover errors, debug and rewrite
6. Get peer review
7. Update the company's data catalog (if they remember)

### Why Standard AI Tools Fail
- **GitHub Copilot / Cursor**: Context starvation. They don't know enterprise schemas, so they hallucinate column names constantly. No ground truth.
- **Text-to-SQL wrappers**: LLM grades its own homework. Subtle errors (wrong GROUP BY, type mismatches) get pushed to production.
- **Proprietary BI Copilots**: Read-only. They generate a query and stop. The metadata graph never gets updated, so catalogs go stale.

### Why This Matters
Without reliable metadata and validation:
- Agents get stuck on tasks a junior engineer could finish in 10 minutes
- Data pipelines break silently
- Company's data map becomes obsolete, eroding trust in governance

---

## 3. WHAT WE'RE BUILDING EXACTLY

An autonomous agent that treats code generation as a *full engineering workflow*, not a simple text-to-SQL problem.

### The Core Flow

**Stage 1: Grounding (Context Retrieval)**
- User submits a natural language request: *"Join orders and customers on customer_id, remove duplicates by email, include only 2024 orders"*
- Agent queries DataHub MCP Server to retrieve:
  - Exact schemas (column names, types, nullability)
  - Primary/foreign key relationships
  - Data profiles (row counts, freshness, ownership)
  - Existing lineage (which tables feed which models)

**Stage 2: Drafting (LLM Generation)**
- LLM writes dbt SQL model + schema.yml test config
- Ground in retrieved metadata, not hallucinated

**Stage 3: Validation (The Secret Sauce)**
- Agent does NOT just hope the code works
- It provisions a local DuckDB instance
- Mocks the DataHub schemas into it (CREATE TABLE stubs with correct types)
- Runs actual `dbt run` (or `dbt build`) against the stubs
- If dbt compiler throws an error: ambiguous column, type mismatch, missing JOIN key, bad GROUP BY — the agent catches it

**Stage 4: Self-Healing (Iterative Fix)**
- Agent reads the structured dbt error
- Rewrites the code to fix it
- Validates again
- Repeats up to 3 times before giving up

**Stage 5: Human Approval (Interrupt)**
- Once code compiles perfectly, LangGraph pauses via `interrupt()`
- React UI shows the engineer the SQL, schema.yml, and a lineage preview
- Engineer reviews and clicks "Approve" or "Reject"

**Stage 6: Closing the Loop (Write-Back)**
- On approval:
  - Create a Git branch, commit files, open a GitHub PR
  - Use DataHub Python SDK to register the new model as a dataset
  - Tag it "agent-generated"
  - Link to the PR for traceability
  - Set lineage back to input tables

**Result:** Next person (human or agent) queries DataHub and sees this new model already has correct lineage and metadata — the catalog stays fresh.

---

## 4. WHY THIS BEATS THE COMPETITION

### vs. GitHub Copilot / Cursor
**Their approach:** Generate SQL based on files open in your IDE or context you manually paste.
**Their flaw:** Massive context starvation. They don't know your enterprise data warehouse schemas → hallucinate column names constantly.
**Your advantage:** You securely hook into DataHub via MCP. Agent has ground-truth of entire data ecosystem before writing a single line of code.

### vs. Standard Text-to-SQL Wrappers
**Their approach:** Pull a schema, send it to LLM, return a query.
**Their flaw:** Rely on LLM to grade its own homework. Subtle syntax errors (wrong GROUP BY, bad CAST) get pushed to the user, breaking pipelines later.
**Your advantage:** DuckDB / dbt Validation Loop. You use deterministic, compiler-level feedback to fix code automatically. You refuse to show code that won't physically run.

### vs. Proprietary BI Copilots (Looker AI, Tableau Pulse, etc.)
**Their approach:** Auto-generate a query and call it done.
**Their flaw:** Read-only. Metadata graph remains outdated — "stale catalog" problem that plagues data teams.
**Your advantage:** You actively write back to the graph. When PR merges, agent updates DataHub with new lineage + tags. Solves exactly what DataHub judges are looking for.

---

## 5. TECHNICAL ARCHITECTURE

### High-Level Design (HLD) Data Flow


[ User Interface (React) ]
↓ (Natural Language Prompt)
↓
[ LangGraph State Machine (FastAPI Backend) ]
├─→ [1. Context Retriever Node] ↔ [DataHub MCP Server]
│ (Pull schemas, FK rels, lineage, profiles)
│
├─→ [2. LLM Generator Node] ↔ [ Any LLM API]
│ (Draft SQL + schema.yml)
│
├─→ [3. DuckDB Stub Generator]
│ (Type-map DataHub types → DuckDB)
│ (Seed with sample rows from profiles)
│
├─→ [4. Validator Node] ↔ [dbt + DuckDB]
│ (Run dbt parse → dbt run on stubs)
│ (Parse compiler errors into structured form)
│
└─→ [Retry Loop with max_retries=3]
├─ If errors: route back to Generator
└─ If pass: pause for human approval

   ├─→ [5. Human Approval (Interrupt)]
   │   (User reviews in React UI)
   │   ↓ (Approve or Reject)
   │
   ├─→ [6. Action/Writeback Node]
   │   ├→ [GitHub API] (Create branch, commit, open PR)
   │   └→ [DataHub Python SDK] (Register model, lineage, tags)



   