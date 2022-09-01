#!/bin/bash
DEV=${1-"nodev"}
host="127.0.0.1"
if [[ $DEV == "dev" ]]; then
  export FLASK_ENV=development
elif [[ $DEV == "prod" ]]; then
  host="0.0.0.0"
fi

python -m flask run --host="$host" --port=5000
