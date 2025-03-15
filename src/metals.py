from aiohttp import web
import json
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import helper
import redis
import sys
import bcrypt
import uuid
from datetime import datetime, timedelta
import threading
import numpy as np
import aiohttp_cors

CONSUMER_GROUP = "gingerConsumers"
CONSUMER_NAME = "Ginger1"
STREAM_NAME="EndpointStream"
TRANSITIVE_PROB=True
DETECTED_PARITY=0

try:
    redisClientDB = redis.StrictRedis(host='localhost',port=6380, db = 0, decode_responses=True)
    redisClientDB.ping()
    try :
        redisClientDB.xgroup_create(STREAM_NAME,CONSUMER_GROUP,id="$",mkstream = True)
    except redis.exceptions.ResponseError:
        pass
    print("Redis connection success!! 🥳")
except redis.ConnectionError as err:
    print(f"Failed to connect to Redis!! 😔 {err}")
    sys.exit(1)