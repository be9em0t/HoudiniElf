#!/usr/bin/env python3
"""
Simple Calculator Script

A minimal example script demonstrating basic argument types.
"""

import argparse
import sys


def build_parser():
    """
    Build and return the argument parser.
    This function must be present for the GUI launcher to work.
    """
    parser = argparse.ArgumentParser(
        description="A simple calculator that performs basic arithmetic"
    )
    
    parser.add_argument(
        "number1",
        type=float,
        help="First number"
    )
    
    parser.add_argument(
        "number2",
        type=float,
        help="Second number"
    )
    
    parser.add_argument(
        "--operation",
        "-op",
        choices=["add", "subtract", "multiply", "divide"],
        default="add",
        help="Mathematical operation to perform"
    )
    
    parser.add_argument(
        "--precision",
        type=int,
        default=2,
        help="Number of decimal places to show in result"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed calculation steps"
    )
    
    return parser


def main():
    """Main execution function"""
    parser = build_parser()
    args = parser.parse_args()
    
    num1 = args.number1
    num2 = args.number2
    
    if args.verbose:
        print(f"Calculating: {num1} {args.operation} {num2}")
        print("="*50)
    
    # Perform calculation
    if args.operation == "add":
        result = num1 + num2
        symbol = "+"
    elif args.operation == "subtract":
        result = num1 - num2
        symbol = "-"
    elif args.operation == "multiply":
        result = num1 * num2
        symbol = "×"
    elif args.operation == "divide":
        if num2 == 0:
            print("Error: Cannot divide by zero!", file=sys.stderr)
            return 1
        result = num1 / num2
        symbol = "÷"
    
    # Format result
    formatted_result = round(result, args.precision)
    
    # Output
    if args.verbose:
        print(f"{num1} {symbol} {num2} = {formatted_result}")
        print("="*50)
        print("✓ Calculation complete!")
    else:
        print(formatted_result)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
