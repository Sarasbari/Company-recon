"""
Pydantic models for Company Recon dossier data structures.
Provides type safety for tool inputs/outputs and the final synthesized dossier.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class FundingInfo(BaseModel):
    stage: str = "Data unavailable"
    total_raised: str = "Data unavailable"
    last_round: str = "Data unavailable"
    investors: List[str] = []


class KeyPerson(BaseModel):
    name: str
    role: str


class NewsItem(BaseModel):
    title: str
    url: str
    date: str = "Unknown"
    summary: str = ""


class AgentMetadata(BaseModel):
    iterations: int = 0
    tool_calls: int = 0
    duration_seconds: int = 0
    model_used: str = "unknown"
    steps: Optional[List[dict]] = None


class Dossier(BaseModel):
    company: str
    researched_at: str = ""
    overview: str = ""
    industry: str = "Data unavailable"
    business_model: str = "Data unavailable"
    founded: str = "Data unavailable"
    headquarters: str = "Data unavailable"
    headcount: str = "Data unavailable"
    funding: FundingInfo = Field(default_factory=FundingInfo)
    key_people: List[KeyPerson] = []
    recent_news: List[NewsItem] = []
    talking_points: List[str] = []
    sources: List[str] = []
    agent_metadata: AgentMetadata = Field(default_factory=AgentMetadata)


class SearchToolInput(BaseModel):
    query: str = Field(..., description="The search query. Be specific. Include company name + topic.")


class FetchToolInput(BaseModel):
    url: str = Field(..., description="The full URL to fetch.")
