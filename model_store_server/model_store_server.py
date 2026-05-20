import os
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

    evicted: list[str] = []
    if worker.loaded == model:
        worker.policy.access(model)
        cache_action = "already_loaded"

    elif worker.policy.contains(model):
        worker_client.load_from_cache(worker, model)
        worker.loaded = model
        worker.policy.access(model)
        cache_action = "load_from_cache"

    else:
        worker_client.load_from_store(worker, model, model_path)
        evicted = worker.policy.admit(model)
        worker.loaded = model
        cache_action = "load_from_store"

    log_extra = f" evicted={evicted}" if evicted else ""
    print(
        f"[/user_request] model={model} action={cache_action} cached={worker.policy.members()}{log_extra}"
    )

    max_tokens = body.get("max_tokens", 512)
    return Response(
        stream_with_context(worker_client.infer(worker, prompt, model, max_tokens)),
        mimetype="text/plain",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
