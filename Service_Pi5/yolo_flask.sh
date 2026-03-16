#!/bin/bash

VENV_PATH="/home/lagct/Desktop/Traffic_Control/yolo/bin/activate"
APP_PATH="/home/lagct/Desktop/Traffic_Control/web_test/project"

source "$VENV_PATH"

cd "$APP_PATH"

export FLASK_APP=app.py
export FLASK_ENV=production
export PYTHONUNBUFFERED=1

flask run --host=0.0.0.0 --port=8000