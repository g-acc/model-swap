import os
import time
from flask import Flask, request, jsonify, Response, stream_with_context
import config
import worker_client
from state import worker

app = Flask(__name__)

if os.path.isdir(config.MODELS_DIR):
    available_models = [f for f in os.listdir(config.MODELS_DIR) if f.endswith(".gguf")]
else:
    available_models = []

print("Model Store Server")
print(f"  MODELS_DIR: {config.MODELS_DIR}")
print(f"  Available models: {available_models}")
print(f"  Worker URL: {config.WORKER_URL}")
print(f"  Cache policy: {worker.policy.name} (capacity={config.MAX_CACHE_SIZE})")


@app.route("/user_request", methods=["POST"])
def user_request():
    body = request.get_json(silent=True) or {}
    prompt = body.get("prompt")
    model = body.get("model")
    if not isinstance(prompt, str) or not isinstance(model, str):
        return jsonify({"error": "prompt and model (strings) are required"}), 400

    model_path = os.path.join(config.MODELS_DIR, model)
    if not os.path.isfile(model_path):
        return jsonify({"error": "model not on store", "model": model}), 404

    t0 = time.perf_counter()
    evicted: list[str] = worker.policy.sweep()
    worker_ms: float | None = None
    cache_action: str

    if worker.loaded == model:
        worker.policy.access(model)
        cache_action = "already_loaded"

    elif worker.policy.contains(model):
        t_w = time.perf_counter()
        worker_client.load_from_local_store(worker, model)
        worker_ms = (time.perf_counter() - t_w) * 1000
        worker.loaded = model
        worker.policy.access(model)
        cache_action = "load_from_local_store"

    else:
        result = worker.policy.admit(model)
        if not result.admitted:
            cache_action = "rejected"
            decision_ms = (time.perf_counter() - t0) * 1000
            print(
                f"[/user_request] ts={time.time():.3f} "
                f"policy={worker.policy.name} model={model} action={cache_action} "
                f"decision_ms={decision_ms:.2f} worker_ms=0.0 "
                f"cached={worker.policy.members()} evicted=[]"
            )
            return jsonify({"error": "cache full, policy refuses eviction",
                            "model": model,
                            "cached": worker.policy.members()}), 503

        evicted = evicted + result.evicted
        t_w = time.perf_counter()
        worker_client.send_model(worker, model, model_path, "load_model_from_store")
        worker_ms = (time.perf_counter() - t_w) * 1000
        worker.loaded = model
        cache_action = "load_from_store"

    decision_ms = (time.perf_counter() - t0) * 1000 - (worker_ms or 0)
    worker_ms_str = f"{worker_ms:.1f}" if worker_ms is not None else "0.0"

    print(
        f"[/user_request] ts={time.time():.3f} "
        f"policy={worker.policy.name} model={model} action={cache_action} "
        f"decision_ms={decision_ms:.2f} worker_ms={worker_ms_str} "
        f"cached={worker.policy.members()} evicted={evicted}"
    )

    max_tokens = body.get("max_tokens", 512)
    return Response(
        stream_with_context(worker_client.infer(worker, prompt, model, max_tokens)),
        mimetype="text/plain",
    )


@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    worker.policy.clear()
    worker.loaded = None
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
