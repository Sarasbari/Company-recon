import os
import httpx

from backend.logging_config import logger


async def web_search(query: str) -> str:
    """
    Search the web using Tavily Search API.
    Returns a configuration error if TAVILY_API_KEY is not set.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or api_key in ("mock_key", "your_tavily_api_key_here", ""):
        return (
            "Configuration Error: TAVILY_API_KEY is not set or is invalid. "
            "Please configure a valid Tavily API key to enable web search. "
            "Visit https://tavily.com to obtain a free API key."
        )

    import asyncio
    attempts = 2
    delay = 1.0

    for attempt in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": query,
                        "search_depth": "basic",
                        "include_answer": False,
                        "max_results": 4
                    }
                )
                
                if response.status_code == 429:
                    return "Error: Tavily Search API key quota exhausted. Please upgrade your Tavily plan or check your billing details."
                    
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                if not results:
                    return "No search results found."
                
                output = []
                for i, res in enumerate(results, 1):
                    title = res.get("title", "No Title")
                    url = res.get("url", "No URL")
                    snippet = res.get("content", "No content available.")
                    if len(snippet) > 600:
                        snippet = snippet[:600] + "..."
                    output.append(f"[{i}] {title}\nURL: {url}\nSnippet: {snippet}\n---")
                return "\n".join(output)
        except Exception as e:
            if attempt == attempts - 1:
                logger.error(f"Web search failed after {attempts} attempts: {str(e)}")
                return f"Error performing web search after {attempts} attempts: {str(e)}"
            await asyncio.sleep(delay)
            delay *= 2.0
