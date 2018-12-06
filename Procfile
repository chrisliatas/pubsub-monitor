web: flask deploy; gunicorn gcpubsub:app
worker: rq worker -u $REDIS_URL gcpubsub-tasks