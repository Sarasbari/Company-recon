import os
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

BLOCKED_DOMAINS = ["linkedin.com", "crunchbase.com", "glassdoor.com"]

async def fetch_page(url: str) -> str:
    """
    Fetch and extract readable text content from a URL.
    Bypasses direct fetching for blocked domains like linkedin.com and crunchbase.com.
    Tries Tavily Extract, and falls back to httpx + BeautifulSoup4.
    """
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    
    # Check blocklist for scraping blocks
    if any(blocked in domain for blocked in BLOCKED_DOMAINS):
        return f"Scraping blocked for domain: {domain}. Direct crawling is prohibited on this domain to avoid bot blocks. Please rely on search snippets instead."

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or api_key == "mock_key":
        if "razorpay.com" in domain:
            return (
                "Razorpay is India's first Neobank and payment solution that helps businesses manage money. "
                "Founded in 2014 by Harshil Mathur and Shashank Kumar. Our product offering includes Payment Gateway, "
                "RazorpayX (Business Banking), Razorpay Capital (Working Capital Loans), and Payroll management. "
                "We serve over 10 million businesses of all sizes, accepting 100+ payment modes. "
                "HQ location is Bengaluru, Karnataka, India."
            )
        elif "techcrunch.com" in domain:
            return (
                "Fintech giant Razorpay co-founders Harshil Mathur and Shashank Kumar announced their Series F round of $375 million today. "
                "The round was co-led by GIC and Lone Pine Capital. It will be used for expansion into Southeast Asia markets, starting with Malaysia."
            )
        return f"Mock content for page at {url}. This domain represents information retrieved in Mock Mode."

    # Method 1: Try Tavily Extract API
    tavily_error = None
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

    # Method 2: Fallback with httpx and BeautifulSoup4
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

    # Both failed - return descriptive failure message
    return f"Failed to fetch content from {url} after trying Tavily Extract and BeautifulSoup fallback. Tavily Error: {tavily_error}. Fallback Error: {fallback_error}."
