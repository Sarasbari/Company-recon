import os
import json
import time
import asyncio
from anthropic import AsyncAnthropic
from backend.agent.prompts import build_system_prompt, SYNTHESIS_PROMPT
from backend.tools.dispatcher import dispatch_tool

MAX_ITERATIONS = 12

async def run_agent(company_name: str, queue: asyncio.Queue = None) -> dict:
    """
    Executes the ReAct agent loop for a company name.
    Streams progress events to the provided asyncio.Queue.
    Returns the final synthesized dossier.
    """
    start_time = time.time()
    
    # Send initial start event
    if queue:
        await queue.put({"type": "start", "company": company_name})
        
    gemini_key = os.getenv("GEMINI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    # Prioritize Gemini if its API key is set
    if gemini_key and gemini_key not in ("mock_key", "your_gemini_api_key_here", ""):
        return await run_gemini_agent(company_name, queue, start_time)

    if not anthropic_key or anthropic_key in ("mock_key", "your_anthropic_api_key_here", ""):
        return await run_mock_agent(company_name, queue, start_time)

    # Real agent logic
    client = AsyncAnthropic(api_key=anthropic_key)
    system_prompt = build_system_prompt(company_name)
    
    tools = [
        {
            "name": "web_search",
            "description": "Search the web for information about a company. Use specific queries. Prefer queries like 'Razorpay funding 2024 Crunchbase' over 'Razorpay'. Returns top 5 results with title, URL, and snippet.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Be specific. Include company name + topic."
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "fetch_page",
            "description": "Fetch and extract readable text content from a URL. Use for official company websites, press releases, news articles. Do NOT use for LinkedIn or Crunchbase direct pages — they block scrapers. Prefer Tavily Extract for those.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL to fetch."
                    }
                },
                "required": ["url"]
            }
        }
    ]

    messages = []
    iteration = 0
    tool_calls_count = 0
    sources_visited = set()

    try:
        while iteration < MAX_ITERATIONS:
            # Call Claude (3.5 Haiku for ReAct loop reasoning and tools dispatch)
            response = await client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
                system=system_prompt,
                tools=tools,
                messages=messages
            )

            # Extract thinking content and tool calls
            assistant_content = []
            reasoning_text = ""
            for block in response.content:
                if block.type == "text":
                    reasoning_text += block.text
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })

            # Stream reasoning to frontend
            if reasoning_text and queue:
                await queue.put({"type": "reason", "text": reasoning_text})

            messages.append({"role": "assistant", "content": assistant_content})

            if response.stop_reason == "end_turn":
                # Agent decided it has completed its research
                break

            if response.stop_reason == "tool_use":
                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
                
                tool_results = []
                for block in tool_use_blocks:
                    tool_calls_count += 1
                    tool_name = block.name
                    tool_input = block.input
                    
                    if tool_name == "fetch_page" and "url" in tool_input:
                        sources_visited.add(tool_input["url"])

                    # Stream action details
                    if queue:
                        await queue.put({
                            "type": "action",
                            "tool": tool_name,
                            "input": tool_input
                        })

                    # Run tool
                    result = await dispatch_tool(tool_name, tool_input)

                    # Stream observation
                    if queue:
                        summary = result[:300] + "..." if len(result) > 300 else result
                        await queue.put({
                            "type": "observation",
                            "tool": tool_name,
                            "summary": summary
                        })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

                messages.append({"role": "user", "content": tool_results})

            iteration += 1

        # Final Synthesis phase using Claude 3.5 Sonnet
        duration = int(time.time() - start_time)
        if queue:
            await queue.put({"type": "reason", "text": "Synthesizing research logs into structured dossier..."})

        synthesis_messages = messages + [
            {"role": "user", "content": SYNTHESIS_PROMPT}
        ]

        synthesis_response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            messages=synthesis_messages
        )

        dossier_text = ""
        for block in synthesis_response.content:
            if block.type == "text":
                dossier_text += block.text

        # Clean JSON wrappers if generated
        dossier_text = dossier_text.strip()
        if dossier_text.startswith("```json"):
            dossier_text = dossier_text[7:]
        if dossier_text.endswith("```"):
            dossier_text = dossier_text[:-3]
        dossier_text = dossier_text.strip()

        dossier = json.loads(dossier_text)
        
        # Populate agent metadata
        dossier["agent_metadata"] = {
            "iterations": iteration,
            "tool_calls": tool_calls_count,
            "duration_seconds": duration,
            "model_used": "claude-3-5-haiku + claude-3-5-sonnet"
        }
        
        # Merge sources visited
        existing_sources = set(dossier.get("sources", []))
        existing_sources.update(sources_visited)
        dossier["sources"] = list(existing_sources)

        if queue:
            await queue.put({"type": "complete", "dossier": dossier})

        return dossier

    except Exception as e:
        error_msg = f"Agent execution failed: {str(e)}"
        if queue:
            await queue.put({"type": "error", "message": error_msg})
        raise e

async def run_gemini_agent(company_name: str, queue: asyncio.Queue = None, start_time: float = None) -> dict:
    """
    Runs the ReAct loop using the free Google Gemini API.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    system_prompt = build_system_prompt(company_name)
    
    gemini_tools = [{
        "functionDeclarations": [
            {
                "name": "web_search",
                "description": "Search the web for information about a company. Use specific queries. Prefer queries like 'Razorpay funding 2024 Crunchbase' over 'Razorpay'. Returns top 5 results with title, URL, and snippet.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "The search query. Be specific. Include company name + topic."
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "fetch_page",
                "description": "Fetch and extract readable text content from a URL. Use for official company websites, press releases, news articles. Do NOT use for LinkedIn or Crunchbase direct pages — they block scrapers. Prefer Tavily Extract for those.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "url": {
                            "type": "STRING",
                            "description": "The full URL to fetch."
                        }
                    },
                    "required": ["url"]
                }
            }
        ]
    }]

    contents = []
    iteration = 0
    tool_calls_count = 0
    sources_visited = set()

    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        while iteration < MAX_ITERATIONS:
            payload = {
                "contents": contents,
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                },
                "tools": gemini_tools
            }
            
            if not contents:
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"Start researching {company_name}."}]
                })
            
            response = await client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()
            
            candidates = res_data.get("candidates", [])
            if not candidates:
                break
                
            first_candidate = candidates[0]
            content_out = first_candidate.get("content", {})
            parts = content_out.get("parts", [])
            
            contents.append(content_out)
            
            reasoning_text = ""
            function_calls = []
            
            for part in parts:
                if "text" in part:
                    reasoning_text += part["text"]
                if "functionCall" in part:
                    function_calls.append(part["functionCall"])
            
            if reasoning_text and queue:
                await queue.put({"type": "reason", "text": reasoning_text})
                
            if not function_calls:
                break
                
            tool_results_parts = []
            for call in function_calls:
                tool_calls_count += 1
                tool_name = call["name"]
                tool_input = call["args"]
                
                if tool_name == "fetch_page" and "url" in tool_input:
                    sources_visited.add(tool_input["url"])
                    
                if queue:
                    await queue.put({
                        "type": "action",
                        "tool": tool_name,
                        "input": tool_input
                    })
                    
                result = await dispatch_tool(tool_name, tool_input)
                
                if queue:
                    summary = result[:300] + "..." if len(result) > 300 else result
                    await queue.put({
                        "type": "observation",
                        "tool": tool_name,
                        "summary": summary
                    })
                    
                tool_results_parts.append({
                    "functionResponse": {
                        "name": tool_name,
                        "response": {"result": result}
                    }
                })
                
            contents.append({
                "role": "user",
                "parts": tool_results_parts
            })
            
            iteration += 1

        duration = int(time.time() - start_time)
        if queue:
            await queue.put({"type": "reason", "text": "Synthesizing research logs into structured dossier..."})
            
        synthesis_payload = {
            "contents": contents + [{
                "role": "user",
                "parts": [{"text": SYNTHESIS_PROMPT}]
            }],
            "systemInstruction": {
                "parts": [{"text": "You are a professional B2B sales analyst."}]
            },
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        synth_res = await client.post(url, json=synthesis_payload)
        synth_res.raise_for_status()
        synth_data = synth_res.json()
        
        dossier_text = synth_data["candidates"][0]["content"]["parts"][0]["text"]
        
        dossier_text = dossier_text.strip()
        if dossier_text.startswith("```json"):
            dossier_text = dossier_text[7:]
        if dossier_text.endswith("```"):
            dossier_text = dossier_text[:-3]
        dossier_text = dossier_text.strip()
        
        dossier = json.loads(dossier_text)
        
        dossier["agent_metadata"] = {
            "iterations": iteration,
            "tool_calls": tool_calls_count,
            "duration_seconds": duration,
            "model_used": "gemini-1.5-flash"
        }
        
        existing_sources = set(dossier.get("sources", []))
        existing_sources.update(sources_visited)
        dossier["sources"] = list(existing_sources)

        if queue:
            await queue.put({"type": "complete", "dossier": dossier})

        return dossier

async def run_mock_agent(company_name: str, queue: asyncio.Queue, start_time: float) -> dict:
    """
    Simulates a ReAct agent loop for testing when Anthropic/Tavily keys are not set.
    """
    comp = company_name.strip()
    
    # Mock events matching ReAct style
    steps = [
        ("reason", f"Initializing research for company '{comp}'. Searching for general overview, headquarters, founding date, and founders."),
        ("action", "web_search", {"query": f"{comp} company overview founding year headquarters founders"}),
        ("observation", "web_search", f"[1] {comp} - About Us\nURL: https://{comp.lower().replace(' ', '')}.com/about\nSnippet: Founded in 2014, {comp} is a leading technology company delivering state-of-the-art software solutions. HQ in Bengaluru, India.\n[2] Crunchbase Profile: {comp} founded 2014, HQ in India."),
        
        ("reason", "Retrieved basic founding info. Now searching for funding stage, total capital raised, and key investment leads."),
        ("action", "web_search", {"query": f"{comp} funding stage total raised investors Crunchbase"}),
        ("observation", "web_search", f"[1] Crunchbase Funding: {comp} has raised a total of $741.5M in funding over 8 rounds. Latest round: Series F.\n[2] TechCrunch: {comp} raises Series F round co-led by GIC and Lone Pine Capital."),
        
        ("reason", f"Funding details found ($741.5M total, Series F). Fetching the home page for {comp} to understand their core business model."),
        ("action", "fetch_page", {"url": f"https://{comp.lower().replace(' ', '')}.com"}),
        ("observation", "fetch_page", f"{comp} is India's leading fintech payment platform enabling merchants to accept, process, and disburse payments. Products include payment gateway, neobanking, billing APIs, and corporate cards. Trusted by over 10M+ businesses."),
        
        ("reason", f"Now searching for recent news articles and press releases about {comp} within the last 90 days."),
        ("action", "web_search", {"query": f"{comp} recent news announcements 2026"}),
        ("observation", "web_search", f"[1] TechCrunch: {comp} launches PayOut Links for B2B merchant operations.\n[2] Economic Times: {comp} announces expansion plans into Southeast Asian markets starting this quarter."),
        
        ("reason", f"Research completed for {comp}. Synthesizing collected logs into a structured dossier...")
    ]

    for step in steps:
        await asyncio.sleep(1.0)
        if not queue:
            continue
        
        stype = step[0]
        if stype == "reason":
            await queue.put({"type": "reason", "text": step[1]})
        elif stype == "action":
            await queue.put({"type": "action", "tool": step[1], "input": step[2]})
        elif stype == "observation":
            await queue.put({"type": "observation", "tool": step[1], "summary": step[2]})

    dossier = {
        "company": comp,
        "researched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overview": f"{comp} is India's leading payment solutions company, providing businesses with a suite of developer-friendly APIs to accept, process, and disburse payments. The company has evolved from a payment gateway into a full-scale financial services platform.",
        "industry": "Fintech / Financial Services",
        "business_model": "B2B SaaS / Transaction Fee",
        "founded": "2014",
        "headquarters": "Bengaluru, India",
        "headcount": "1001-5000 (estimated)",
        "funding": {
            "stage": "Series F",
            "total_raised": "$741.5M",
            "last_round": "$375M (2021)",
            "investors": ["GIC", "Lone Pine Capital", "Tiger Global", "Sequoia Capital India"]
        },
        "key_people": [
            { "name": "Harshil Mathur", "role": "CEO & Co-founder" },
            { "name": "Shashank Kumar", "role": "CTO & Co-founder" }
        ],
        "recent_news": [
            {
                "title": f"{comp} launches PayOut Links for B2B payments",
                "url": f"https://techcrunch.com/2026/06/{comp.lower()}-payout-links",
                "date": "3 days ago",
                "summary": f"The new service allows merchants to make bulk transfers and track payables through dynamic, automated web links."
            },
            {
                "title": f"Fintech leader {comp} expands merchant offerings in Southeast Asia",
                "url": f"https://economictimes.com/{comp.lower()}-sea-expansion",
                "date": "1 week ago",
                "summary": f"{comp} is scaling operations in Southeast Asian markets, following the acquisition of Curlec in Malaysia."
            }
        ],
        "talking_points": [
            f"{comp}'s expansion into Southeast Asia aligns with cross-border commerce growth; their local payment API integrations could be a major value add.",
            f"Having raised a Series F round co-led by GIC, {comp} is well-capitalized and likely scaling its infrastructure. Focus outreach on scalability and enterprise-grade reliability.",
            f"The recently launched PayOut Links feature indicates a strong push into B2B payouts. Suggest how your product integrates with payout workflows to streamline their new offering."
        ],
        "sources": [
            f"https://{comp.lower().replace(' ', '')}.com",
            "https://www.crunchbase.com",
            "https://techcrunch.com",
            "https://economictimes.indiatimes.com"
        ],
        "agent_metadata": {
            "iterations": 4,
            "tool_calls": 4,
            "duration_seconds": int(time.time() - start_time),
            "model_used": "Mock ReAct Agent (API Key Bypass)"
        }
    }

    await asyncio.sleep(1.0)
    if queue:
        await queue.put({"type": "complete", "dossier": dossier})

    return dossier
