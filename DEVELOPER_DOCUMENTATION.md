# Developer Documentation — Agentic Research Backend

## 1. Purpose & Business Problem Alignment

The **Agentic Research Backend** is an enterprise-grade multi-agent system designed specifically for corporate strategy, product management, and business intelligence teams. It transforms a raw product or business idea into an executive-ready market, competitor, and risk analysis report delivered exclusively as a professionally formatted **Microsoft Word (.docx)** document.

Unlike traditional single-prompt assistants or passive chatbots, this backend operates as an autonomous, high-speed multi-agent team:
1. **Plans its work dynamically** based on the specific business idea.
2. **Delegates tasks to candidate agents** with strict context boundaries.
3. **Executes live intelligence gathering** using concurrent web search APIs.
4. **Applies rigorous quality evaluation** via an independent critic agent before delivery.

---

## 2. Multi-Agent Solution Architecture

The architecture uses a **Hierarchical Orchestrator (Supervisor-Worker) Pattern** implemented via a decoupled middleware pipeline. Four specialized agents coordinate through a shared, typed context:

```
                              ┌────────────────────────┐
                              │    SUPERVISOR AGENT    │
                              │ (Orchestrator & Harness)│
                              └───────────┬────────────┘
                                          │
                     ┌────────────────────┼────────────────────┐
                     │                    │                    │
                     ▼                    ▼                    ▼
            ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
            │ RESEARCHER AGENT│  │ COMPARATOR AGENT│  │ EVALUATOR AGENT │
            │ (Tavily Search) │  │(Synthesis & Risk│  │ (Quality Rubric │
            │   [Candidate]   │  │   [Candidate]   │  │   [Candidate]   │
            └─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Agent Roles & Separation of Concerns

| Agent | Responsibility | Core Skill / Tooling |
|---|---|---|
| **Supervisor** | Lifecycle owner. Formulates the task plan, manages middleware dispatch, coordinates candidate delegation, and synthesizes the executive summary. | Orchestration, LLM synthesis, `TaskManager`, Session State. |
| **Researcher** | Competitive intelligence gathering. Formulates multi-angle search queries, runs concurrent Tavily API requests, filters duplicates, and writes grounded market findings. | High-speed concurrent Tavily Search, source extraction. |
| **Comparator** | Analytical reasoning. Deconstructs the idea against research findings through chained reasoning: comparative advantages $\to$ multi-factor risks $\to$ strategic recommendations. | Deep contextual reasoning, sequential prompt chaining. |
| **Evaluator** | Quality assurance critic. Audits generated sections against an explicit 4-point rubric (Specificity, Grounding, Completeness, Internal Consistency); commands bounded rewrites upon deficiency. | Evaluative critique, bounded revision loops. |

**Why this architecture:**
- **Skill Specialization:** Information retrieval (Researcher) and strategic judgment (Comparator) have conflicting prompt requirements. Separating them prevents search hallucination from bleeding into analytical reasoning.
- **Independent Quality Gate:** An agent should never evaluate its own output using the same prompt context that generated it. The Evaluator acts as an independent adversarial auditor.
- **Predictable Orchestration:** Workers do not communicate directly with one another. All state flows through the typed `PipelineContext`, ensuring deterministic execution and an auditable trail.

---

## 3. Candidate Task Delegation

Delegation is executed via the **Middleware Pipeline Pattern**. Each agent's capability is encapsulated as a standalone `Skill` implementing the `run(context: PipelineContext)` protocol:

```python
Pipeline(
    skills=[
        PlanningSkill(self),             # Dynamic plan formulation
        ProductIdeaSkill(self),          # Executive vision restatement
        ResearchSkill(researcher),       # Concurrent web search & intelligence
        AnalysisSkill(comparator),       # Chained comparative & risk analysis
        EvaluationSkill(evaluator),      # Concurrent section quality audit
        SummarySkill(self),              # Executive summary synthesis
        ReportSkill(),                   # Professional Word (.docx) generation
    ]
)
```

### Context Boundary Enforcement
- **Isolated Scopes:** Candidate agents only receive the slice of data necessary to perform their work. The Researcher never sees the Comparator's prompts; the Comparator never sees raw search JSON responses.
- **Auditability:** Every delegation is registered as a `"middleware_dispatch"` event in the `TaskManager` activity log.
- **State Tracking:** Candidate agents mark tasks as `pending`, `in_progress`, and `done`, updating the shared to-do list in real-time.

---

## 4. Plan $\to$ Execute $\to$ Evaluate Lifecycle

The system operates across three distinct, auditable phases:

```
  PHASE 1: PLAN           PHASE 2: EXECUTE                   PHASE 3: EVALUATE & COMPOSE
┌──────────────┐    ┌───────────────────────────────┐    ┌───────────────────────────────────┐
│ Dynamic Task │───▶│ Concurrent Web Intelligence   │───▶│ Concurrent Section Rubric Audits  │
│ Formulation  │    │ Chained Comparative Analysis  │    │ Bounded Rewrites on Deficiencies  │
│ (4-6 Tasks)  │    │ Multi-Dimensional Risk Profile│    │ Executive Summary & Word (.docx)  │
└──────────────┘    └───────────────────────────────┘    └───────────────────────────────────┘
```

1. **Plan (Dynamic Problem Decomposition):**
   - The Supervisor prompts the model with the raw idea to generate a structured 4–6 task roadmap.
   - Each item is registered in the `TaskManager` with unique task IDs (`plan_item_0`, `plan_item_1`, etc.).
2. **Execute (Context-Accumulating Execution):**
   - The Researcher executes multi-query concurrent searches to ground the report in real-world market data.
   - The Comparator builds upon the research through a dependency chain (described in Section 7).
   - Planned task items progress from `pending` to `done` as their corresponding milestones complete.
3. **Evaluate (Audit & Gatekeeping):**
   - Sections are audited concurrently against a 4-point rubric.
   - Approved sections are passed to the Executive Synthesizer and compiled strictly into a Microsoft Word document.

---

## 5. Evaluation Criteria & Quality Gatekeeping

Quality control is enforced through an explicit contract. The **EvaluatorAgent** reviews each section against four rigid criteria:

1. **Specificity:** Does the section reference concrete details, actual company names, and verified metrics rather than generic filler?
2. **Grounding (Anti-Hallucination):** Are all claims strictly anchored to the provided web research, without inventing speculative statistics or partnerships?
3. **Completeness:** Does the section fully cover its mandated scope without trailing off or leaving unaddressed requirements?
4. **Internal Consistency:** Does the section avoid contradicting the product vision or previous sections?

### Bounded Revision Protocol
```
[Generated Section] ──▶ Evaluator LLM Pass ──▶ Verdict: PASS?
                                                    │
                      ┌─────────────────────────────┴─────────────────────────────┐
                      ▼ YES                                                       ▼ NO (REVISE)
               Accept Section                                     Check Revision Budget (<= 1)
                                                                                  │
                                                    ┌─────────────────────────────┴─────────────────────────────┐
                                                    ▼ Budget Available                          ▼ Budget Exhausted
                                             Trigger Rewrite with Feedback            Accept Section with Audit Flag
                                             Re-evaluate Revised Output               ("evaluation_exhausted")
```

- **Bounded Execution:** Bounded by `config.MAX_SECTION_REVISIONS = 1`. This prevents infinite critique loops and runaway latency.
- **Transparent Logging:** Every verdict (`PASS` or `REVISE`), feedback snippet, and exhaustion event is logged to the JSONL audit log.

---

## 6. The Agent Harness

The **Agent Harness** represents the operational runtime and infrastructure wrapper that surrounds the multi-agent system, providing safety, execution control, and execution control:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          AGENT HARNESS LAYER                           │
│                                                                        │
│  ┌───────────────────────┐  ┌────────────────────────────────────────┐ │
│  │ Execution Runtime     │  │ Tool Sandboxing & Isolation            │ │
│  │ - Middleware Pipeline │  │ - Concurrent Tavily Search wrapper     │ │
│  │ - TaskManager State   │  │ - Thread-safe worker isolation         │ │
│  └───────────────────────┘  └────────────────────────────────────────┘ │
│  ┌───────────────────────┐  ┌────────────────────────────────────────┐ │
│  │ Safety & Rate Limits  │  │ Output Formatting Harness            │ │
│  │ - Token budget caps   │  │ - Agent-initiated follow-up questions  │ │
│  │ - Context trimming    │  │ - Recommended strategic actions        │ │
│  │ - Multi-model fallback│  │ - Continuous interactive dialogue loop │ │
│  └───────────────────────┘  └────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Tool Sandboxing & Concurrency Control:**
   - External tools (Tavily API) are encapsulated with connection management and rate limiting.
   - Multi-threading runs within managed `ThreadPoolExecutor` contexts, isolating thread exceptions and preventing orphaned tasks.
2. **Token Budget & TPM Safety Controls:**
   - Provider rate limits (e.g. Groq 8,000 TPM limit) are protected through strict context budgeting.
   - Follow-up Q&A context is capped at 3,500 characters of report summary, and output reservations are right-sized (e.g., `max_tokens=800` for Q&A, `max_tokens=300` for evaluation verdicts), preventing HTTP 413 rate-limit errors.
3. **Auditability & Observability:**
   - Every agent interaction, timestamp, attempt, model name, and prompt outcome is persisted to `data/logs/{run_id}.log.jsonl`.
---

## 7. Reasoning and Complex Task Handling

Strategic business analysis cannot be accomplished with a single naive prompt. The system uses **Context-Accumulating Prompt Chaining**:

```
Research Findings ──▶ [Comparative Analysis]
                             │
                             ▼ (Includes Analysis)
                      [Risk Assessment]
                             │
                             ▼ (Includes Analysis + Risks)
                      [Strategic Recommendations]
```

1. **Step 1 — Comparative Analysis:** Takes the product vision and research findings to establish differentiation, competitive moat, and disadvantages.
2. **Step 2 — Risk Assessment:** Ingests the comparative analysis. Instead of generating boilerplate risks, it identifies risks directly arising from the specific weaknesses found in Step 1.
3. **Step 3 — Strategic Recommendation:** Ingests both the comparative analysis and the risk assessment to form an actionable, nuanced verdict with concrete implementation milestones.

This ensures internal coherence across the entire report—the recommendations directly solve the risks identified in Step 2, which in turn stem from the competitive realities mapped in Step 1.

---

## 8. Feedback Handovers

Feedback flows across two distinct boundaries:

1. **Intra-Run Autonomous Feedback (Evaluator $\to$ Candidate Agent):**
   - When the Evaluator flags a section as `REVISE`, it returns structured critique (e.g., *"The analysis lacks pricing differentiation against Competitor X"*).
   - The harness automatically injects this feedback into the rewrite prompt:
     ```python
     current_text = self.ask(
         REVISE_SYSTEM_PROMPT,
         f"Original Section:\n{current_text}\n\nEvaluator Feedback:\n{feedback}\n\nRewrite now."
     )
     ```
   - Requires zero human intervention.
2. **Post-Run Human-in-the-Loop Feedback (User $\leftrightarrow$ Agent Harness):**
   - The Supervisor retains the entire report text, activity log, and conversation history in memory.
      - Every answer is grounded in the generated document and logged to the persistent session file.

---

## 9. Executive Word (.docx) Report Generation Engine

The backend strictly outputs Microsoft Word (`.docx`) documents to meet corporate business reporting standards:

1. **OpenXML Native Table Engine:**
   - Markdown tables (`| Col 1 | Col 2 |`) are parsed into native `python-docx` table objects.
   - Styled with **Corporate Deep Navy (`#1E3A8A`)** header shading, white bold text, subtle borders (`#CBD5E1`), alternating row shading (`#F8FAFC`), and custom cell padding.
2. **Text & Typography Sanitization:**
   - Raw `<br>` tags are parsed and replaced with native cell line breaks and separate paragraphs.
   - Informal emojis and tick marks (`✅`, `❌`, `✔`) are converted into clean corporate indicators (`Yes`, `No`, `Supported`, `None`).
   - Full-width citation brackets (`【1】`) are normalized to standard clean brackets (`[1]`).
3. **Native Headings & Formatting:**
   - Section headings (`#`, `##`, `###`) are converted into native Word `Heading 1`, `Heading 2`, and `Heading 3` with corporate typography.
   - Inline markdown (`**bold**`, `*italic*`) is parsed into distinct formatted runs.
   - Bullet and numbered lists are mapped to `List Bullet` and `List Number` styles.
4. **100% Resilient File Saving:**
   - **XML Sanitization:** Strips illegal XML 1.0 control characters (`\x00-\x08`, `\x0B-\x0C`, `\x0E-\x1F`), preventing `python-docx` / `lxml` from crashing with `ValueError`.
   - **Directory Verification:** Ensures `data/reports/` exists before saving.
   - **File-Lock Collision Handling:** Catches `PermissionError` (if the file is currently open in Microsoft Word on Windows) and appends a timestamp (`_YYYYMMDD_HHMMSS.docx`) so saving always succeeds without pipeline interruption.
   - **Emergency Backup:** Includes a fallback mechanism that writes an emergency plaintext backup in case of unforeseen OS errors.

---

## 10. Multi-Tier Error Management

Failure handling is architected defensively across four concentric boundaries:

1. **Call-Level Retries (`core/llm_client.py`):**
   - Transient network issues, rate limits (HTTP 429), or empty completions retry up to `MAX_RETRIES_PER_MODEL = 2` with exponential backoff.
2. **Provider Model Fallback Chain:**
   - If the primary model (`openai/gpt-oss-120b`) fails or exhausts rate limits, the client automatically advances to fallback models (`openai/gpt-oss-20b`, `groq/compound-mini`).
3. **Tool-Level Fault Isolation:**
   - Search failures for individual queries are caught and logged; the pipeline proceeds gracefully with the remaining search results rather than aborting.
4. **Conversational Loop Resilience:**
   
---

## 11. File Map

```
agent_research_backend_v3/
├── main.py                     # CLI entry point
├── config.py                   # Central settings (models, docx format, concurrency)
├── requirements.txt            # Python dependencies (openai, tavily-python, python-docx)
├── DEVELOPER_DOCUMENTATION.md  # Comprehensive architecture & design document
├── README.md                   # Operational quickstart and overview
├── agents/
│   ├── base.py                 # Abstract Agent base class with LLM binding & token control
│   ├── supervisor.py           # Orchestrator & pipeline runner
│   ├── researcher.py           # Concurrent Tavily market search agent
│   ├── comparator.py           # Chained comparative, risk, and recommendation agent
│   ├── evaluator.py            # Quality rubric auditor & bounded rewriter
│   └── skills.py               # Middleware skill wrappers (Plan, Research, Eval, Docx)
├── core/
│   ├── context.py              # Typed PipelineContext data container
│   ├── pipeline.py             # Middleware Pipeline execution engine
│   ├── llm_client.py           # OpenAI/Groq client with retry & fallback chain
│   ├── search_tool.py          # Tavily search tool wrapper
│   ├── task_manager.py         # To-do list tracking & JSONL audit logger
│   └── report_generator.py     # Professional Microsoft Word (.docx) generator
└── data/
    ├── reports/                # Generated Word documents (.docx)
    └── logs/                   # Full JSONL activity audit trails
```

---

## 12. Anti-Hallucination Framework & Grounding Contract

To ensure high-fidelity, audit-ready business intelligence, the system enforces a multi-tier **Anti-Hallucination Framework**:

1. **Deterministic Low-Temperature Sampling (`temperature=0.1`)**:
   - Configured centrally via `config.LLM_TEMPERATURE = 0.1`.
   - Prevents the model from deviating into non-factual parametric memory, locking generation to in-context retrieval.
2. **Strict Closed-World Grounding Contracts**:
   - `ResearcherAgent` and `ComparatorAgent` operate under a contractual system prompt.
   - Forbids mentioning companies, competitor entities, or numerical statistics not present in verified search context.
3. **Removal of Word-Count Inflation**:
   - Shifted from arbitrary length requirements to **information density**.
   - Eliminates the pressure that mathematically forces LLMs to pad short search contexts with invented facts.
4. **Data Gap Transparency Protocol**:
   - If pricing metrics, customer churn, or TAM are unavailable in the search data, agents write `[Requires Primary Due Diligence / Commercial Confirmation]` rather than guessing.
5. **Source Attribution & Citation Anchoring**:
   - Search results are formatted with explicit source indexing (`[Source X]`), grounding the factual lineage of every claim.
