import os
from flask import Flask, request, jsonify
from llama_cpp import Llama

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = None  # no size limit for large model files

MODEL_CACHE_DIR = "./model_cache"

llm: Llama | None = None


def init_server():
    """
    Finds models and workers
    """
    pass

def user_request():
    """
    Recieves user request (prompt and model)
    Forwards to worker
    """
    pass

def inference_resposne():
    """
    Recieves result from worker 
    Forwards to user
    """
    
    pass

if __name__ == "__main__ ":
    init_server();