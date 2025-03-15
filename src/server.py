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
import metals
from metals import redisClientDB, STREAM_NAME

route_map = {}
nodeMap = ["login","profile","movies","rentMovies","buyMovies"]
globalTransMat=[[0]*len(nodeMap) for _ in range(len(nodeMap))]
redisClientDB.set("GlobalTransProbMat",json.dumps(globalTransMat))

def register_route(method, path, handler):
    if path not in route_map:
        route_map[path] = {}
    route_map[path][method] = handler


#handlers are defined down.
async def healthCheck(request : web.Request) -> web.Response:
    requestData = await request.json()
    print(requestData)
    return helper.sendResp({ "status": "yes" })

async def generate_keys(request : web.Request) -> web.Response:
    jsonRequest = await request.json()
    domainName = jsonRequest.get("domainname")
    serverName = jsonRequest.get("name")
    helper.setContext("gingDName",domainName)
    helper.setContext("gingName",serverName)
    isAlreadyinRedis = helper.get_redis(domainName,redisClientDB)
    if isAlreadyinRedis is None:
        (clientPrivateKey,clientPublicKey) = helper.generateEncryptionKeysS()
        (ourPrivateKey,ourPublicKey) = helper.generateEncryptionKeysS()
        valueToRedis = helper.mkKeyValue(pubKeyClient=clientPublicKey,privKeyOurs=ourPrivateKey,pubKeyOurs=ourPublicKey)
        helper.store_redis(domainName,valueToRedis,redisClientDB,2)
        return helper.sendResp(
            {"redirecturl": "/ginger/calls",
            "publickey":clientPublicKey,
            "privateKey":clientPrivateKey,
            "gingerPubKey" : ourPublicKey
            })
    else:
        return helper.sendErr(msg="You have a already registered domain with this name",code=400)

async def getServers(request: web.Request) -> web.Response:
    (keys, values) = helper.getAllRedisVal(redisClientDB,2)
    resp_json={}
    for key,value in zip(keys,values):
        if value:
            try:
                data = json.loads(value)
                resp_json[key]={field:data[field] for field in ["domainName","status","pubKeyClient","name"] if field in data}
            except json.JSONDecodeError:
                print("Error decoding the json while sending for dashboard")
    return helper.sendResp(resp_json)


async def processRequests(request: web.Request) -> web.Response:
    
    def addItToStream(username,endpoint,redis):
        globalTransMat = json.loads(redis.get("GlobalTransProbMat")) #make sure this alsready there
        lastNode = helper.get_redis(username+"_lastNode",redis)
        if lastNode is not None:
            globalTransMat[nodeMap.index(lastNode)][nodeMap.index(endpoint)]+=1
            redis.set("GlobalTransProbMat",json.dumps(globalTransMat))
        redis.xadd(STREAM_NAME,{username:endpoint})
    
    request = await request.json()
    endPoint = request.get("endpoint")
    userName = request.get("username")
    addItToStream(userName,endPoint,redisClientDB)
    print(f"score for bot!! {metals.DETECTED_PARITY}")
    if(metals.DETECTED_PARITY>70):
        return helper.sendResp(
            {"status":"BOT_DETECTED"}
        )
    elif(metals.DETECTED_PARITY>50):
        return helper.sendResp(
            {"status":"MID_BOT"}
        )
    else:
        return helper.sendResp(
            {"status": "SUCCESS"}
        )
    
async def checkpassword(request : web.Request) -> web.Response:
    request = await request.json()
    username = request.get("name")
    password = request.get("password")
    stored_passHash = helper.get_redis(username+"gingerheremachan",redisClientDB,1)
    if stored_passHash is None:
        return helper.sendErr(msg="Give right password and username",code=400)
    else:
        if (bcrypt.checkpw(password.encode(),stored_passHash.encode())):
        #set sessionToken here!
            sessionToken = "GINGER-"+str(uuid.uuid4())
            expiryTime = datetime.now()+ timedelta(hours=1) # one hour da
            expiryTimHttp = expiryTime.strftime("%a, %d %b %Y %H:%M:%S GMT")
            response = web.json_response({"message":"Login done!"})
            response.headers["Session-Token"] = sessionToken
            response.headers["Expires"] = expiryTimHttp
            return response
        else:
            return helper.sendErr(msg="Give right password and username",code=400)

async def analyseFrontend(request: web.Request) -> web.Response:
    
    request_data = await request.json()
    time_diffs = [m["timeDiff"] for m in request_data["movementPatterns"] if "timeDiff" in m]

    if request_data["mouseMoves"] < 5 and request_data["clicks"] < 2:
        result = "Bot"
    elif len(time_diffs) > 1 and np.std(time_diffs) < 10:
        result = "Bot"
    else:
        result = "Human"
    print(result)
    if (result == "Bot" and metals.DETECTED_PARITY >= 70):
        return helper.sendResp(
            {"status":"BOT_DETECTED"}
        )
    else:
        return helper.sendResp(
            {"status":"HUMAN"}
        )

# Register your endpoints here!
register_route("POST","/analysefront",analyseFrontend)
register_route("POST","/health",healthCheck)
register_route("POST","/generatekey",generate_keys)
register_route("GET","/dashboard",getServers)
register_route("POST","/ginger/calls",processRequests)
register_route("POST","/getlogin",checkpassword)