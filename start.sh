#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl start mariadb
python -c "import app; print('APP DATABASE INITIALIZATION SUCCESS')"
python app.py
