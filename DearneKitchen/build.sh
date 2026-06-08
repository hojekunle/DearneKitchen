#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
echo "=== Media files collected to staticfiles ==="
ls -la Media/items/ | head -5
ls -la staticfiles/media/items/ | head -5
python manage.py migrate --no-input
python manage.py seed_initial_data
