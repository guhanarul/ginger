from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from aiohttp import web
import redis
import json
import threading
import secrets
import time

threadStore = threading.local()

def generateEncryptionKeysS():
    try:

        ourPrivateKey = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        ourPublicKey = ourPrivateKey.public_key()

        private_pem = ourPrivateKey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        public_pem = ourPublicKey.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
    
    except Exception as e:
        print(f"Error during encryption occured: ${e}")
        raise web.HTTPInternalServerError(text="generate keys failed")

    return (private_pem,public_pem)

def store_redis(key,value,redis_client,db=None):
    if db is None:
        try:
            redis_client.set(key,str(value))
        except Exception as e:
            print(f"Error during redis key set!! {e}")
            raise web.HTTPInternalServerError(text="Redis storage failed")
    else:
        redis_client.execute_command('SELECT',db)
        try:
            redis_client.set(key,json.dumps(value))
        except Exception as e:
            redis_client.execute_command('SELECT',0)
            print(f"Error during redis key set!! {e}")
            raise web.HTTPInternalServerError(text="Redis storage failed")
        redis_client.execute_command('SELECT',0)
    
def get_redis(key,redis_client,db=None):
    if db is None:
        redisData = redis_client.get(key)
    else :
        redis_client.execute_command('SELECT',db)
        redisData = redis_client.get(key)
        redis_client.execute_command('SELECT',0)
    return redisData

def getAllRedisVal(redisClient,db = None):
    if db:
        redisClient.execute_command('SELECT',db)
        keys=redisClient.keys('*')
        values=redisClient.mget(keys)
        redisClient.execute_command('SELECT',0)
    else:
        keys=redisClient.keys('*')
        values=redisClient.mget(keys)
    return (keys,values)

def mkKeyValue(**kwargs):
    redis_value = {
            "domainName":kwargs.get("domainName",getContext("gingDName")),
            "status":kwargs.get("status",1),
            "pubKeyClient" : kwargs.get("pubKeyClient","NULL"),
            "pubKeyOurs" :  kwargs.get("pubKeyOurs","NULL"),
            "privKeyOurs" : kwargs.get("privKeyOurs","NULL"),
            "name": kwargs.get("name",getContext("gingName")) # Bug here
        }
    return redis_value

def sendErr(**kwargs):
  return web.Response(
      text=json.dumps(
          {
           "message": kwargs.get("msg","NONE")
          }
      ),
      status=kwargs.get("code",200),
      content_type="application/json"
    )

def sendResp(jsondata):
    return web.Response(
        text=json.dumps(jsondata),
        content_type="application/json"
    )

def getContext(key):
    return getattr(threadStore, key, None)

def setContext(key , value):
    setattr(threadStore, key, value)

def generateStreamKey(username):
    timestamp = time.time_ns
    rndstr = secrets.token_hex(4)
    return f"{username}:{timestamp}:{rndstr}"
