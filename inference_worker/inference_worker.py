import os
from flask import Flask, request, jsonify
from llama_cpp import Llama

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = None  # no size limit for large model files

MODEL_CACHE_DIR = "./model_cache"

llm: Llama | None = None


def init_llama():
    global llm
    cached = [f for f in os.listdir(MODEL_CACHE_DIR) if f.endswith(".gguf")] if os.path.isdir(MODEL_CACHE_DIR) else []
    if not cached:
        print("No model found in cache, llama instance not created.")
        return
    model_path = os.path.join(MODEL_CACHE_DIR, cached[0])
    if len(cached) > 1:
        print(f"Multiple models in cache, loading first: {cached[0]}")
    n_gpu_layers = int(os.environ.get("N_GPU_LAYERS", -1))
    n_ctx = int(os.environ.get("N_CTX", 2048))
    llm = Llama(model_path=model_path, n_gpu_layers=n_gpu_layers, n_ctx=n_ctx)
    print(f"Initialized llama.cpp instance with {cached[0]}.")
 
@app.route("/load_model_from_store", methods=["POST"])
def load_model_from_store():
    """
    Receive a model file from the model store server.
    Store in memory or disk, then load into GPU via llama.cpp.
    """
    pass


@app.route("/load_model_from_cache", methods=["POST"])
def load_model_from_cache():
    """
    Receive a model name from the model store server.
    Load the already-cached model into GPU via llama.cpp.
    """
    pass


@app.route("/cache_model", methods=["POST"])
def cache_model():
    """
    Receive a model file from the model store server.
    Store on disk (or memory) without loading into GPU.
    """
    model_name = request.headers.get("X-Model-Name")
    if not model_name:
        return jsonify({"error": "X-Model-Name header required"}), 400

    os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_CACHE_DIR, model_name)

    with open(model_path, "wb") as f:
        chunk_size = 1024 * 1024  # 1MB chunks
        while chunk := request.stream.read(chunk_size):
            f.write(chunk)

    return jsonify({"status": "cached", "path": model_path})


if __name__ == "__main__":
    init_llama()
    app.run(host="0.0.0.0", port=8080)
