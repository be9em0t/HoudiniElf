import os
from typing import Any, Dict, Optional

try:
    from tools_Houdini.Houdini_Agentic_Mode import skills_houdini
    from tools_Houdini.Houdini_Agentic_Mode.rpc_bridge import check_houdini_rpc, run_houdini_python
except ImportError:
    try:
        from . import skills_houdini
        from .rpc_bridge import check_houdini_rpc, run_houdini_python
    except ImportError:
        import skills_houdini
        from rpc_bridge import check_houdini_rpc, run_houdini_python


def _is_llm_configured() -> bool:
    return bool(os.getenv("RAPTOR_MINI_API_KEY"))


def preprocess_request(user_text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    if not user_text or not isinstance(user_text, str) or not user_text.strip():
        return {
            'status': 'error',
            'message': 'Empty or invalid request',
        }

    # No environment key required for VS Code Copilot-hosted LLM usage.
    # LLM translation is allowed while run via agent pipeline.

    try:
        intent_payload = skills_houdini.interpret_request(user_text, context)
        return {
            'status': 'ok',
            'payload': intent_payload,
        }
    except Exception as exc:
        return {
            'status': 'error',
            'message': str(exc),
        }


def execute_request(request: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
    # Accept either a raw intent string or already-preprocessed payload
    if isinstance(request, dict) and 'intent' in request and 'tool' not in request:
        preprocess = preprocess_request(request.get('intent', ''), context)
        if preprocess['status'] != 'ok':
            return preprocess
        request = preprocess['payload']

    if not isinstance(request, dict):
        return {'status': 'error', 'message': 'Invalid request format'}

    tool = request.get('tool')
    args = request.get('args', {})

    if tool != 'run_houdini_python':
        return {
            'status': 'error',
            'message': f'Unsupported tool: {tool}',
        }

    code = args.get('code')
    if not code:
        return {
            'status': 'error',
            'message': 'Missing code argument for run_houdini_python',
        }

    rpc_status = check_houdini_rpc()
    if rpc_status != 'rpc_ok':
        return {
            'status': 'ok',
            'execution': {
                'tool': tool,
                'code': code,
                'result': f'RPC unavailable: {rpc_status}',
            },
        }

    try:
        result = run_houdini_python(code)
        return {
            'status': 'ok',
            'execution': {
                'tool': tool,
                'code': code,
                'result': result,
            },
        }
    except Exception as exc:
        return {
            'status': 'error',
            'message': f'Execution error: {exc}',
        }
