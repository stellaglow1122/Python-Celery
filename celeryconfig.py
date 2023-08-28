# Celery configuration
# http://docs.celeryproject.org/en/latest/configuration.html

broker_url = 'redis://localhost:6379'

# Task result backend settings
result_backend = 'db+postgresql://username:password@hostname/databasename'

# use custom schema for the database result backend.
database_table_schemas = {
    'task': 'celery',
    'group': 'celery',
}

# json serializer is more secure than the default pickle
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
worker_concurrency = 8
worker_lost_wait = 180
task_queues = {
    'QueueName': {
        'exchange': 'QueueName',
        'routing_key': 'QueueName',
    },
}
task_create_missing_queues = True

# change to local time zone
timezone = 'America/Boise'
enable_utc = False