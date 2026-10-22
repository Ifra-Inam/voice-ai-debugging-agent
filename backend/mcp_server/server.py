import html
import os
from urllib.parse import urlparse

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("devsearch")

SE_API = "https://api.stackexchange.com/2.3"
GH_API = "https://api.github.com"
TAVILY_API = "https://api.tavily.com/search"

TIMEOUT = httpx.Timeout(20.0)

# Official documentation sources allowed in search results.
OFFICIAL_SOURCES: dict[str, list[str]] = {
    "python": ["docs.python.org"],
    "azure": ["learn.microsoft.com"],
    "mdn": ["developer.mozilla.org"],
    "node": ["nodejs.org"],
    "react": ["react.dev"],
    "langchain": ["python.langchain.com", "docs.langchain.com"],
    "mcp": ["modelcontextprotocol.io"],
    "github": ["docs.github.com"],
    "aws": ["docs.aws.amazon.com"],
    "docker": ["docs.docker.com"],
    "kubernetes": ["kubernetes.io"],
    "postgres": ["postgresql.org"],
}

# Helpers

async def se_get(path: str, params: dict) -> dict:
    """Call the public Stack Exchange API."""
    params = {"site": "stackoverflow", **params}

    if key := os.getenv("STACKEXCHANGE_KEY"):
        params["key"] = key

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{SE_API}{path}", params=params)
        response.raise_for_status()
        return response.json()

async def gh_get(
    path: str,
    params: dict | None = None,
) -> httpx.Response:
    """Call the public GitHub API."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "devsearch-mcp",
    }

    if token := os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        headers=headers,
    ) as client:
        response = await client.get(
            f"{GH_API}{path}",
            params=params,
        )
        response.raise_for_status()
        return response

def http_error(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code

        if status in (403, 429):
            return (
                "API rate limit reached. Try again later, or optionally "
                "configure GITHUB_TOKEN or STACKEXCHANGE_KEY."
            )

        return f"Request failed with HTTP {status}."

    if isinstance(error, httpx.HTTPError):
        return f"Network error: {error}"

    return f"Search failed: {error}"

def is_official_url(url: str, domains: list[str]) -> bool:
    """Ensure a result belongs to an allowed official domain."""
    host = (urlparse(url).hostname or "").lower()

    return any(
        host == domain or host.endswith("." + domain)
        for domain in domains
    )

# MCP Tools

@mcp.tool()
async def search_stackoverflow(
    query: str,
    tags: list[str] | None = None,
) -> str:
    """Search Stack Overflow questions relevant to a technical issue.

    Args:
        query: Search text, e.g. "asyncio gather timeout".
        tags: Optional tags, e.g. ["python", "asyncio"].
    """
    params = {
        "q": query,
        "order": "desc",
        "sort": "relevance",
        "pagesize": 5,
    }

    if tags:
        params["tagged"] = ";".join(tags)

    try:
        data = await se_get("/search/advanced", params)
    except httpx.HTTPError as error:
        return http_error(error)

    items = data.get("items", [])

    if not items:
        return "No Stack Overflow results found."

    results = []

    for question in items:
        title = html.unescape(question["title"])
        accepted = bool(question.get("accepted_answer_id"))

        results.append(
            f"- {title}\n"
            f"  URL: {question['link']}\n"
            f"  Score: {question['score']} | "
            f"Answers: {question['answer_count']} | "
            f"Accepted answer: {'yes' if accepted else 'no'}\n"
            f"  Tags: {', '.join(question.get('tags', []))}"
        )

    return "\n\n".join(results)

@mcp.tool()
async def search_github_issues(query: str) -> str:
    """Search public GitHub issues for bugs and workarounds.

    Args:
        query: Search text. GitHub qualifiers are supported,
               e.g. "repo:pallets/flask is:open timeout".
    """
    try:
        response = await gh_get(
            "/search/issues",
            {
                "q": f"{query} is:issue",
                "per_page": 5,
                "sort": "best-match",
            },
        )
    except httpx.HTTPError as error:
        return http_error(error)

    data = response.json()
    items = data.get("items", [])

    if not items:
        return "No GitHub issues found."

    results = [
        f"{data.get('total_count', 0)} total matches; "
        f"showing {len(items)}:\n"
    ]

    for issue in items:
        repo = issue["repository_url"].split("/repos/")[-1]
        labels = ", ".join(
            label["name"] for label in issue.get("labels", [])
        ) or "none"

        # Keep results concise for the LLM.
        body = " ".join((issue.get("body") or "").split())[:500]

        results.append(
            f"- {issue['title']}\n"
            f"  URL: {issue['html_url']}\n"
            f"  Repository: {repo}#{issue['number']} | "
            f"State: {issue['state']} | "
            f"Comments: {issue['comments']} | "
            f"Labels: {labels}\n"
            f"  Description: {body or 'No description provided.'}"
        )

    return "\n\n".join(results)

@mcp.tool()
async def search_official_docs(
    query: str,
    source: str | None = None,
) -> str:
    """Search official technical documentation using Tavily.

    Args:
        query: What to look up, e.g.
               "ContentUnderstandingClient begin_analyze_binary".
        source: Optional source category, such as python, azure,
                react, langchain, mcp, or docker.
                Omit to search all configured official sources.
    """
    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        return (
            "Official documentation search requires TAVILY_API_KEY. "
            "Configure it in the environment used to run the MCP server."
        )

    if source:
        source = source.lower()

        if source not in OFFICIAL_SOURCES:
            return (
                f"Unknown source '{source}'. Available sources: "
                f"{', '.join(OFFICIAL_SOURCES)}."
            )

        domains = OFFICIAL_SOURCES[source]
    else:
        domains = [
            domain
            for source_domains in OFFICIAL_SOURCES.values()
            for domain in source_domains
        ]

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                TAVILY_API,
                json={
                    "api_key": api_key,
                    "query": query,
                    "include_domains": domains,
                    "max_results": 5,
                    "search_depth": "basic",
                },
            )
            response.raise_for_status()

        rows = response.json().get("results", [])

    except httpx.HTTPError as error:
        return http_error(error)

    # Verify the domains even if the search service returns
    # a result outside the requested allowlist.
    rows = [
        row for row in rows
        if is_official_url(row.get("url", ""), domains)
    ]

    if not rows:
        return "No results found in the selected official documentation."

    results = []

    for row in rows:
        title = row.get("title", "Untitled")
        url = row.get("url", "")
        snippet = " ".join(row.get("content", "").split())[:500]

        results.append(
            f"- {title}\n"
            f"  URL: {url}\n"
            f"  Summary: {snippet}"
        )

    return "\n\n".join(results)

if __name__ == "__main__":
    mcp.run()