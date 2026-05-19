import os
from flask import Flask, request, jsonify, Response, stream_with_context
from llama_cpp import Llama

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = None  # no size limit for large model files

MODEL_CACHE_DIR = "./model_cache"

llm: Llama | None = None
loaded_model_name: str | None = None


def init_llama():
    global llm, loaded_model_name
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
    loaded_model_name = cached[0]
    print(f"Initialized llama.cpp instance with {cached[0]}.")


# From Remote Store Server 
@app.route("/load_model_from_store", methods=["POST"])
def load_model_from_store():
    """
    Receive a model file from the model store server.
    Store in memory or disk, then load into GPU via llama.cpp.
    """
    global llm, loaded_model_name
    model_name = request.headers.get("X-Model-Name")
    if not model_name:
        return jsonify({"error": "X-Model-Name header required"}), 400

    # We should check if it already exists here no?
    
    os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_CACHE_DIR, model_name)

    with open(model_path, "wb") as f:
        chunk_size = 1024 * 1024  # 1MB chunks
        while chunk := request.stream.read(chunk_size):
            f.write(chunk)

    n_gpu_layers = int(os.environ.get("N_GPU_LAYERS", -1))
    n_ctx = int(os.environ.get("N_CTX", 2048))
    llm = Llama(model_path=model_path, n_gpu_layers=n_gpu_layers, n_ctx=n_ctx)
    loaded_model_name = model_name
    print(f"Loaded {model_name} into GPU.")

    return jsonify({"status": "loaded", "model": model_name})

# Local Load
@app.route("/load_model_from_cache", methods=["POST"])
def load_model_from_cache():
    """
    Receive a model name from the model store server.
    Load the already-cached model into GPU via llama.cpp.
    """
    global llm, loaded_model_name
    model_name = request.headers.get("X-Model-Name")
    if not model_name:
        return jsonify({"error": "X-Model-Name header required"}), 400
    model_path = os.path.join(MODEL_CACHE_DIR, model_name)
    
    # Makes sure you don't load a model that isn't actually there
    if not os.path.isfile(model_path):
        return jsonify({"error": "model not found in cache", "model": model_name}), 404


    n_gpu_layers = int(os.environ.get("N_GPU_LAYERS", -1))
    n_ctx = int(os.environ.get("N_CTX", 2048))
    llm = Llama(model_path=model_path, n_gpu_layers=n_gpu_layers, n_ctx=n_ctx)
    loaded_model_name = model_name
    print(f"Loaded {model_name} into GPU.")

    return jsonify({"status": "loaded", "model": model_name})
    

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


@app.route("/infer", methods=["POST"])
def infer():
    global llm, loaded_model_name
    body = request.get_json(force=True)
    prompt = body.get("prompt")
    model = body.get("model")

    if not prompt:
        return jsonify({"error": "prompt required"}), 400
    if llm is None:
        return jsonify({"error": "no model loaded"}), 503
    if model and model != loaded_model_name:
        return jsonify({"error": "model mismatch", "loaded": loaded_model_name, "requested": model}), 409

    max_tokens = body.get("max_tokens", 512)

    def generate():
        for chunk in llm(prompt, max_tokens=max_tokens, stream=True):
            token = chunk["choices"][0]["text"]
            yield token

    return Response(stream_with_context(generate()), mimetype="text/plain")


if __name__ == "__main__":
    init_llama()
    app.run(host="0.0.0.0", port=8080)
