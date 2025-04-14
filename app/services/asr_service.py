import os
import logging
import openai
from app.core.config import settings

# 配置日志
logger = logging.getLogger("asr_service")

class ASRService:
    def __init__(self):
        """初始化ASR服务"""
        # 初始化ASR客户端
        self.client = openai.Client(
            api_key=settings.ASR_API_KEY, 
            base_url=settings.ASR_API_BASE_URL
        )
        logger.info("ASR服务初始化完成")
    
    def transcribe(self, audio_path, output_path=None):
        """
        将音频文件转换为文本
        
        Args:
            audio_path: 音频文件路径
            output_path: 可选的输出文件路径，如果提供则将转录结果保存到文件
            
        Returns:
            转录的文本内容
        """
        try:
            logger.info(f"开始将音频转换为文本: {audio_path}")
            
            with open(audio_path, "rb") as audio_file:
                completion = self.client.audio.transcriptions.create(
                    model=settings.ASR_MODEL, 
                    file=audio_file
                )
            
            # 获取转录文本
            transcript = completion.text if hasattr(completion, 'text') else str(completion)
            logger.info(f"音频转文本完成，文本长度: {len(transcript)}")
            
            # 如果提供了输出路径，保存到文件
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(transcript)
                logger.info(f"转录文本已保存到: {output_path}")
            
            return transcript
        except Exception as e:
            logger.error(f"音频转文本失败: {str(e)}", exc_info=True)
            raise

# 创建单例
asr_service = ASRService()