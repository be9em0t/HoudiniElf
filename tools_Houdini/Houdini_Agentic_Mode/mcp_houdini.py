"""Minimal MCP-like router and dispatcher for Houdini agentic intent handling."""
from typing import Dict

from .intent_router import route_intent, execute_routed_intent
from .rpc_bridge import check_houdini_rpc


def preprocess_request(user_text: str, context: Dict = None) -> Dict:
    """Interpret user request and compute an action plan."""
    context = context or {}
    health = check_houdini_rpc()
    if health != 'rpc_ok':
        return {
            'status': 'rpc_unavailable',
            'message': (
                'Houdini RPC server is unavailable. Verify Houdini is running and listening on 127.0.0.1:5005 ' 
                'and that the startup script is installed in preferences/houdini/<version>/scripts/456.py.'
            ),
            'raw_health': health,
        }

    routed = route_intent(user_text, context)
    return {
        'status': 'ready',
        'intent': routed['intent'],
        'tool': routed['tool'],
        'args': routed['args'],
        'plan': f"Execute tool {routed['tool']} with args {routed['args']}",
    }


def execute_plan(plan: Dict):
    """Run an already routed plan. Assumes health check done in preprocess_request."""
    if plan.get('status') != 'ready':
        raise ValueError('Plan not ready for execution: ' + str(plan))

    result = execute_routed_intent({'tool': plan['tool'], 'args': plan['args']})
    return {'status': 'executed', 'result': result}
