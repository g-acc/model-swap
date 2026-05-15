import os
from flask import Flask, request, jsonify
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
        return jsonify({"error": "model not on store", 
                        "model": model}), 404
    
    elif model in worker.cached:
        worker_client.load_from_cache(worker, model)
        worker.loaded = model
        cache_action = "load_from_cache"

    else:
        worker_client.load_from_store(worker, model, model_path)
        worker.cached.add(model)
        worker.loaded = model
        cache_action = "load_from_store"

    print(f"[/user_request] model={model} action={cache_action} prompt_len ={len(prompt)}")

    return jsonify({
        "status": "would_infer",
        "model" : model,
        "worker": worker.url,
        "cache_action": cache_action,
        "prompt": prompt,
    })

if __name__ == "__main__":
      app.run(host="0.0.0.0", port=8000)
