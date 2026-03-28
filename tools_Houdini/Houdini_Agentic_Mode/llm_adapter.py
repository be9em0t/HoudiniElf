import json
import os
from pathlib import Path
from typing import Dict, Optional

import requests


def _load_agent_prompt() -> str:
    prompt_path = Path(__file__).parent / 'houdini_agentic_mode.prompt.md'
    if prompt_path.exists():
        return prompt_path.read_text(encoding='utf-8')
    return ''


def llm_translate_intent_to_houdini_code(intent: str, context: Optional[Dict] = None) -> str:
    """Translate natural language intent into Houdini Python code using an LLM backend."""
    if not intent or not isinstance(intent, str):
        raise ValueError("Intent must be a non-empty string")

    context = context or {}
    cleaned_intent = intent.strip()

    system_prompt = _load_agent_prompt()
    user_prompt = (
        f"You are generating Houdini Python code for this intent: {cleaned_intent}. "
        "Return only valid Python code that uses hou nodes and operations."
    )

    openai_key = os.getenv('OPENAI_API_KEY')
    raptor_key = os.getenv('RAPTOR_MINI_API_KEY')

    if openai_key:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {openai_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                'max_tokens': 400,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        code = data['choices'][0]['message']['content'].strip()
        return code

    if raptor_key:
        # Placeholder endpoint for Raptor; adapt to your provider in production.
        response = requests.post(
            'https://api.raptor.example.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {raptor_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'raptor-mini',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                'max_tokens': 400,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        code = data['choices'][0]['message']['content'].strip()
        return code

    # fallback non-network stub
    sanitized_intent = cleaned_intent.replace('\n', ' ')
    return f"# no LLM key present; placeholder code for intent: {sanitized_intent}\nprint('llm missing')"
