from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from app.services.video_processor import video_processor

router = APIRouter()

class VideoRequest(BaseModel):
    url: HttpUrl
    start_minutes: int = 5  # 从第几分钟开始提取，默认5分钟
    interval_minutes: int = 5  # 每隔几分钟提取一帧，默认5分钟
    max_frames: int = 8  # 最多提取几帧，默认8帧

@router.post("/process-video")
async def process_video(request: VideoRequest):
    """
    处理视频API
    - 下载指定URL的MP4文件
    - 提取音频为MP3格式(16k采样率，单声道)
    - 从指定分钟开始每隔指定分钟提取视频帧(最多指定帧数)
    """
    # 直接返回处理结果，包含文件访问URL
    result = await video_processor.process_video(
        str(request.url),
        start_minutes=request.start_minutes,
        interval_minutes=request.interval_minutes,
        max_frames=request.max_frames
    )
    return JSONResponse(content=result)

# 移除任务状态查询接口，因为不再需要