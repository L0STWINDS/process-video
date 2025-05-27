# 视频处理API服务

## 项目介绍

这是一个基于FastAPI开发的视频处理API服务，主要功能包括视频帧提取、音频转文本等。服务采用Docker容器化部署，为LLM、VLM解读做数据准备。

## 功能

- **视频处理**：从视频中提取帧
- **音频转文本**：使用ASR服务将视频音频转换为文本
- **自动参数计算**：如果不设置帧采样间隔将自动计算采样间隔
- **资源管理**：自动清理过期临时文件，避免磁盘空间占用过大

## 技术栈

- **后端框架**：FastAPI
- **视频处理**：FFmpeg
- **异步处理**：asyncio, aiohttp
- **语音识别**：OpenAI兼容的ASR服务

## 部署方法
将 docker-compose-example.yml 复制为 docker-compose.yml，然后按照以下步骤进行配置：
修改 docker-compose.yml 文件中的 environment 配置，将ASR服务配置为你所使用的接口（ASR_API_BASE_URL，ASR_API_KEY，ASR_MODEL），FILE_ACCESS_BASE_URL 配置为你的服务器的IP或域名。
修改 docker-compose.yml 文件中的 volumes 配置，根据你的磁盘情况设置 /app/temp 的映射路径。
```bash
docker-compose up -d
```

## 示例
指定采样起始时间和间隔时间（秒）
```curl
curl --request POST \
  --url http://127.0.0.1:8000/api/process-video \
  -H "Authorization: Bearer your-secret-api-key-here" \
  -H 'Content-Type: application/json' \
  -D '{
  "url": "http://127.0.0.1:5244/d/MP4/video.mp4",
  "start_seconds": "300",
  "interval_seconds": "300",
  "max_frames": "10"
}'
```
不指定采样起始时间和间隔时间，将自动计算采样间隔（视频时长/(max_frames+1)）
```curl
curl --request POST \
  --url http://127.0.0.1:8000/api/process-video \
  -H "Authorization: Bearer your-secret-api-key-here" \
  -H 'Content-Type: application/json' \
  -D '{
  "url": "http://127.0.0.1:5244/d/MP4/video.mp4",
  "max_frames": "10"
}'
```