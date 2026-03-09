from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

class GhostIssue(BaseModel):
    """Standardized issue found by a metric adapter."""
    type: str # 'issue', 'ghost', 'flag'
    id: str   # internal tool id
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    severity: str = "medium" # 'low', 'medium', 'high', 'critical'
    metadata: Dict = Field(default_factory=dict)

class MetricSummary(BaseModel):
    total_files: int
    total_lines: int
    large_file_count: int
    average_lines: float
    vibe_score: int
    coupling_metrics: Optional[Dict] = Field(default_factory=dict)

class AIInsights(BaseModel):
    synthesis: Optional[str] = None
    reasoning: Optional[str] = None
    patches: List[Dict] = Field(default_factory=list)

class ArchitectureReport(BaseModel):
    vibe_score: int
    stack: str
    files_analyzed: int
    total_lines: int
    issues: List[str] = Field(default_factory=list)
    architectural_ghosts: List[str] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    coupling_metrics: Dict = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)  # Adapter/engine errors
    ai_prompt: Optional[str] = None
    ai_synthesis: Optional[str] = None
    ai_reasoning: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)
