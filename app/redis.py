import redis
import os
import json

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# decode_responses=True ensures we get Python strings back instead of bytes
redis_client = redis.from_url(REDIS_URL, decode_responses=True)