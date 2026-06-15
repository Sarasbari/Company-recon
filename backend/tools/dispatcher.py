from backend.tools.search import web_search
from backend.tools.fetch import fetch_page

async def dispatch_tool(name: str, arguments: dict) -> str:
    """
    Dispatches tool calls by name and feeds them the parsed arguments.
    """
    if name == "web_search":
        query = arguments.get("query")
        if not query:
            return "Error: Missing 'query' parameter."
        return await web_search(query)
    elif name == "fetch_page":
        url = arguments.get("url")
        if not url:
            return "Error: Missing 'url' parameter."
        return await fetch_page(url)
    else:
        return f"Error: Unknown tool '{name}'."
