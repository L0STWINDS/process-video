from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional
from app.services.video_processor import video_processor
from app.core.auth import verify_api_key

router = APIRouter()

class VideoRequest(BaseModel):
    url: HttpUrl
    start_seconds: Optional[int] = None
    interval_seconds: Optional[int] = None
    max_frames: Optional[int] = 8

@router.post("/process-video")
async def process_video(
    request: VideoRequest,
    api_key: str = Depends(verify_api_key)
):
    try:
        result = await video_processor.process_video(
            str(request.url),
            start_seconds=request.start_seconds,
            interval_seconds=request.interval_seconds,
            max_frames=request.max_frames
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))