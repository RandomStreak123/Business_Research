"""
Pluggable search tool for the Researcher agent.

Uses Tavily (tavily.com) — a search API built for AI agents, with a
free tier. Requires TAVILY_API_KEY to be set in your environment.
"""

import os
from typing import TypedDict

from tavily import TavilyClient

_client: TavilyClient | None = None


class SearchResult(TypedDict):
    title: str
    snippet: str
    url: str


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError(
                "TAVILY_API_KEY is not set. Get a free key at "
                "https://tavily.com and run:\n"
                "  export TAVILY_API_KEY=your_key_here"
            )
        _client = TavilyClient(api_key=api_key)
    return _client


def search(query: str, max_results: int = 5) -> list[SearchResult]:
    client = _get_client()
    response = client.search(query=query, max_results=max_results)

    return [
        {
            "title": r.get("title", ""),
            "snippet": r.get("content", ""),
            "url": r.get("url", ""),
        }
        for r in response.get("results", [])
    ]
