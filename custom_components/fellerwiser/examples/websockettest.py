import websockets
import asyncio

async def hello():
    ip = "192.168.0.18"
    async with websockets.connect("ws://"+ip+"/api", extra_headers={'authorization':'Bearer 35c369b1-2f8c-4103-83dd-0188a565d3fc'}, ping_timeout=None) as ws:
        while True:
            result =  await ws.recv()
            print ("Received '%s'" % result)

        ws.close()
asyncio.run(hello())
