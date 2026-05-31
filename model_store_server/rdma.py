import asyncio
import os
import ucxx

# This is the chunck size that is sent over R
CHUNK = 4 * 1024 * 1024 

def send(host: str, port: int, model_name: str, file_path: str) -> None:

    size = os.path.getsize(file_path)
    async def _send():
        ep = await ucxx.create_endpoint(host, port)
        await ep.send_obj(f"{model_name}:{size}".encode())
        with open(file_path, "rb") as f:
            while chunk := f.read(CHUNK):
                await ep.send(chunk)
        await ep.recv_obj()  
        await ep.close()

    asyncio.run(_send())
