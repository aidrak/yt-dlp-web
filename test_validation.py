#!/usr/bin/env python3
"""
Test file to trigger validation hook
This should trigger the validate_rules.py script
"""


def test_function():
    # This is a simple test function
    api_key = "hardcoded_secret_key_123"  # This should trigger a security warning
    return api_key


if __name__ == "__main__":
    print("Testing validation...")
    result = test_function()
    print(f"Result: {result}")
