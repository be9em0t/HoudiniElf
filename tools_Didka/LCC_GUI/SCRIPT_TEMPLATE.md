# Script Template for Launcher Compatibility

Use this template when creating new scripts for the launcher.

## Minimal Template

```python
#!/usr/bin/env python3
"""
Your Script Name

Brief description of what this script does.
"""

import argparse
import sys


def build_parser():
    """
    Build and return the argument parser.
    
    This function MUST exist for the launcher to work.
    The GUI will call this to discover your script's arguments.
    """
    parser = argparse.ArgumentParser(
        description="What your script does"
    )
    
    # Add your arguments here
    parser.add_argument("input", help="Input description")
    parser.add_argument("--option", "-o", help="Option description")
    
    return parser


def main():
    """Main execution function"""
    parser = build_parser()
    args = parser.parse_args()
    
    # Your script logic here
    print(f"Processing {args.input}...")
    
    return 0  # Return 0 for success, non-zero for errors


if __name__ == "__main__":
    sys.exit(main())
```

## Argument Types & Resulting Widgets

### 1. Positional Arguments → Text Field (Required)
```python
parser.add_argument("input_file", help="Input file path")
```

### 2. Boolean Flags → Checkbox
```python
parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
parser.add_argument("--no-cache", action="store_true", help="Disable caching")
```

### 3. Choice Arguments → Dropdown Menu
```python
parser.add_argument("--format", choices=["json", "xml", "csv"], default="json")
parser.add_argument("--mode", choices=["fast", "slow", "balanced"], default="balanced")
```

### 4. File/Path Arguments → Text Field + Browse Button
```python
parser.add_argument("--output-file", help="Output file path")
parser.add_argument("--input-dir", help="Input directory")
parser.add_argument("--config-path", help="Config file location")
```

*Auto-detected when argument name contains: file, path, dir, directory, folder, input, output*

### 5. Integer Arguments → Text Field (Numeric)
```python
parser.add_argument("--count", type=int, default=10, help="Number of iterations")
parser.add_argument("--max-items", type=int, help="Maximum items to process")
```

### 6. Float Arguments → Text Field (Numeric)
```python
parser.add_argument("--threshold", type=float, default=0.5, help="Threshold value")
parser.add_argument("--scale", type=float, help="Scaling factor")
```

### 7. Text Arguments → Text Field
```python
parser.add_argument("--name", default="default", help="Name to use")
parser.add_argument("--prefix", help="Text prefix")
```

## Best Practices

### 1. Always Provide Help Text
```python
# Good
parser.add_argument("--timeout", type=int, help="Connection timeout in seconds")

# Avoid
parser.add_argument("--timeout", type=int)
```

### 2. Set Sensible Defaults
```python
parser.add_argument("--threads", type=int, default=4, help="Number of threads")
parser.add_argument("--format", choices=["json", "xml"], default="json")
```

### 3. Mark Required Arguments
```python
parser.add_argument("--api-key", required=True, help="API key for authentication")
```

### 4. Use Short Options
```python
parser.add_argument("--verbose", "-v", action="store_true")
parser.add_argument("--output", "-o", help="Output file")
```

### 5. Provide Good Descriptions
```python
parser = argparse.ArgumentParser(
    description="Convert images to different formats with optional compression",
    epilog="Example: python script.py input.png --format jpg --quality 85"
)
```

### 6. Validate Inputs in main()
```python
def main():
    parser = build_parser()
    args = parser.parse_args()
    
    # Validate
    if args.count < 1:
        print("Error: count must be positive", file=sys.stderr)
        return 1
    
    # Process...
    return 0
```

## Common Patterns

### File Input/Output
```python
def build_parser():
    parser = argparse.ArgumentParser(description="Process files")
    parser.add_argument("input_file", help="Input file to process")
    parser.add_argument("--output-file", "-o", help="Output file (default: stdout)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    return parser
```

### Data Processing with Options
```python
def build_parser():
    parser = argparse.ArgumentParser(description="Data processor")
    parser.add_argument("data_file", help="Data file to process")
    parser.add_argument("--format", choices=["csv", "json", "xml"], default="csv")
    parser.add_argument("--filter", help="Filter expression")
    parser.add_argument("--limit", type=int, help="Max records to process")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser
```

### Batch Processing
```python
def build_parser():
    parser = argparse.ArgumentParser(description="Batch processor")
    parser.add_argument("input_dir", help="Input directory")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument("--pattern", default="*.txt", help="File pattern to match")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process subdirectories")
    parser.add_argument("--threads", type=int, default=4, help="Number of threads")
    return parser
```

## Testing Your Script

Before adding to the launcher, test independently:

```bash
# Test help
python your_script.py --help

# Test with arguments
python your_script.py input.txt --verbose --output result.txt

# Test error handling
python your_script.py nonexistent.txt
```

## Debugging Tips

### Script Not Appearing
- Check filename ends with `.py`
- Not in a subdirectory of `tools/`
- No syntax errors

### Parser Not Loading
- Ensure `build_parser()` function exists
- Must return an `ArgumentParser` object
- Check for import errors

### Widget Types Wrong
- Verify argument `type` parameter
- Check `action` (store_true/store_false)
- Ensure `choices` is a list
- Use path keywords in argument names

## Advanced: Custom Validation

```python
def validate_positive(value):
    """Custom validation function"""
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"{value} must be positive")
    return ivalue

def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=validate_positive, help="Positive integer")
    return parser
```

## Need Help?

1. Check `sample_text_processor.py` for comprehensive example
2. Check `simple_calculator.py` for minimal example
3. Read README.md for full documentation
4. Test your `build_parser()` function directly:
   ```python
   parser = build_parser()
   parser.print_help()
   ```
