#!/bin/bash
cd /opt/1panel/docker/compose/process-video
export API_KEY=not empty
export ASR_API_BASE_URL=http://192.168.1.100:9997/v1
export ASR_API_KEY=not empty
export ASR_MODEL=SenseVoiceSmall
export FILE_ACCESS_BASE_URL=http://192.168.1.100:8000/files
export TEMP_DIR="./temp"  # 添加临时目录环境变量
uvicorn main:app --host 0.0.0.0 --port 8000