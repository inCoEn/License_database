from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'License_database.settings')
os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')

app = Celery('License_database')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'save_stats_to_db': {
        'task': 'SB_model.tasks.save_stats_to_db',
        'schedule': 60.0
    }
}
