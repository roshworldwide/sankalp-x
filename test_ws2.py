import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://127.0.0.1:8000/ws/voice/stream", max_size=10*1024*1024) as ws:
        await ws.send(json.dumps({"action": "start", "user_id": "test"}))
        await ws.send(json.dumps({"action": "process_text", "text": "What government schemes are available for farmers in India?"}))
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=30)
                if isinstance(msg, bytes):
                    print(f"Received Audio: {len(msg)} bytes")
                else:
                    print(f"Received Text: {msg}")
            except asyncio.TimeoutError:
                print("Timeout waiting for response.")
                break

asyncio.run(test())
