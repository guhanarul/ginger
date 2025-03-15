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
from server import route_map, register_route, nodeMap
import metals
from metals import redisClientDB,STREAM_NAME,CONSUMER_GROUP,CONSUMER_NAME

async def handle_calls (request):
    key = (request.method , request.path)
    try :
        handler = route_map[key]
    except Exception as e:
        print(f"Error while lookup: {e}")
        return helper.sendErr(msg="404: Not Found",code=404)
    response = await handler(request)
    return response

def detectLoops(endpointGraph):
    print("detectLoop Started!!")
    visitedNodes = set()
    recStack = []
    def doDfs(node):
        if node in recStack:
            cycleStartIndex = recStack.index(node)
            cycleLength = len(recStack) - cycleStartIndex
            return True, cycleLength
        
        if node in visitedNodes:
            return False, 0

        visitedNodes.add(node)
        recStack.append(node)

        for neighbor in endpointGraph.get(node, []):
            isLoop, loopLength = doDfs(neighbor)
            if isLoop:
                return True, loopLength

        recStack.pop()
        return False, 0

    for node in endpointGraph:
        if node not in visitedNodes:
            isLoop, loopLength = doDfs(node)
            if isLoop:
                return True, loopLength

    return False, 0


def buildRealGraph(userEndpoint,redis):
    usernameFromRequest = list(userEndpoint.keys())[0]
    valueFromRequest = userEndpoint[usernameFromRequest]
    print(f"This is the valFrm: {valueFromRequest}")
    streamKey = usernameFromRequest + "_ACGRAPH"
    if (redis.exists(streamKey)):
        print("existing")
        adjGraph = redis.hgetall(streamKey)
        adjGraph = {k: json.loads(v) for k, v in adjGraph.items()}
        lastNode = helper.get_redis(usernameFromRequest+"_lastNode",redis)
        print(lastNode)
        if lastNode in adjGraph:
            print("lastNode in adjGraph")
            adjGraph[lastNode].append(valueFromRequest)
        else:
            adjGraph[lastNode]=[valueFromRequest]
        for k, v in adjGraph.items():
            redis.hset(streamKey,k,json.dumps(v))
        helper.store_redis(usernameFromRequest+"_lastNode",valueFromRequest,redis)
        return (True,adjGraph)
    else :
        print("newin")
        helper.store_redis(usernameFromRequest+"_lastNode",valueFromRequest,redis)
        redis.hset(streamKey,str(valueFromRequest),json.dumps([]))
        return (False,[])

def processStream(redis):
    while True :
        messages = redis.xreadgroup(CONSUMER_GROUP,CONSUMER_NAME,{STREAM_NAME: ">"},count=1,block=5000)
        if not messages:
            continue
        for stream , entries in messages:
            for entryId, data in entries:
                print(f"Prcessing: {data} in {stream}")
                (canweCompute,endpointGraph)=buildRealGraph(data,redis)
                if canweCompute:
                    isdetected,loopLength=detectLoops(endpointGraph)
                    if isdetected:
                        print("detected!")
                        print(metals.DETECTED_PARITY)
                        metals.DETECTED_PARITY += (20*loopLength)
                        print(f"Updated parity score: {metals.DETECTED_PARITY}")

                redis.xack(STREAM_NAME,CONSUMER_GROUP,entryId)
                redis.xdel(STREAM_NAME,entryId)

async def preflight_handler(request):
    """Handles OPTIONS preflight requests."""
    return web.Response(status=200, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })

route_paths = list(route_map.keys())

for path in route_paths:
    register_route("OPTIONS", path, preflight_handler)

app = web.Application()
app.router.add_route("*","/{tail:.*}",handle_calls)

cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
        allow_methods=["POST", "GET", "OPTIONS"],
    )
})

for path, methods in route_map.items():
    options_registered = "OPTIONS" in methods
    for method, handler in methods.items():
        if method == "OPTIONS" and options_registered:
            continue 
        route = app.router.add_route(method, path, handler)
        cors.add(route)

if __name__ == "__main__":
    endpointProcessor = threading.Thread(target=processStream, args=(redisClientDB,),daemon=True)
    endpointProcessor.start()
    web.run_app(app,host= "127.0.0.1",port=8084)