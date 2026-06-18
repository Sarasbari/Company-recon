import os
import httpx

async def web_search(query: str) -> str:
    """
    Search the web using Tavily Search API.
    If TAVILY_API_KEY is not configured or is a mock key, returns realistic mock search results.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or api_key == "mock_key":
        q_lower = query.lower()
        if "overview" in q_lower or "about" in q_lower or "founded" in q_lower:
            return (
                "[1] Razorpay - About Us\n"
                "URL: https://razorpay.com/about/\n"
                "Snippet: Razorpay is India's leading payments and developer APIs solution, founded in 2014 by Harshil Mathur and Shashank Kumar. It helps businesses accept, process, and disburse payments.\n"
                "---\n"
                "[2] Razorpay on Crunchbase\n"
                "URL: https://www.crunchbase.com/organization/razorpay\n"
                "Snippet: Razorpay is a financial services company offering a payment gateway, suite of payments API, and banking solutions. HQ in Bengaluru, Karnataka, India.\n"
                "---\n"
            )
        elif "funding" in q_lower or "raised" in q_lower or "investors" in q_lower:
            return (
                "[1] Razorpay Funding Rounds - Crunchbase\n"
                "URL: https://www.crunchbase.com/organization/razorpay/funding_rounds\n"
                "Snippet: Razorpay has raised a total of $741.5M in funding over 8 rounds. Their latest funding was raised on Dec 20, 2021, from a Series F round led by GIC and Lone Pine Capital.\n"
                "---\n"
                "[2] TechCrunch: Razorpay raises $375M at $7.5B valuation\n"
                "URL: https://techcrunch.com/2021/12/19/razorpay-raises-375m-series-f/\n"
                "Snippet: Indian fintech startup Razorpay has raised $375 million in its Series F funding round, co-led by Lone Pine Capital, Alkeon Capital, and TCV, valuing the firm at $7.5 billion.\n"
                "---\n"
            )
        elif "news" in q_lower or "recent" in q_lower:
            return (
                "[1] TechCrunch: Razorpay Launches New UPI Products\n"
                "URL: https://techcrunch.com/2024/05/20/razorpay-upi-products-india/\n"
                "Snippet: Razorpay has announced several new payment products focusing on UPI payments, supporting offline and online merchants across India.\n"
                "---\n"
                "[2] Economic Times: Razorpay Expansion into SE Asia\n"
                "URL: https://economictimes.indiatimes.com/tech/startups/razorpays-southeast-asia-expansion\n"
                "Snippet: Razorpay is expanding its footprint in Southeast Asia, starting with Curlec acquisition in Malaysia, to provide cross-border business payments.\n"
                "---\n"
            )
        else:
            return (
                f"[1] Search result for '{query}'\n"
                "URL: https://example.com/company\n"
                f"Snippet: This is a placeholder search result for the query '{query}' in mock mode.\n"
                "---\n"
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
                        "max_results": 5
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
                    output.append(f"[{i}] {title}\nURL: {url}\nSnippet: {snippet}\n---")
                return "\n".join(output)
        except Exception as e:
            if attempt == attempts - 1:
                return f"Error performing web search after {attempts} attempts: {str(e)}"
            await asyncio.sleep(delay)
            delay *= 2.0
