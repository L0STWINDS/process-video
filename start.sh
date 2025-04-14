#!/bin/bash
cd /opt/1panel/docker/compose/process-video
uvicorn main:app --host 0.0.0.0 --port 8000