# celery.py
import os
from celery import Celery
from django.conf import settings

# 设置Celery的默认配置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# 创建Celery实例
app = Celery('home')

# 使用Django的settings配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动加载任务模块
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
