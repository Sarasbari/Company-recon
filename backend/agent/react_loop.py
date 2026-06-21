import os
import json
import time
import asyncio
import httpx
from anthropic import AsyncAnthropic
from backend.agent.prompts import build_system_prompt, SYNTHESIS_PROMPT
from backend.tools.dispatcher import dispatch_tool
from backend.models import Dossier
from backend.logging_config import logger

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


def validate_dossier_with_pydantic(dossier_dict: dict) -> dict:
    """
    Validates a raw dossier dict through the Pydantic Dossier model.
    Returns a cleaned, validated dict. Falls back to the raw dict if validation fails.
    """
    try:
        validated = Dossier.model_validate(dossier_dict)
        return validated.model_dump()
    except Exception as e:
        logger.warning(f"Pydantic validation warning (non-fatal): {str(e)}")
        return dossier_dict


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
                
            logger.warning(f"Validation warning (Attempt {attempt + 1}): generated company name '{dossier.get('company')}' did not match requested '{company_name}'.")
            if attempt == 1:
                raise ValueError(f"Dossier validation failed: generated company '{dossier.get('company')}' does not match requested '{company_name}' after retry.")
                
            if queue:
                await queue.put({"type": "reason", "text": f"Dossier validation failed (got '{dossier.get('company')}'). Retrying research for '{company_name}'..."})
        except Exception as e:
            if attempt == 1:
                raise e


async def _run_agent_internal(company_name: str, queue: asyncio.Queue = None) -> dict:
    """
    Internal ReAct agent runner. Routes to the appropriate LLM provider.
    Priority: Gemini > Groq > Anthropic.
    Raises ValueError if no LLM API key is configured.
    """
    start_time = time.time()
    
    # Send initial start event
    if queue:
        await queue.put({"type": "start", "company": company_name})
        
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    # Prioritize Gemini if its API key is set
    if gemini_key and gemini_key not in ("mock_key", "your_gemini_api_key_here", ""):
        return await run_gemini_agent(company_name, queue, start_time)

    # Try Groq if its API key is set
    if groq_key and groq_key not in ("mock_key", "your_groq_api_key_here", ""):
        return await run_groq_agent(company_name, queue, start_time)

    # Try Anthropic if its API key is set
    if anthropic_key and anthropic_key not in ("mock_key", "your_anthropic_api_key_here", ""):
        return await run_anthropic_agent(company_name, queue, start_time)

    # No LLM API key configured — fail with clear error
    error_msg = (
        "Configuration Error: No LLM API key configured. "
        "Set at least one of GEMINI_API_KEY, GROQ_API_KEY, or ANTHROPIC_API_KEY in your .env file."
    )
    if queue:
        await queue.put({"type": "error", "message": error_msg})
    raise ValueError(error_msg)


# ─── Tool Definitions (shared across providers) ─────────────────────────────

def get_anthropic_tools():
    """Returns tool definitions in Anthropic's format."""
    return [
        {
            "name": "web_search",
            "description": "Search the web for information about a company. Use specific queries. Prefer queries like '[Company] funding 2024 site:crunchbase.com' over just '[Company]'. Returns top 5 results with title, URL, and snippet.",
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
            "description": "Fetch and extract readable text content from a URL. Use for official company websites, press releases, news articles. Do NOT use for LinkedIn or Crunchbase direct pages — they block scrapers.",
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


def get_gemini_tools():
    """Returns tool definitions in Gemini's format."""
    return [{
        "functionDeclarations": [
            {
                "name": "web_search",
                "description": "Search the web for information about a company. Use specific queries. Prefer queries like '[Company] funding 2024 site:crunchbase.com' over just '[Company]'. Returns top 5 results with title, URL, and snippet.",
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
                "description": "Fetch and extract readable text content from a URL. Use for official company websites, press releases, news articles. Do NOT use for LinkedIn or Crunchbase direct pages — they block scrapers.",
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


# ─── Anthropic Agent ────────────────────────────────────────────────────────

async def run_anthropic_agent(company_name: str, queue: asyncio.Queue = None, start_time: float = None) -> dict:
    """
    Runs the ReAct loop using Anthropic Claude API.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    client = AsyncAnthropic(api_key=anthropic_key)
    system_prompt = build_system_prompt(company_name)
    tools = get_anthropic_tools()

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
        
        # Validate through Pydantic
        dossier = validate_dossier_with_pydantic(dossier)
        
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
        logger.error(error_msg)
        if queue:
            await queue.put({"type": "error", "message": error_msg})
        raise e


# ─── Gemini Agent ───────────────────────────────────────────────────────────

LAST_GEMINI_REQUEST_TIME = 0.0
GEMINI_MIN_INTERVAL = 4.1  # 4.1s to be safe under the 15 RPM limit


async def gemini_post_with_retry(client, url, json_payload, queue=None, max_retries=6, initial_delay=5.0, backoff_factor=2.0):
    global LAST_GEMINI_REQUEST_TIME
    delay = initial_delay
    for attempt in range(max_retries):
        # Enforce minimum interval between requests proactively
        now = time.time()
        elapsed = now - LAST_GEMINI_REQUEST_TIME
        if elapsed < GEMINI_MIN_INTERVAL:
            sleep_time = GEMINI_MIN_INTERVAL - elapsed
            await asyncio.sleep(sleep_time)
            
        LAST_GEMINI_REQUEST_TIME = time.time()
        try:
            response = await client.post(url, json=json_payload)
            if response.status_code == 429:
                retry_after_str = response.headers.get("retry-after")
                try:
                    retry_delay = float(retry_after_str) if retry_after_str else delay
                except ValueError:
                    retry_delay = delay
                
                if queue:
                    await queue.put({
                        "type": "reason",
                        "text": f"Gemini API rate limit (429) hit. Retrying attempt {attempt + 1}/{max_retries} in {retry_delay:.1f}s..."
                    })
                await asyncio.sleep(retry_delay)
                LAST_GEMINI_REQUEST_TIME = time.time()
                delay *= backoff_factor
                continue
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 429:
                retry_after_str = e.response.headers.get("retry-after")
                try:
                    retry_delay = float(retry_after_str) if retry_after_str else delay
                except ValueError:
                    retry_delay = delay
                if queue:
                    await queue.put({
                        "type": "reason",
                        "text": f"Gemini API rate limit (429) hit. Retrying attempt {attempt + 1}/{max_retries} in {retry_delay:.1f}s..."
                    })
                await asyncio.sleep(retry_delay)
                LAST_GEMINI_REQUEST_TIME = time.time()
                delay *= backoff_factor
                continue
            elif status_code in (500, 502, 503, 504) and attempt < max_retries - 1:
                if queue:
                    await queue.put({
                        "type": "reason",
                        "text": f"Gemini API transient error ({status_code}). Retrying in {delay:.1f}s..."
                    })
                await asyncio.sleep(delay)
                LAST_GEMINI_REQUEST_TIME = time.time()
                delay *= backoff_factor
                continue
            raise e
        except (httpx.RequestError, asyncio.TimeoutError) as e:
            if attempt < max_retries - 1:
                if queue:
                    await queue.put({
                        "type": "reason",
                        "text": f"Gemini API network/timeout error. Retrying in {delay:.1f}s..."
                    })
                await asyncio.sleep(delay)
                LAST_GEMINI_REQUEST_TIME = time.time()
                delay *= backoff_factor
                continue
            raise e
            
    # Final attempt
    now = time.time()
    elapsed = now - LAST_GEMINI_REQUEST_TIME
    if elapsed < GEMINI_MIN_INTERVAL:
        await asyncio.sleep(GEMINI_MIN_INTERVAL - elapsed)
    LAST_GEMINI_REQUEST_TIME = time.time()
    response = await client.post(url, json=json_payload)
    response.raise_for_status()
    return response.json()


async def run_gemini_agent(company_name: str, queue: asyncio.Queue = None, start_time: float = None) -> dict:
    """
    Runs the ReAct loop using the free Google Gemini API.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    system_prompt = build_system_prompt(company_name)
    gemini_tools = get_gemini_tools()

    contents = []
    iteration = 0
    tool_calls_count = 0
    sources_visited = set()

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
            
            res_data = await gemini_post_with_retry(client, url, payload, queue)
            
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
        
        synth_data = await gemini_post_with_retry(client, url, synthesis_payload, queue)
        
        dossier_text = synth_data["candidates"][0]["content"]["parts"][0]["text"]
        
        dossier_text = dossier_text.strip()
        if dossier_text.startswith("```json"):
            dossier_text = dossier_text[7:]
        if dossier_text.endswith("```"):
            dossier_text = dossier_text[:-3]
        dossier_text = dossier_text.strip()
        
        dossier = json.loads(dossier_text)
        
        # Validate through Pydantic
        dossier = validate_dossier_with_pydantic(dossier)
        
        populate_agent_metadata(dossier, iteration, tool_calls_count, duration, "gemini-2.0-flash", queue)
        
        existing_sources = set(dossier.get("sources", []))
        existing_sources.update(sources_visited)
        dossier["sources"] = list(existing_sources)

        if queue:
            await queue.put({"type": "complete", "dossier": dossier})

        return dossier


# ─── Groq Agent ─────────────────────────────────────────────────────────────

async def run_groq_agent(company_name: str, queue: asyncio.Queue = None, start_time: float = None) -> dict:
    """
    Runs the ReAct loop using Groq's free-tier API (llama-3.3-70b-versatile for research, llama-3.1-8b-instant for synthesis).
    Uses the OpenAI-compatible chat completions API with tool calling.
    """
    from groq import AsyncGroq

    api_key = os.getenv("GROQ_API_KEY")
    client = AsyncGroq(api_key=api_key)
    system_prompt = build_system_prompt(company_name)

    # Groq uses OpenAI-compatible tool format
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for information about a company. Use specific queries. Returns top 5 results with title, URL, and snippet.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query. Be specific. Include company name + topic."
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_page",
                "description": "Fetch and extract readable text content from a URL. Use for official company websites, press releases, news articles. Do NOT use for LinkedIn or Crunchbase direct pages — they block scrapers.",
                "parameters": {
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
        }
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Start researching {company_name}."}
    ]
    iteration = 0
    tool_calls_count = 0
    sources_visited = set()

    try:
        while iteration < MAX_ITERATIONS:
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1024
            )

            choice = response.choices[0]
            assistant_message = choice.message

            # Extract reasoning text
            reasoning_text = assistant_message.content or ""
            if reasoning_text and queue:
                await queue.put({"type": "reason", "text": reasoning_text})

            # Append assistant message to conversation
            messages.append({
                "role": "assistant",
                "content": reasoning_text,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in (assistant_message.tool_calls or [])
                ] or None
            })

            # If no tool calls, agent has finished research
            if not assistant_message.tool_calls:
                break

            # Process tool calls
            for tool_call in assistant_message.tool_calls:
                tool_calls_count += 1
                tool_name = tool_call.function.name
                tool_input = json.loads(tool_call.function.arguments)

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

                # Append tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

            iteration += 1

        # Synthesis phase
        duration = int(time.time() - start_time)
        if queue:
            await queue.put({"type": "reason", "text": "Synthesizing research logs into structured dossier..."})

        synthesis_messages = messages + [
            {"role": "user", "content": SYNTHESIS_PROMPT}
        ]

        synthesis_response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=synthesis_messages,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )

        dossier_text = synthesis_response.choices[0].message.content or ""

        # Clean JSON wrappers if generated
        dossier_text = dossier_text.strip()
        if dossier_text.startswith("```json"):
            dossier_text = dossier_text[7:]
        if dossier_text.endswith("```"):
            dossier_text = dossier_text[:-3]
        dossier_text = dossier_text.strip()

        dossier = json.loads(dossier_text)

        # Validate through Pydantic
        dossier = validate_dossier_with_pydantic(dossier)

        populate_agent_metadata(dossier, iteration, tool_calls_count, duration, "groq/llama-3.3-70b-versatile", queue)

        existing_sources = set(dossier.get("sources", []))
        existing_sources.update(sources_visited)
        dossier["sources"] = list(existing_sources)

        if queue:
            await queue.put({"type": "complete", "dossier": dossier})

        return dossier

    except Exception as e:
        error_msg = f"Groq agent execution failed: {str(e)}"
        logger.error(error_msg)
        if queue:
            await queue.put({"type": "error", "message": error_msg})
        raise e
