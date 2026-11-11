#!/bin/bash
export PYTHONPATH=/home/claude/v6110
exec /usr/bin/python3.12 /home/claude/v6110/native_host.py 2>>/tmp/e2e/host.err
