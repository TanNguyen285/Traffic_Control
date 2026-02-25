#!/bin/bash

VENV_PATH="/home/pi/flask_app/venv/bin/activate"
APP_PATH="/home/pi/flask_app/app.py"

source "$VENV_PATH"

export FLASK_APP="$APP_PATH"
export FLASK_ENV=production
export PYTHONUNBUFFERED=1

flask run --host=0.0.0.0 --port=5000
