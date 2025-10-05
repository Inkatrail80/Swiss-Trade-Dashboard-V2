import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = int(os.environ.get("THREADS_PER_WORKER", "2"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))

# Render free tier has limited RAM; keep worker count modest.
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")
preload_app = True
