from fastapi import APIRouter
from app.api.endpoints import video

# 创建主路由
api_router = APIRouter(prefix="/api")

# 注册各模块路由
api_router.include_router(video.router, tags=["视频处理"])

# 这里可以继续添加其他模块的路由
# api_router.include_router(other_module.router, tags=["其他模块"])