import os
from flask import Flask, request, jsonify
import config


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
    
    # TODO: use actual inference later

    return jsonify({
        "status": "scaffolding",
        "prompt": prompt,
        "model": model,
    })

if __name__ == "__main__":
      app.run(host="0.0.0.0", port=8000)
