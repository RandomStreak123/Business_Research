# Agent Research Backend — Enterprise Business Edition

A high-speed, terminal-based multi-agent system designed for business and corporate strategy teams. It turns a product or business idea into an executive-ready market, competitor, and risk research report delivered strictly as a formatted **Microsoft Word (.docx)** document.

See [`DEVELOPER_DOCUMENTATION.md`](file:///Ubuntu-22.04/home/ajith/agent_research_backend_v3/DEVELOPER_DOCUMENTATION.md) for the complete architecture guide covering candidate delegation, the Agent Harness, reasoning chains, evaluation rubrics, and error management.

---

## Testing

Run the automated unit test suite (no external API calls required):

`ash
python3 -m unittest discover tests
# or with pytest:
pytest
`
---

## Core Capabilities

- **Strict Microsoft Word (.docx) Delivery**: Generates structured Word documents featuring executive typography, metadata callout tables, and formatted lists. No Markdown files are generated.
- **High-Speed Concurrency**: Parallelized Tavily web search queries and concurrent multi-section quality evaluations cut pipeline execution time by up to 65%.
- **Dynamic Planning & Task Tracking**: Automatically creates a custom 4–6 step task plan for each business idea, tracking progress live in the activity log.
- **Independent Quality Evaluation**: An adversarial Evaluator agent audits all analytical sections against an explicit 4-point rubric (Specificity, Grounding, Completeness, Internal Consistency) with bounded rewrites.

---

## Setup

```bash
cd /home/ajith/agent_research_backend_v3
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
export GROQ_API_KEY=your_groq_key_here
export TAVILY_API_KEY=your_tavily_key_here
```

API Keys:
- **Groq**: Free tier available at [console.groq.com/keys](https://console.groq.com/keys)
- **Tavily**: Free search tier available at [tavily.com](https://tavily.com)

---

## Run

```bash
python main.py
```

### Execution Flow
1. **Input**: Enter your business/product concept.
2. **Scoping**: Specify an optional competitor focus and research depth (`quick` or `deep`).
3. **Execution**: Watch live progress as agents plan, search, analyze, evaluate, and compile your Word report.
4. **Output**: Your report is saved directly to `data/reports/<idea_slug>_<run_id>.docx`.

---

## Architecture Overview

```
Supervisor (Orchestrator)
   │
   ├── PlanningSkill (Formulates 4-6 dynamic tasks)
   ├── ProductIdeaSkill (Structures executive vision)
   ├── ResearchSkill ──▶ Researcher Agent (Concurrent Tavily Search)
   ├── AnalysisSkill ──▶ Comparator Agent (Chained Competitive & Risk Analysis)
   ├── EvaluationSkill ─▶ Evaluator Agent (Concurrent 4-Point Rubric Audits)
   ├── SummarySkill (Synthesizes executive summary within token budgets)
   └── ReportSkill (Builds styled Microsoft Word .docx report)
```