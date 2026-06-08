#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
mkdir -p staticfiles/media/items staticfiles/media/feedback
cp -r Media/items/. staticfiles/media/items/
cp -r Media/feedback/. staticfiles/media/feedback/
python manage.py migrate --no-input
python manage.py seed_initial_data
