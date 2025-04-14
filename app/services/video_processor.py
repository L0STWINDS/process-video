import os
import asyncio
import aiohttp
import uuid
import time
import logging
import json
from datetime import datetime, timedelta
import shutil
from pathlib import Path
import ffmpeg
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.services.asr_service import asr_service  # 导入ASR服务

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("video_processor")

# 信号量控制并发
semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_TASKS)

# 存储任务状态
tasks = {}

class VideoProcessor:
    def __init__(self):
        # 确保临时目录存在
        os.makedirs(settings.TEMP_DIR, exist_ok=True)
        
        # 确保任务记录目录存在
        self.tasks_record_dir = os.path.join(settings.TEMP_DIR, "_tasks_record")
        os.makedirs(self.tasks_record_dir, exist_ok=True)
        
        # 加载已有任务记录
        self._load_tasks_from_disk()
        
        # 启动定期清理任务
        asyncio.create_task(self._cleanup_old_files())
    
    def _load_tasks_from_disk(self):
        """从磁盘加载任务记录"""
        try:
            logger.info("正在从磁盘加载任务记录...")
            loaded_count = 0
            
            # 遍历任务记录目录中的所有JSON文件
            for file_name in os.listdir(self.tasks_record_dir):
                if file_name.endswith('.json'):
                    task_id = file_name[:-5]  # 去掉.json后缀
                    file_path = os.path.join(self.tasks_record_dir, file_name)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            task_info = json.load(f)
                            
                            # 转换字符串时间为datetime对象
                            if 'created_at' in task_info and isinstance(task_info['created_at'], str):
                                task_info['created_at'] = datetime.fromisoformat(task_info['created_at'])
                            
                            # 添加到内存中的任务字典
                            tasks[task_id] = task_info
                            loaded_count += 1
                    except Exception as e:
                        logger.error(f"加载任务记录 {task_id} 失败: {str(e)}")
            
            logger.info(f"成功从磁盘加载了 {loaded_count} 个任务记录")
        except Exception as e:
            logger.error(f"加载任务记录失败: {str(e)}", exc_info=True)
    
    def _save_task_to_disk(self, task_id, task_info):
        """将任务信息保存到磁盘"""
        try:
            file_path = os.path.join(self.tasks_record_dir, f"{task_id}.json")
            
            # 创建任务信息的副本，避免修改原始数据
            task_data = task_info.copy()
            
            # 将datetime对象转换为ISO格式字符串
            if 'created_at' in task_data and isinstance(task_data['created_at'], datetime):
                task_data['created_at'] = task_data['created_at'].isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(task_data, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            logger.error(f"保存任务 {task_id} 到磁盘失败: {str(e)}")
            return False
    
    async def _cleanup_old_files(self):
        """定期清理过期的临时文件"""
        while True:
            try:
                logger.info("开始执行定期清理任务...")
                now = datetime.now()
                cutoff = now - timedelta(minutes=settings.TEMP_FILE_RETENTION_MINUTES)
                logger.info(f"清理截止时间: {cutoff.isoformat()}, 将清理早于此时间的任务")
                
                # 记录当前任务总数
                total_tasks = len(tasks)
                cleaned_tasks = 0
                
                for task_id, task_info in list(tasks.items()):
                    # 只清理已完成或失败的任务，正在处理的任务不清理
                    if (task_info.get("status") in ["completed", "failed"] and 
                        task_info.get("created_at") and task_info["created_at"] < cutoff):
                        
                        # 记录将被删除的任务信息
                        task_created_at = task_info["created_at"].isoformat() if isinstance(task_info["created_at"], datetime) else task_info["created_at"]
                        logger.info(f"发现过期任务: {task_id}, 创建时间: {task_created_at}, 状态: {task_info['status']}")
                        
                        # 删除过期任务的文件
                        task_dir = os.path.join(settings.TEMP_DIR, task_id)
                        if os.path.exists(task_dir):
                            # 记录删除前的文件大小
                            dir_size = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                                          for dirpath, _, filenames in os.walk(task_dir) 
                                          for filename in filenames)
                            dir_size_mb = dir_size / (1024 * 1024)
                            
                            shutil.rmtree(task_dir)
                            logger.info(f"已删除任务目录: {task_dir}, 释放空间: {dir_size_mb:.2f}MB")
                        else:
                            logger.warning(f"任务目录不存在: {task_dir}")
                        
                        # 从内存中的任务列表中移除
                        tasks.pop(task_id, None)
                        
                        # 删除任务记录文件
                        task_record_file = os.path.join(self.tasks_record_dir, f"{task_id}.json")
                        if os.path.exists(task_record_file):
                            os.remove(task_record_file)
                            logger.info(f"已删除任务记录文件: {task_record_file}")
                        
                        cleaned_tasks += 1
                        logger.info(f"已从任务列表中移除任务: {task_id}")
                
                # 记录清理结果摘要
                if cleaned_tasks > 0:
                    logger.info(f"清理任务完成: 共检查 {total_tasks} 个任务, 清理了 {cleaned_tasks} 个过期任务")
                else:
                    logger.info(f"清理任务完成: 共检查 {total_tasks} 个任务, 没有发现过期任务")
                    
            except Exception as e:
                logger.error(f"清理任务执行出错: {str(e)}", exc_info=True)
            
            # 记录下次执行时间
            next_run = datetime.now() + timedelta(minutes=settings.CLEANUP_INTERVAL_MINUTES)
            logger.info(f"下次清理任务将在 {next_run.isoformat()} 执行")
            
            # 根据配置的分钟数进行休眠
            await asyncio.sleep(settings.CLEANUP_INTERVAL_MINUTES * 60)
    
    @retry(stop=stop_after_attempt(settings.MAX_RETRIES), 
           wait=wait_exponential(multiplier=settings.RETRY_DELAY))
    async def _download_video(self, url, file_path):
        """下载视频文件，带重试机制"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=settings.DOWNLOAD_TIMEOUT) as response:
                    if response.status != 200:
                        raise Exception(f"下载失败，HTTP状态码: {response.status}")
                    
                    with open(file_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(1024 * 1024)  # 1MB chunks
                            if not chunk:
                                break
                            f.write(chunk)
            return True
        except Exception as e:
            logger.error(f"下载视频失败: {str(e)}")
            raise
    
    async def _extract_audio(self, video_path, audio_path):
        """提取音频为MP3格式，16k采样率，单声道"""
        try:
            loop = asyncio.get_event_loop()
            process = await loop.run_in_executor(None, lambda: (
                ffmpeg
                .input(video_path)
                .output(audio_path, format='mp3', acodec='libmp3lame', 
                        ar=16000, ac=1)
                .overwrite_output()
                .run(quiet=False, capture_stderr=True)
            ))
            return True
        except ffmpeg.Error as e:
            logger.error(f"提取音频失败: {str(e.stderr.decode())}")
            raise
        except Exception as e:
            logger.error(f"提取音频失败: {str(e)}")
            raise
    
    async def _extract_frames(self, video_path, output_dir, start_minutes=5, interval_minutes=5, max_frames=8):
        """从视频中提取帧，根据传入的起始时间、间隔和最大帧数"""
        try:
            # 获取视频时长
            probe = await asyncio.get_event_loop().run_in_executor(
                None, lambda: ffmpeg.probe(video_path)
            )
            duration = float(probe['format']['duration'])
            
            # 转换为秒
            start_time = start_minutes * 60  # 转换为秒
            interval = interval_minutes * 60  # 转换为秒
            
            logger.info(f"视频帧提取参数: 起始时间={start_time}秒, 间隔={interval}秒, 最大帧数={max_frames}")
            
            frame_times = []
            current_time = start_time
            
            while current_time < duration and len(frame_times) < max_frames:
                frame_times.append(current_time)
                current_time += interval
            
            # 提取帧
            for i, time_sec in enumerate(frame_times):
                output_file = os.path.join(output_dir, f"frame_{i+1}.jpg")
                
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda: (
                            ffmpeg
                            .input(video_path, ss=time_sec)
                            .output(output_file, vframes=1)
                            .overwrite_output()
                            .run(quiet=False, capture_stderr=True)
                        )
                    )
                except ffmpeg.Error as e:
                    logger.error(f"提取第 {i+1} 帧失败 (时间点: {time_sec}秒): {str(e.stderr.decode())}")
                    raise
            
            return len(frame_times)
        except ffmpeg.Error as e:
            logger.error(f"视频探测失败: {str(e.stderr.decode())}")
            raise
        except Exception as e:
            logger.error(f"提取视频帧失败: {str(e)}")
            raise
    
    async def _transcribe_audio(self, audio_path, output_path=None):
        """将音频转换为文本，使用ASR服务"""
        try:
            logger.info(f"调用ASR服务处理音频: {audio_path}")
            
            # 使用run_in_executor在线程池中执行阻塞操作
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(
                None, 
                lambda: asr_service.transcribe(audio_path, output_path)
            )
            
            return transcript
        except Exception as e:
            logger.error(f"调用ASR服务失败: {str(e)}", exc_info=True)
            raise
    
    async def process_video(self, url, start_minutes=5, interval_minutes=5, max_frames=8):
        """处理视频的主函数
        
        Args:
            url: 视频URL
            start_minutes: 从第几分钟开始提取帧，默认5分钟
            interval_minutes: 每隔几分钟提取一帧，默认5分钟
            max_frames: 最多提取几帧，默认8帧
            
        Returns:
            包含文件访问URL的JSON字符串
        """
        async with semaphore:
            task_id = str(uuid.uuid4())
            task_dir = os.path.join(settings.TEMP_DIR, task_id)
            os.makedirs(task_dir, exist_ok=True)
            
            # 初始化任务状态（仅用于内部处理）
            tasks[task_id] = {
                "status": "processing",
                "created_at": datetime.now(),
                "url": url,
                "message": "任务已创建",
                "frame_params": {
                    "start_minutes": start_minutes,
                    "interval_minutes": interval_minutes,
                    "max_frames": max_frames
                },
                "result": {}
            }
            
            # 保存任务信息到磁盘
            self._save_task_to_disk(task_id, tasks[task_id])
            
            video_path = os.path.join(task_dir, "video.mp4")
            audio_path = os.path.join(task_dir, "audio.mp3")
            frames_dir = os.path.join(task_dir, "frames")
            transcript_path = os.path.join(task_dir, "transcript.txt")
            os.makedirs(frames_dir, exist_ok=True)
            
            try:
                # 下载视频
                logger.info(f"开始下载视频: {url}")
                await self._download_video(url, video_path)
                logger.info(f"视频下载完成: {video_path}")
                
                # 提取音频
                logger.info(f"开始提取音频: {video_path} -> {audio_path}")
                await self._extract_audio(video_path, audio_path)
                logger.info("音频提取完成")
                
                # 提取视频帧
                logger.info(f"开始提取视频帧到目录: {frames_dir}")
                frame_count = await self._extract_frames(
                    video_path, 
                    frames_dir, 
                    start_minutes=start_minutes,
                    interval_minutes=interval_minutes,
                    max_frames=max_frames
                )
                logger.info(f"视频帧提取完成，共提取 {frame_count} 帧")
                
                # 音频转文本
                logger.info(f"开始将音频转换为文本...")
                transcript = await self._transcribe_audio(audio_path, transcript_path)
                logger.info(f"音频转文本完成，文本长度: {len(transcript)}")
                
                # 保存文本到文件
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    f.write(transcript)
                logger.info(f"音频转文本完成，已保存到: {transcript_path}")
                
                # 构建文件访问URL
                base_url = f"{settings.FILE_ACCESS_BASE_URL}/{task_id}"
                
                # 构建返回结果
                result = {
                    "transcript_url": f"{base_url}/transcript.txt",
                    "frames_urls": []
                }
                
                # 添加所有帧的URL
                for i in range(1, frame_count + 1):
                    result["frames_urls"].append(f"{base_url}/frames/frame_{i}.jpg")
                
                # 更新任务状态（仅用于内部记录）
                tasks[task_id].update({
                    "status": "completed",
                    "message": "处理完成",
                    "result": result
                })
                
                # 保存更新后的任务信息到磁盘
                self._save_task_to_disk(task_id, tasks[task_id])
                
                return result
                
            except Exception as e:
                logger.error(f"任务 {task_id} 处理失败: {str(e)}", exc_info=True)
                tasks[task_id].update({
                    "status": "failed",
                    "message": f"处理失败: {str(e)}"
                })
                # 保存失败状态到磁盘
                self._save_task_to_disk(task_id, tasks[task_id])
                return {"error": f"处理失败: {str(e)}"}

    def get_task_status(self, task_id):
        """获取任务状态"""
        if task_id not in tasks:
            # 尝试从磁盘加载任务信息
            task_record_file = os.path.join(self.tasks_record_dir, f"{task_id}.json")
            if os.path.exists(task_record_file):
                try:
                    with open(task_record_file, 'r', encoding='utf-8') as f:
                        task_info = json.load(f)
                        # 将任务信息加载到内存中
                        if 'created_at' in task_info and isinstance(task_info['created_at'], str):
                            task_info['created_at'] = datetime.fromisoformat(task_info['created_at'])
                        tasks[task_id] = task_info
                        logger.info(f"从磁盘加载了任务 {task_id} 的信息")
                except Exception as e:
                    logger.error(f"从磁盘加载任务 {task_id} 失败: {str(e)}")
                    return {"status": "not_found", "message": "任务不存在或无法加载"}
            else:
                return {"status": "not_found", "message": "任务不存在"}
        
        task_info = tasks[task_id]
        return {
            "task_id": task_id,
            "status": task_info["status"],
            "message": task_info["message"],
            "created_at": task_info["created_at"].isoformat() if isinstance(task_info["created_at"], datetime) else task_info["created_at"],
            "result": task_info.get("result", {})
        }

# 创建单例
video_processor = VideoProcessor()