import asyncio
import os
import threading
import ucxx


CHUNK = 4 * 1024 * 1024  # bytes per RDMA message; must match the sender
_listener = None


def start_listener(port: int, cache_dir: str) -> None:
    """Run the UCX listener in a daemon thread with its own event loop."""

    async def handle(ep):
        header = (await ep.recv_obj()).decode()
        model_name, size = header.rsplit(":", 1)
        size = int(size)

        os.makedirs(cache_dir, exist_ok=True)
        path = os.path.join(cache_dir, model_name)
        received = 0
        with open(path, "wb") as f:
            while received < size:
                n = min(CHUNK, size - received)
                buf = bytearray(n)
                await ep.recv(buf)
                f.write(buf)
                received += n

        await ep.send_obj(b"ok")  # tell the sender the file is fully written
        await ep.close()
        print(f"[rdma] received {model_name} ({size} bytes)", flush=True)

    def run():
        global _listener
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def serve():
            # create_listener must run inside a live loop so ucxx attaches its
            # progress engine; otherwise incoming connections never complete.
            global _listener
            _listener = ucxx.create_listener(handle, port)
            print(f"[rdma] listening on port {_listener.port}", flush=True)
            while True:
                await asyncio.sleep(3600)

        loop.run_until_complete(serve())

    threading.Thread(target=run, daemon=True).start()
