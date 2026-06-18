import os
import json
import time
import asyncio
from anthropic import AsyncAnthropic
from backend.agent.prompts import build_system_prompt, SYNTHESIS_PROMPT
from backend.tools.dispatcher import dispatch_tool

MAX_ITERATIONS = 12

def validate_dossier_company(requested_name: str, dossier: dict) -> bool:
    """
    Asserts that the generated dossier's company name matches the requested company name (fuzzy/substring check).
    """
    if not dossier or "company" not in dossier:
        return False
    
    req_clean = requested_name.strip().lower()
    gen_clean = str(dossier["company"]).strip().lower()
    
    # Check simple substring matches
    if req_clean in gen_clean or gen_clean in req_clean:
        return True
        
    # Clean up corporate suffixes (e.g. Inc, Ltd, Co, Corp, Limited)
    suffixes = ["inc.", "inc", "ltd.", "ltd", "corp.", "corp", "co.", "co", "limited", "pvt", "private"]
    for s in suffixes:
        req_clean = req_clean.replace(s, "")
        gen_clean = gen_clean.replace(s, "")
        
    req_clean = req_clean.strip()
    gen_clean = gen_clean.strip()
    
    if req_clean in gen_clean or gen_clean in req_clean:
        return True
        
    return False

def populate_agent_metadata(dossier: dict, iteration: int, tool_calls: int, duration: int, model: str, queue: asyncio.Queue = None):
    """
    Safely populates agent metadata in the dossier, including execution steps if the queue has history.
    """
    dossier["agent_metadata"] = {
        "iterations": iteration,
        "tool_calls": tool_calls,
        "duration_seconds": duration,
        "model_used": model
    }
    if queue and hasattr(queue, "history"):
        dossier["agent_metadata"]["steps"] = list(queue.history)

async def run_agent(company_name: str, queue: asyncio.Queue = None) -> dict:
    """
    Executes the ReAct agent loop for a company name with retry on validation failure.
    """
    for attempt in range(2):
        try:
            dossier = await _run_agent_internal(company_name, queue)
            if validate_dossier_company(company_name, dossier):
                return dossier
                
            print(f"Validation warning (Attempt {attempt + 1}): generated company name '{dossier.get('company')}' did not match requested '{company_name}'.")
            if attempt == 1:
                raise ValueError(f"Dossier validation failed: generated company '{dossier.get('company')}' does not match requested '{company_name}' after retry.")
                
            if queue:
                await queue.put({"type": "reason", "text": f"Dossier validation failed (got '{dossier.get('company')}'). Retrying research for '{company_name}'..."})
        except Exception as e:
            if attempt == 1:
                raise e

async def _run_agent_internal(company_name: str, queue: asyncio.Queue = None) -> dict:
    """
    Internal ReAct agent runner.
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
        populate_agent_metadata(dossier, iteration, tool_calls_count, duration, "claude-3-5-haiku + claude-3-5-sonnet", queue)
        
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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
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
        
        populate_agent_metadata(dossier, iteration, tool_calls_count, duration, "gemini-2.0-flash", queue)
        
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
    comp_lower = comp.lower()

    # Pre-defined mock data for specific test companies
    mock_db = {
        "zomato": {
            "overview": "Zomato is a leading multinational restaurant aggregator and food delivery company. It provides information, menus, and user-reviews of restaurants as well as food delivery options from partner restaurants in select cities.",
            "industry": "Internet / Food Delivery / Quick Commerce",
            "business_model": "Transactional Commission / Hyperlocal Logistics",
            "founded": "2008",
            "headquarters": "Gurugram, Haryana, India",
            "headcount": "5001-10000 (estimated)",
            "funding": {
                "stage": "Public (NSE: ZOMATO)",
                "total_raised": "$2.1B",
                "last_round": "IPO (July 2021)",
                "investors": ["Info Edge", "Ant Group", "Tiger Global Management", "Temasek Holdings"]
            },
            "key_people": [
                { "name": "Deepinder Goyal", "role": "CEO & Founder" },
                { "name": "Akshant Goyal", "role": "CFO" }
            ],
            "recent_news": [
                {
                    "title": "Zomato's Blinkit expansion outpaces competitors in major metro regions",
                    "url": "https://economictimes.indiatimes.com/zomato-blinkit-expansion",
                    "date": "2 weeks ago",
                    "summary": "Blinkit has significantly scaled its dark store count to meet surging demand in Noida, Gurugram, and Bengaluru."
                },
                {
                    "title": "Zomato announces record quarterly profits matching expectations",
                    "url": "https://moneycontrol.com/zomato-q4-results",
                    "date": "1 month ago",
                    "summary": "Consolidated net profit rose as margins improved in both food delivery and quick commerce segments."
                }
            ],
            "talking_points": [
                "Zomato is aggressively scaling its quick commerce arm, Blinkit. Suggesting solutions tailored for dark store routing could support their high-density logistics optimization.",
                "With deep market share in Indian metropolitan areas, pitch scaling solutions that help Zomato expand into tier-2 and tier-3 towns efficiently.",
                "Zomato's continuous focus on customer retention through loyalty benefits makes personalization tech a high-value pitch for their customer support teams."
            ],
            "sources": ["https://www.zomato.com", "https://economictimes.indiatimes.com", "https://moneycontrol.com"]
        },
        "stripe": {
            "overview": "Stripe is a global financial infrastructure platform that lets businesses accept payments, grow their revenue, and run their operations online. It serves millions of companies, from startups to large enterprises.",
            "industry": "Fintech / Payment Processing",
            "business_model": "B2B SaaS / Transaction Fee",
            "founded": "2010",
            "headquarters": "San Francisco, California, USA",
            "headcount": "5001-10000 (estimated)",
            "funding": {
                "stage": "Private (Late Stage)",
                "total_raised": "$8.7B",
                "last_round": "$6.5B (March 2023)",
                "investors": ["Sequoia Capital", "Andreessen Horowitz", "Thrive Capital", "Founders Fund"]
            },
            "key_people": [
                { "name": "Patrick Collison", "role": "CEO & Co-founder" },
                { "name": "John Collison", "role": "President & Co-founder" }
            ],
            "recent_news": [
                {
                    "title": "Stripe launches new AI-powered checkout routing features",
                    "url": "https://techcrunch.com/stripe-ai-checkout",
                    "date": "10 days ago",
                    "summary": "The update automatically routes payments through the most cost-effective provider to optimize conversion rates."
                },
                {
                    "title": "Fintech leader Stripe crosses $1 trillion in total payment volume",
                    "url": "https://wsj.com/stripe-1-trillion-tpv",
                    "date": "1 month ago",
                    "summary": "Annual payment volume grew significantly as enterprises shifted more volume to Stripe's core APIs."
                }
            ],
            "talking_points": [
                "Stripe's crossing of $1T in TPV presents a major scale opportunity. Propose high-availability cloud migration integrations for high-volume transactions.",
                "With their newly launched AI-powered checkout, show how your solution helps validate and secure input data before reaching Stripe APIs.",
                "Since Stripe serves millions of platforms globally, pitch localized billing compliance management tools for their cross-border users."
            ],
            "sources": ["https://stripe.com", "https://techcrunch.com", "https://www.wsj.com"]
        },
        "tata motors": {
            "overview": "Tata Motors Limited is a leading global automobile manufacturer of cars, utility vehicles, buses, trucks, and defense vehicles. It is part of the multi-billion dollar Tata group.",
            "industry": "Automotive / Manufacturing",
            "business_model": "Direct Sales / B2B Distribution",
            "founded": "1945",
            "headquarters": "Mumbai, Maharashtra, India",
            "headcount": "10000+ (estimated)",
            "funding": {
                "stage": "Public (NSE: TATAMOTORS)",
                "total_raised": "$2.3B",
                "last_round": "Public Markets",
                "investors": ["Tata Sons", "Life Insurance Corporation of India", "Mutual Funds"]
            },
            "key_people": [
                { "name": "Natarajan Chandrasekaran", "role": "Chairman" },
                { "name": "Guenter Butschek", "role": "CEO & Managing Director" }
            ],
            "recent_news": [
                {
                    "title": "Tata Motors dominates Indian EV passenger vehicle sector",
                    "url": "https://autocarindia.com/tata-motors-ev-dominance",
                    "date": "3 weeks ago",
                    "summary": "Tata Motors reports recording highest EV sales in India, powered by demand for Nexon and Punch EV models."
                },
                {
                    "title": "Tata Motors signs memorandum for manufacturing expansion",
                    "url": "https://reuters.com/tata-motors-tamil-nadu-plant",
                    "date": "2 months ago",
                    "summary": "The automaker will invest in setting up a state-of-the-art vehicle assembly plant in Tamil Nadu."
                }
            ],
            "talking_points": [
                "Tata Motors' EV sector dominance is a key vector. Propose smart battery management system optimizations for passenger fleets.",
                "Given their manufacturing expansion in Tamil Nadu, offer automated factory logistics scheduling integrations.",
                "Highlight how your supply chain validation platform can help Tata Motors audit compliance across regional suppliers."
            ],
            "sources": ["https://www.tatamotors.com", "https://www.reuters.com", "https://www.autocarindia.com"]
        },
        "notion": {
            "overview": "Notion is a single space where you can think, write, and plan. Capture thoughts, manage projects, or even run an entire company — and customize it exactly the way you want.",
            "industry": "Software / B2B SaaS / Collaboration",
            "business_model": "B2C / B2B Subscription SaaS",
            "founded": "2013",
            "headquarters": "San Francisco, California, USA",
            "headcount": "501-1000 (estimated)",
            "funding": {
                "stage": "Private (Late Stage)",
                "total_raised": "$343M",
                "last_round": "$275M (October 2021)",
                "investors": ["Index Ventures", "Sequoia Capital", "Coatue Management", "Base10 Partners"]
            },
            "key_people": [
                { "name": "Ivan Zhao", "role": "CEO & Co-founder" },
                { "name": "Simon Last", "role": "Co-founder" }
            ],
            "recent_news": [
                {
                    "title": "Notion launches Notion Sites to revolutionize public wikis",
                    "url": "https://techcrunch.com/notion-sites-launch",
                    "date": "1 week ago",
                    "summary": "The feature allows users to deploy high-speed, customized websites directly from their workspace databases."
                },
                {
                    "title": "Notion integrates advanced generative AI features into core editor",
                    "url": "https://theverge.com/notion-ai-workspace",
                    "date": "1 month ago",
                    "summary": "Users can now invoke AI agents to summarize meetings, autofill project reports, and translate docs."
                }
            ],
            "talking_points": [
                "Notion's Sites launch indicates a focus on web deployment. Offer caching and SEO audit tooling integrations for Notion public pages.",
                "Pitch automated integration tools that bridge third-party databases with Notion's core workspace dynamically.",
                "Notion AI's expansion opens conversational API integrations; propose secure vector DB syncing pipelines."
            ],
            "sources": ["https://www.notion.so", "https://techcrunch.com", "https://www.theverge.com"]
        },
        "wave": {
            "overview": "Wave is a fintech company offering mobile money services in Francophone Africa. It provides users with free deposits, withdrawals, and bill payments via a QR-code card and mobile app.",
            "industry": "Fintech / Mobile Money",
            "business_model": "B2C Financial Services",
            "founded": "2018",
            "headquarters": "Dakar, Senegal",
            "headcount": "1001-5000 (estimated)",
            "funding": {
                "stage": "Series A",
                "total_raised": "$200M",
                "last_round": "$200M (September 2021)",
                "investors": ["Stripe", "Founders Fund", "Ribbit Capital", "Sequoia Capital Heritage"]
            },
            "key_people": [
                { "name": "Drew Durbin", "role": "CEO & Co-founder" },
                { "name": "Lincoln Quirk", "role": "Co-founder" }
            ],
            "recent_news": [
                {
                    "title": "Fintech unicorn Wave expands mobile money services in Cote d'Ivoire",
                    "url": "https://bloomberg.com/wave-Cote-d-Ivoire",
                    "date": "3 weeks ago",
                    "summary": "Wave reports high user adoption as it challenges incumbent telecom carriers with a zero-fee transaction model."
                },
                {
                    "title": "Wave secures regulatory license to operate banking services",
                    "url": "https://techcabal.com/wave-banking-license",
                    "date": "2 months ago",
                    "summary": "The central bank grants Wave authority to offer direct savings and credit services in Senegal."
                }
            ],
            "talking_points": [
                "Wave's expansion in Cote d'Ivoire highlights rapid user growth. Propose offline-capable transaction syncing protocols to bypass local connection dropouts.",
                "With their new banking license, pitch secure KYC verification pipelines to onboard credit applicants fast.",
                "Highlight how your transactional analytics suite can help Wave detect mobile money fraud patterns in real-time."
            ],
            "sources": ["https://www.wave.com", "https://www.bloomberg.com", "https://techcabal.com"]
        },
        "razorpay": {
            "overview": "Razorpay is India's leading payment solutions company, providing businesses with a suite of developer-friendly APIs to accept, process, and disburse payments. The company has evolved from a payment gateway into a full-scale financial services platform.",
            "industry": "Fintech / Financial Services",
            "business_model": "B2B SaaS / Transaction Fee",
            "founded": "2014",
            "headquarters": "Bengaluru, Karnataka, India",
            "headcount": "1001-5000 (estimated)",
            "funding": {
                "stage": "Series F",
                "total_raised": "$741.5M",
                "last_round": "$375M (Dec 2021)",
                "investors": ["GIC", "Lone Pine Capital", "Tiger Global", "Sequoia Capital India"]
            },
            "key_people": [
                { "name": "Harshil Mathur", "role": "CEO & Co-founder" },
                { "name": "Shashank Kumar", "role": "CTO & Co-founder" }
            ],
            "recent_news": [
                {
                    "title": "Razorpay launches PayOut Links for B2B merchant operations",
                    "url": "https://techcrunch.com/razorpay-payout-links",
                    "date": "3 days ago",
                    "summary": "The new service allows merchants to make bulk transfers and track payables through dynamic, automated web links."
                },
                {
                    "title": "Fintech leader Razorpay expands merchant offerings in Southeast Asia",
                    "url": "https://economictimes.indiatimes.com/razorpay-sea-expansion",
                    "date": "1 week ago",
                    "summary": "Razorpay is scaling operations in Southeast Asian markets, following the acquisition of Curlec in Malaysia."
                }
            ],
            "talking_points": [
                "Razorpay's expansion into Southeast Asia aligns with cross-border commerce growth; their local payment API integrations could be a major value add.",
                "Having raised a Series F round co-led by GIC, Razorpay is well-capitalized and likely scaling its infrastructure. Focus outreach on scalability and enterprise-grade reliability.",
                "The recently launched PayOut Links feature indicates a strong push into B2B payouts. Suggest how your product integrates with payout workflows to streamline their new offering."
            ],
            "sources": ["https://razorpay.com", "https://www.crunchbase.com", "https://techcrunch.com", "https://economictimes.indiatimes.com"]
        }
    }

    # Find matching company mock details or use generic fallback
    selected_mock = None
    for key, val in mock_db.items():
        if key in comp_lower or comp_lower in key:
            selected_mock = val
            comp = key.title()
            break
            
    if not selected_mock:
        # Generic fallback Early Stage SaaS template
        comp_clean = comp.title()
        domain_mock = comp.lower().replace(" ", "") + ".com"
        selected_mock = {
            "overview": f"{comp_clean} is a growing technology company focused on delivering software products and digital experiences. The firm leverages modern tools to serve clients across global markets.",
            "industry": "Technology / Software",
            "business_model": "B2B SaaS / Services",
            "founded": "2020",
            "headquarters": "San Francisco, California, USA",
            "headcount": "101-500 (estimated)",
            "funding": {
                "stage": "Seed / Early Stage",
                "total_raised": "$5.0M",
                "last_round": "$5.0M Seed (2024)",
                "investors": ["Angel Investors", "Early-stage VC fund"]
            },
            "key_people": [
                { "name": f"Alex Rivers", "role": "CEO & Founder" }
            ],
            "recent_news": [
                {
                    "title": f"{comp_clean} announces launch of new developer tools suite",
                    "url": f"https://techcrunch.com/{comp.lower()}-dev-tools",
                    "date": "3 days ago",
                    "summary": f"The company has released their next-gen APIs to accelerate client integration speed by up to 50%."
                }
            ],
            "talking_points": [
                f"{comp_clean}'s new developer tools suite indicates active feature shipping. Suggesting automated testing and CI/CD tools could align with their roadmap.",
                f"As an early-stage startup, highlighting cost efficiency and developer speed can be a strong value driver for outreach.",
                f"Highlight integration compatibility to show how they can layer your solution over their new APIs easily."
            ],
            "sources": [f"https://{domain_mock}", "https://techcrunch.com"]
        }

    # Extract mock fields
    overview = selected_mock["overview"]
    industry = selected_mock["industry"]
    business_model = selected_mock["business_model"]
    founded = selected_mock["founded"]
    headquarters = selected_mock["headquarters"]
    headcount = selected_mock["headcount"]
    funding = selected_mock["funding"]
    key_people = selected_mock["key_people"]
    recent_news = selected_mock["recent_news"]
    talking_points = selected_mock["talking_points"]
    sources = selected_mock["sources"]

    # Construct mock streaming events
    domain_clean = comp.lower().replace(" ", "") + ".com"
    steps = [
        ("reason", f"Initializing research for company '{comp}'. Searching for general overview, headquarters, founding date, and founders."),
        ("action", "web_search", {"query": f"{comp} company overview founding year headquarters founders"}),
        ("observation", "web_search", f"[1] {comp} - About Us\nURL: https://{domain_clean}\nSnippet: Founded in {founded}, {comp} is a leading player in the {industry} sector. HQ in {headquarters}.\n[2] Crunchbase Profile: {comp} founded {founded}, HQ in {headquarters}."),
        
        ("reason", f"Retrieved basic founding info. Now searching for funding stage, total capital raised, and key investment leads for {comp}."),
        ("action", "web_search", {"query": f"{comp} funding stage total raised investors Crunchbase"}),
        ("observation", "web_search", f"[1] Crunchbase Funding: {comp} has raised a total of {funding['total_raised']} in funding. Latest round: {funding['stage']}.\n[2] News: {comp} funding updates detail key leads including {', '.join(funding['investors'][:2])}."),
        
        ("reason", f"Funding details found ({funding['total_raised']} total, {funding['stage']}). Fetching the home page for {comp} to understand their core business model."),
        ("action", "fetch_page", {"url": f"https://{domain_clean}"}),
        ("observation", "fetch_page", f"{overview} Operations are categorized under {industry} with a {business_model} model. Primary stakeholders include key leaders: {', '.join([kp['name'] for kp in key_people])}."),
        
        ("reason", f"Now searching for recent news articles and press releases about {comp} within the last 90 days."),
        ("action", "web_search", {"query": f"{comp} recent news announcements 2026"}),
        ("observation", "web_search", f"[1] News: {recent_news[0]['title']}\nURL: {recent_news[0]['url']}\nSnippet: {recent_news[0]['summary']}"),
        
        ("reason", f"Research completed for {comp}. Synthesizing collected logs into a structured dossier...")
    ]

    for step in steps:
        await asyncio.sleep(0.5)
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
        "overview": overview,
        "industry": industry,
        "business_model": business_model,
        "founded": founded,
        "headquarters": headquarters,
        "headcount": headcount,
        "funding": funding,
        "key_people": key_people,
        "recent_news": recent_news,
        "talking_points": talking_points,
        "sources": sources
    }

    populate_agent_metadata(dossier, 4, 4, int(time.time() - start_time), "Mock ReAct Agent (API Key Bypass)", queue)

    await asyncio.sleep(0.5)
    if queue:
        await queue.put({"type": "complete", "dossier": dossier})

    return dossier

