#!/bin/bash
cd "$(dirname "$0")"
python3 auto_sync.py
echo ""
echo "Press any key to close..."
read -n 1
