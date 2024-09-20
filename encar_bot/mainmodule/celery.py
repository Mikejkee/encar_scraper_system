import os
from celery import Celery, Task
from django.conf import settings


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mainmodule.settings")
app = Celery("mainmodule")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(settings.INSTALLED_APPS)


class BaseTask(Task):
    autoretry_for = (Exception, KeyError)
    retry_kwargs = {'max_retries': 2}
    retry_backoff = True
