import os
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from backend.logging_config import logger

BLOCKED_DOMAINS = ["linkedin.com", "crunchbase.com", "glassdoor.com"]


async def fetch_page(url: str) -> str:
    """
    Fetch and extract readable text content from a URL.
    Bypasses direct fetching for blocked domains like linkedin.com and crunchbase.com.
    Uses a 4-tier fallback chain:
      1. Tavily Extract API (requires TAVILY_API_KEY)
      2. Firecrawl API (requires FIRECRAWL_API_KEY)
      3. Jina Reader (free, no key needed)
      4. httpx + BeautifulSoup4 (raw fallback)
    """
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    
    # Check blocklist for scraping blocks
    if any(blocked in domain for blocked in BLOCKED_DOMAINS):
        return f"Scraping blocked for domain: {domain}. Direct crawling is prohibited on this domain to avoid bot blocks. Please rely on search snippets instead."

    # --- Method 1: Try Tavily Extract API ---
    tavily_error = None
    api_key = os.getenv("TAVILY_API_KEY")
    if api_key and api_key not in ("mock_key", "your_tavily_api_key_here", ""):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.tavily.com/extract",
                    json={
                        "api_key": api_key,
                        "urls": [url]
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if results and results[0].get("raw_content"):
                        raw_content = results[0]["raw_content"]
                        if raw_content.strip():
                            return raw_content[:4000]
                else:
                    tavily_error = f"Tavily Extract API status {response.status_code}: {response.text}"
        except Exception as e:
            tavily_error = f"Tavily Extract failed: {str(e)}"
    else:
        tavily_error = "TAVILY_API_KEY not configured, skipping Tavily Extract."

    # --- Method 2: Try Firecrawl API ---
    firecrawl_error = None
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
    if firecrawl_key and firecrawl_key not in ("mock_key", "your_firecrawl_api_key_here", ""):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    headers={
                        "Authorization": f"Bearer {firecrawl_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "url": url,
                        "formats": ["markdown"]
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    # Firecrawl v1 returns data.markdown
                    content = data.get("data", {}).get("markdown", "")
                    if content and content.strip():
                        return content[:4000]
                else:
                    firecrawl_error = f"Firecrawl API status {response.status_code}: {response.text}"
        except Exception as e:
            firecrawl_error = f"Firecrawl failed: {str(e)}"
    else:
        firecrawl_error = "FIRECRAWL_API_KEY not configured, skipping Firecrawl."

    # --- Method 3: Try Jina Reader (free, no API key needed) ---
    jina_error = None
    try:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"Accept": "text/plain"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(jina_url, headers=headers)
            if response.status_code == 200:
                content = response.text.strip()
                if content and len(content) > 50:
                    return content[:4000]
                else:
                    jina_error = "Jina Reader returned empty or very short content."
            else:
                jina_error = f"Jina Reader status {response.status_code}"
    except Exception as e:
        jina_error = f"Jina Reader failed: {str(e)}"

    # --- Method 4: Fallback with httpx and BeautifulSoup4 ---
    fallback_error = None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Strip scripts, styles, headers, footers, navs to clean up the content
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
                
            text = soup.get_text(separator=" ")
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = "\n".join(chunk for chunk in chunks if chunk)
            
            if clean_text.strip():
                return clean_text[:4000]  # Restrict response content size
            else:
                fallback_error = "Extracted page content was empty."
    except Exception as e:
        fallback_error = str(e)

    # All methods failed - return descriptive failure message
    logger.warning(f"All fetch methods failed for {url}: Tavily={tavily_error}, Firecrawl={firecrawl_error}, Jina={jina_error}, BS4={fallback_error}")
    return (
        f"Failed to fetch content from {url} after trying all available methods. "
        f"Tavily: {tavily_error}. Firecrawl: {firecrawl_error}. "
        f"Jina Reader: {jina_error}. BeautifulSoup: {fallback_error}."
    )
