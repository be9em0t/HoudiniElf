import argparse
import json

from .intent_router import route_intent, execute_routed_intent


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
        output['result'] = execute_routed_intent(routed)

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
