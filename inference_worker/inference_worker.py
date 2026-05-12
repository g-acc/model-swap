import os
from flask import Flask, request, jsonify
from llama_cpp import Llama

app = Flask(__name__)

llm: Llama | None = None


def init_llama():
    global llm
    model_path = os.environ.get("MODEL_PATH")
    if not model_path:
        print("No model loaded, llama instance not created.")
        return
    n_gpu_layers = int(os.environ.get("N_GPU_LAYERS", -1))
    n_ctx = int(os.environ.get("N_CTX", 2048))
    llm = Llama(model_path=model_path, n_gpu_layers=n_gpu_layers, n_ctx=n_ctx)
    print("Initialized llama.cpp instance.")
 
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
    pass


if __name__ == "__main__":
    init_llama()
    app.run(host="0.0.0.0", port=8080)
