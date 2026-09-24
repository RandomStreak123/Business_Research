"""
Researcher agent.

Job: given a product/business idea, extract high-signal search keywords,
execute high-speed concurrent web searches (Tavily), and write up
strictly grounded market & competitor findings with source attribution.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from agents.base import Agent
from config import SEARCH_MAX_WORKERS
from core.search_tool import search

SYSTEM_PROMPT = """You are a senior market research intelligence analyst. Given a \
product/business idea and verified live search results, write a dense, factually \
grounded market & competitor research section for an executive business report.

STRICT ANTI-HALLUCINATION & FORMAT CONTRACT:
1. CLOSED-WORLD GROUNDING: Document ONLY the competitors, companies, and market facts \
explicitly present in the supplied search results. You are strictly forbidden from inventing \
competitor names, hypothetical partnerships, or speculative statistics.
2. CITATION REQUIREMENT: When citing competitor features, pricing, or market trends, \
explicitly cite the source using [Source X].
3. DENSITY OVER LENGTH: Focus on dense, high-signal intelligence rather than padding. \
If critical data points (such as pricing or churn) are missing from the search results, \
explicitly note '[Data Gap: Requires Primary Market Verification]'.
4. PROFESSIONAL EXECUTIVE FORMATTING: Do NOT use raw HTML tags such as <br> or <b> in tables or text. \
Do NOT use informal emojis or tick marks (such as ✅, ❌, ✔). Use clear, professional corporate terminology \
such as 'Yes', 'No', 'Supported', 'None', 'Not Available'. Use clean standard Markdown tables and lists.
5. STRUCTURE: Group your findings into:
   - Direct Competitors & Established Solutions (with citations)
   - Indirect Alternatives & Adjacent Products
   - Market Gaps & Unaddressed Customer Pain Points."""

MAX_RESULTS_IN_PROMPT = 10
SNIPPET_CHAR_LIMIT = 240


def _extract_core_keywords(text: str, max_words: int = 7) -> str:
    """Extract clean, high-signal keywords from a potentially verbose business idea."""
    stop_words = {"a", "an", "the", "and", "or", "for", "with", "that", "this", "to", "in", "on", "of", "service", "platform"}
    words = [w for w in text.strip().split() if w.lower() not in stop_words]
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])


class ResearcherAgent(Agent):
    name = "researcher"

    def run(self, idea: str, focus_competitor: str = "", depth: str = "quick") -> str:
        task_id = "research_market"
        self.tm.add_task(task_id, "Research competitors & existing products", self.name)
        self.tm.start_task(task_id)

        keywords = _extract_core_keywords(idea)

        queries = [
            f"{keywords} competitors",
            f"{keywords} alternatives",
            f"{keywords} market landscape",
        ]
        if focus_competitor:
            queries.append(f"{focus_competitor} product pricing features")

        max_results = 4 if depth == "deep" else 3

        # Execute searches concurrently for minimum latency
        all_results = []
        seen_urls = set()

        with ThreadPoolExecutor(max_workers=min(len(queries), SEARCH_MAX_WORKERS)) as executor:
            future_to_query = {executor.submit(search, q, max_results=max_results): q for q in queries}
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    results = future.result()
                    self.tm.log("search_executed", self.name, f"query='{query}' results={len(results)}")
                    for r in results:
                        url = r.get("url", "")
                        if url and url in seen_urls:
                            continue
                        if url:
                            seen_urls.add(url)
                        all_results.append(r)
                except Exception as exc:
                    self.tm.log("search_failed", self.name, f"query='{query}' error={exc}")

        capped_results = all_results[:MAX_RESULTS_IN_PROMPT]
        results_blob = "\n".join(
            f"[Source {idx+1}] {r.get('title', 'Unknown')}\n"
            f"URL: {r.get('url', '')}\n"
            f"Summary: {r.get('snippet', '')[:SNIPPET_CHAR_LIMIT]}\n"
            for idx, r in enumerate(capped_results)
        )

        focus_instruction = (
            f"\n\nTarget Competitor Focus: The user specifically requested deep comparative analysis "
            f"against '{focus_competitor}'. Prioritize findings on this competitor if available."
            if focus_competitor else ""
        )

        prompt = (
            f"Product / Business Idea:\n{idea}\n\n"
            f"Verified Live Web Search Results:\n{results_blob}\n\n"
            f"Write the grounded market & competitor research section now, adhering strictly to the Anti-Hallucination Contract."
            f"{focus_instruction}"
        )
        output = self.ask(SYSTEM_PROMPT, prompt)
        self.tm.complete_task(task_id, result_summary=f"{len(output.split())} words produced")
        return output
