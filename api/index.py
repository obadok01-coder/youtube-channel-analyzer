import asyncio
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from engine.models import AnalyzeRequest
from engine.youtube import YouTubeAnalyzer
from engine.ai import AIAnalyzer

app = FastAPI(title="YouTube Channel Analyzer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "env_configured": {
            "YOUTUBE_API_KEY": bool(os.getenv("YOUTUBE_API_KEY")),
            "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
            "DEEPSEEK_API_KEY": bool(os.getenv("DEEPSEEK_API_KEY")),
            "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
        },
    }


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    yt_key = os.getenv("YOUTUBE_API_KEY")
    if not yt_key:
        raise HTTPException(status_code=500, detail="YOUTUBE_API_KEY is not configured on the server.")

    try:
        yt = YouTubeAnalyzer(yt_key)
        ai = AIAnalyzer(
            openai_key=os.getenv("OPENAI_API_KEY"),
            deepseek_key=os.getenv("DEEPSEEK_API_KEY"),
            gemini_key=os.getenv("GEMINI_API_KEY"),
        )

        result = await yt.analyze_channel(request.url)

        if result["total_videos_analyzed"] == 0:
            return {
                "status": "success",
                "channel_name": result["channel_name"],
                "channel_thumbnail": result.get("channel_thumbnail"),
                "total_videos_analyzed": 0,
                "average_views": 0,
                "outliers": [],
                "message": "No public videos found for this channel.",
            }

        outliers = result["outliers"][:5]

        if outliers:
            title_tasks = [ai.analyze_title(o["title"]) for o in outliers]
            transcript_tasks = [ai.analyze_transcript(o.get("video_id")) for o in outliers]

            all_tasks = title_tasks + transcript_tasks
            results_list = await asyncio.gather(*all_tasks, return_exceptions=True)

            mid = len(outliers)
            title_results = results_list[:mid]
            transcript_results = results_list[mid:]

            for i, o in enumerate(outliers):
                tr = title_results[i]
                o["title_analysis"] = tr if not isinstance(tr, Exception) else None
                cr = transcript_results[i]
                o["transcript_analysis"] = cr if not isinstance(cr, Exception) else None

        return {
            "status": "success",
            "channel_name": result["channel_name"],
            "channel_thumbnail": result.get("channel_thumbnail"),
            "total_videos_analyzed": result["total_videos_analyzed"],
            "average_views": result["average_views"],
            "outliers": [
                {
                    "title": o["title"],
                    "link": o["link"],
                    "thumbnail": o.get("thumbnail", ""),
                    "views": o.get("views", 0),
                    "avg_views": o.get("avg_views", 0),
                    "ratio": o["ratio"],
                    "title_analysis": o.get("title_analysis"),
                    "transcript_analysis": o.get("transcript_analysis"),
                }
                for o in outliers
            ],
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


static_dir = os.path.join(project_root, "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
