from pydantic_settings import BaseSettings
from pydantic import Field
import os

class Settings(BaseSettings):
    # 并行处理限制
    MAX_CONCURRENT_TASKS: int = int(os.getenv("MAX_CONCURRENT_TASKS", "3"))
    # 临时文件存储路径
    TEMP_DIR: str = os.getenv("TEMP_DIR", "./temp")
    # 下载超时设置(秒)
    DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", "300"))
    # 处理超时设置(秒)
    PROCESSING_TIMEOUT: int = int(os.getenv("PROCESSING_TIMEOUT", "600"))
    # 临时文件保留时间(分钟)
    TEMP_FILE_RETENTION_MINUTES: int = int(os.getenv("TEMP_FILE_RETENTION_MINUTES", "10"))
    # 清理任务执行间隔(分钟)
    CLEANUP_INTERVAL_MINUTES: int = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "10"))
    # 重试设置
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "2"))

    # ASR服务配置
    ASR_API_BASE_URL: str = os.getenv("ASR_API_BASE_URL", "http://192.168.22.104:9997/v1")
    ASR_API_KEY: str = os.getenv("ASR_API_KEY", "not empty")
    ASR_MODEL: str = os.getenv("ASR_MODEL", "SenseVoiceSmall")

    # 视频帧提取配置
    # FRAME_EXTRACT_START_MINUTES: int = int(os.getenv("FRAME_EXTRACT_START_MINUTES", "5"))  # 从第几分钟开始提取
    # FRAME_EXTRACT_INTERVAL_MINUTES: int = int(os.getenv("FRAME_EXTRACT_INTERVAL_MINUTES", "5"))  # 每隔几分钟提取一帧
    # FRAME_EXTRACT_MAX_FRAMES: int = int(os.getenv("FRAME_EXTRACT_MAX_FRAMES", "8"))  # 最多提取几帧

    # 文件访问基础URL
    FILE_ACCESS_BASE_URL: str = os.getenv("FILE_ACCESS_BASE_URL", "http://192.168.22.103:8000/files")

settings = Settings()