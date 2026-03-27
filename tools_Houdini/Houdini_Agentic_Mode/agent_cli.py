import argparse
import json
import os
import sys

try:
    from .intent_router import route_intent, execute_routed_intent
except ImportError:
    # Allow running as script from this directory: add parent path to sys.path
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    from intent_router import route_intent, execute_routed_intent


def main():
    parser = argparse.ArgumentParser(description='Houdini agentic CLI')
    parser.add_argument('--intent', type=str, required=True, help='Natural language intent')
    parser.add_argument('--target_path', type=str, default='/obj', help='Target Houdini network path')
    parser.add_argument('--node_path', type=str, help='Node path for VEX or inspect calls')
    parser.add_argument('--file_path', type=str, help='VEX file path for push_vex calls')
    parser.add_argument('--code', type=str, help='Explicit python code for run_houdini_python fallback')
    parser.add_argument('--dry_run', action='store_true', help='Do not execute side-effect call')

    args = parser.parse_args()
    context = {
        'target_path': args.target_path,
        'node_path': args.node_path,
        'file_path': args.file_path,
        'code': args.code,
    }

    routed = route_intent(args.intent, context)
    output = {
        'intent': routed['intent'],
        'tool': routed['tool'],
        'args': routed['args'],
        'result': None,
        'dry_run': args.dry_run,
    }

    if not args.dry_run:
        try:
            from .rpc_bridge import check_houdini_rpc
        except ImportError:
            from rpc_bridge import check_houdini_rpc

        health = check_houdini_rpc()
        if health != 'rpc_ok':
            output['error'] = health
            output['notes'] = (
                'Houdini RPC is unavailable. Please verify Houdini is running and that the RPC server script is loaded. '
                'Check that Houdini has loaded scripts/456.py or equivalent and that port 5005 on 127.0.0.1 is reachable.'
            )
        else:
            try:
                output['result'] = execute_routed_intent(routed)
            except ConnectionError as ce:
                output['error'] = str(ce)
                output['notes'] = (
                    'Houdini RPC server became unavailable during execution. Ensure Houdini is running, the RPC startup script is active, and retry.'
                )
            except Exception as e:
                output['error'] = str(e)

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
