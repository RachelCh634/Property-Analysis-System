from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class AnalysisDepth(str, Enum):
    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"

class PropertyAnalysisRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=500)
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD
    include_market_analysis: bool = True
    include_development_potential: bool = True

class PropertyAnalysisResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]]
    analysis_id: Optional[str]
    timestamp: datetime = Field(default_factory=datetime.now)

class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    current_step: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime