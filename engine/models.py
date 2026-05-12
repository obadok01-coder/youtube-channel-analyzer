from pydantic import BaseModel
from typing import List, Optional


class AnalyzeRequest(BaseModel):
    url: str


class VideoOutlier(BaseModel):
    title: str
    link: str
    thumbnail: str
    views: int
    avg_views: float
    ratio: float
    title_analysis: Optional[str] = None
    transcript_analysis: Optional[str] = None


class AnalyzeResponse(BaseModel):
    status: str
    channel_name: Optional[str] = None
    channel_thumbnail: Optional[str] = None
    total_videos_analyzed: Optional[int] = None
    average_views: Optional[float] = None
    outliers: List[VideoOutlier] = []
    error: Optional[str] = None
    message: Optional[str] = None
