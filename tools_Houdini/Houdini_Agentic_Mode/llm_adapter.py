import os
from typing import Dict, Optional

try:
    import requests
except ImportError:
    requests = None


def ensure_llm_configured() -> str:
    """Verify mandatory LLM API key is set; raises clear ValueError otherwise."""
    api_key = os.getenv('RAPTOR_MINI_API_KEY')
    if not api_key:
        raise ValueError(
            'LLM translation not configured. Set RAPTOR_MINI_API_KEY with strong model support (Raptor mini).'
        )
    return api_key


def llm_translate_intent_to_houdini_code(intent_text: str, context: Optional[Dict] = None) -> str:
    """Translate user intent into Houdini python via Raptor mini API.

    Environment variables:
    - RAPTOR_MINI_API_KEY: API key for OpenAI/raptor endpoint.
    - RAPTOR_MINI_API_URL: Optional URL; default is OpenAI responses endpoint.

    If not configured, raises a clear ValueError.
    """
    api_key = ensure_llm_configured()

    api_url = os.getenv('RAPTOR_MINI_API_URL', 'https://api.openai.com/v1/responses')
    if requests is None:
        raise RuntimeError('requests library is required for LLM API calls; install via pip install requests')

    prompt = (
        'Translate the following Houdini intent to a single Python expression that uses hou.* APIs. ' 
        'Do not include explanatory text, only valid Python that can be eval() executed in Houdini with imported hou.\n' 
        f'Intent: {intent_text}\n'
    )

    payload = {
        'model': 'raptor-mini',
        'input': prompt,
        'max_output_tokens': 1024,
    }

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    r = requests.post(api_url, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()

    # OpenAI response field extraction may vary; use path if available.
    if 'output' in data and isinstance(data['output'], list):
        value = data['output'][0]
        if isinstance(value, dict) and 'content' in value:
            return value['content'][0].get('text', '').strip()
        if isinstance(value, str):
            return value.strip()

    if 'choices' in data and len(data['choices']) > 0:
        text = data['choices'][0].get('message', {}).get('content') if data['choices'][0].get('message') else data['choices'][0].get('text')
        if text:
            return text.strip()

    raise RuntimeError('Could not parse LLM response for intent translation.')
