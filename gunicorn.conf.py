# gunicorn.conf.py
import os

bind = "0.0.0.0:" + os.environ.get("PORT", "10000")
workers = 1
threads = 4
timeout = 180  # Aumentado a 180 segundos (3 minutos)
graceful_timeout = 60
worker_class = "sync"
max_requests = 1000
max_requests_jitter = 100