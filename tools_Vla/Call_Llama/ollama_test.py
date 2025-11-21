import requests
import json

# Configuration
OLLAMA_HOST = "http://192.168.1.28:11434"
MODEL = "gpt-oss:20b"  # Change this to your preferred model

# Create a session for connection pooling (reuses TCP connections = faster)
session = requests.Session()
session.headers.update({"Connection": "keep-alive"})

def list_models():
    """List available models on the Ollama server."""
    resp = session.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [model["name"] for model in data.get("models", [])]

def send_prompt_non_streaming(prompt, model=MODEL):
    """Send a non-streaming request to Ollama server."""
    resp = session.post(
        f"{OLLAMA_HOST}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=60
    )
    resp.raise_for_status()
    return resp.json()

def send_prompt_streaming(prompt, model=MODEL, verbose=False):
    """Send a streaming request to Ollama server and yield tokens.
    
    Args:
        prompt: The prompt to send
        model: Model name to use
        verbose: If True, yields dict with metadata; if False, yields just response text
    """
    resp = session.post(
        f"{OLLAMA_HOST}/api/generate",
        json={"model": model, "prompt": prompt, "stream": True},
        stream=True,
        timeout=60
    )
    resp.raise_for_status()
    
    for line in resp.iter_lines():
        if line:
            data = json.loads(line.decode("utf-8"))
            
            if verbose:
                # Return full data including thinking, timings, etc.
                yield data
            else:
                # Return just the response text
                if "response" in data and data["response"]:
                    yield data["response"]
            
            if data.get("done", False):
                break

if __name__ == "__main__":
    # List available models
    print("=== Available models ===")
    models = list_models()
    for model in models:
        print(f"  - {model}")
    print()
    
    # Test non-streaming
    print("=== Non-streaming test ===")
    result = send_prompt_non_streaming("Explain quantum entanglement simply.")
    print(f"Response: {result.get('response', 'No response')}")
    if 'load_duration' in result:
        print(f"Load time: {result['load_duration'] / 1e9:.2f}s")
    if 'total_duration' in result:
        print(f"Total time: {result['total_duration'] / 1e9:.2f}s")
    print()
    
    # Test streaming with verbose mode
    print("=== Streaming test (with metadata) ===")
    thinking_phase = True
    response_started = False
    
    for data in send_prompt_streaming("What is the speed of light?", verbose=True):
        # Show thinking tokens
        if data.get("thinking") and thinking_phase:
            print(f"[Thinking: {data['thinking']}]", end="", flush=True)
        
        # Show when response starts
        if data.get("response") and not response_started:
            if thinking_phase:
                print("\n[Response]:", end=" ", flush=True)
            thinking_phase = False
            response_started = True
        
        # Show response tokens
        if data.get("response"):
            print(data["response"], end="", flush=True)
        
        # Show final stats
        if data.get("done"):
            print("\n")
            if 'load_duration' in data and data['load_duration'] > 0:
                print(f"Model load time: {data['load_duration'] / 1e9:.2f}s")
            if 'prompt_eval_duration' in data:
                print(f"Prompt eval time: {data['prompt_eval_duration'] / 1e9:.2f}s")
            if 'eval_duration' in data:
                print(f"Response gen time: {data['eval_duration'] / 1e9:.2f}s")
            if 'total_duration' in data:
                print(f"Total time: {data['total_duration'] / 1e9:.2f}s")
    print()
