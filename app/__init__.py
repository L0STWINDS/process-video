from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles  # 导入StaticFiles
from app.api.router import api_router
from app.core.config import settings
import os

def create_app() -> FastAPI:
    """
    创建FastAPI应用实例
    """
    app = FastAPI(
        title="视频处理API", 
        description="处理视频文件的REST API",
        version="0.1.0"
    )
    
    # 注册路由
    app.include_router(api_router)
    
    # 确保临时目录存在
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    
    # 挂载静态文件目录
    app.mount("/files", StaticFiles(directory=settings.TEMP_DIR), name="files")
    
    @app.get("/")
    async def root():
        return {"message": "视频处理API服务正常运行"}
    
    return app