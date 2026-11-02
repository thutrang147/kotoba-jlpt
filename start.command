#!/bin/bash
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then
  exec .venv/bin/python server.py
fi
printf '%s\n' 'Chạy lần đầu: python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt'
exit 1
