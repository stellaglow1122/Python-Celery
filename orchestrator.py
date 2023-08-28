#!/usr/bin/env python3

import os
import celeryconfig
#import settings
from datetime import timedelta
from celery import Celery
from heatmap.getDevices import get_devices

APP_NAME = 'ApplicationName'
app = Celery(APP_NAME)
app.config_from_object('celeryconfig', force=True)

app.conf.beat_schedule = {
    'run-task_a_one-every-1-minutes': {
        'task': 'heatmap.getDevices.get_devices',
        'schedule': timedelta(minutes=3),
        'options':{
            'queue' : 'QueueName',
            'retry':True,
            'retry_policy': {
                'max_retries': 3,
                'interval_start': 0,
                'interval_step': 10,
                'interval_max': 60,
            },
        },
    },
}