#!/usr/bin/env python3
"""
Sample Python module with intentional code quality issues
for testing Ghostclaw analyzer.
"""

import os
import sys
import json
from typing import Optional, Dict, Any, List


def very_long_function_with_many_parameters(
    param1,
    param2,
    param3,
    param4,
    param5,
    param6,
    param7,
    param8,
    param9,
    param10,
    param11,
    param12,
):
    """
    A function with too many parameters (should be ≤5 ideally).
    This violates basic design principles and makes testing hard.
    """
    result = []
    for i in range(100):
        if i % 2 == 0:
            if i % 3 == 0:
                if i % 5 == 0:
                    result.append(i * 2)
                else:
                    result.append(i * 3)
            else:
                result.append(i * 4)
        else:
            result.append(i * 5)
    return result


def complex_nested_function(x):
    """
    A function with deep nesting and high cyclomatic complexity.
    Ghostclaw should flag this as high complexity.
    """
    if x > 0:
        if x < 10:
            if x % 2 == 0:
                if x % 3 == 0:
                    return "divisible by 6"
                else:
                    return "even but not by 3"
            else:
                if x % 3 == 0:
                    return "odd and divisible by 3"
                else:
                    return "odd prime-ish"
        else:
            if x < 50:
                if x % 5 == 0:
                    return "multiple of 5"
                else:
                    return "between 10 and 50"
            else:
                return "large number"
    else:
        if x == 0:
            return "zero"
        else:
            if x > -10:
                return "small negative"
            else:
                return "large negative"


class GodClass:
    """
    A God Class - does too many things, violates Single Responsibility.
    Ghostclaw should flag this as an architectural smell.
    """

    def __init__(self):
        self.data = []
        self.config = {}
        self.cache = {}
        self.log_messages = []

    def process_data(self, input_data):
        """Process data with validation, transformation, and caching."""
        # Validation
        if not input_data:
            raise ValueError("Input data cannot be empty")

        # Transformation
        transformed = []
        for item in input_data:
            if isinstance(item, dict):
                transformed.append({k.upper(): v for k, v in item.items()})
            elif isinstance(item, str):
                transformed.append(item.strip().title())
            else:
                transformed.append(item)

        # Caching
        cache_key = hash(tuple(transformed))
        if cache_key in self.cache:
            return self.cache[cache_key]

        # More processing...
        result = self._additional_processing(transformed)
        self.cache[cache_key] = result
        self.log_messages.append(f"Processed {len(input_data)} items")
        return result

    def _additional_processing(self, data):
        """Another responsibility - data analysis."""
        return {
            "count": len(data),
            "types": list(set(type(x).__name__ for x in data)),
            "sample": data[:3]
        }

    def save_to_file(self, filename: str):
        """Another responsibility - I/O."""
        with open(filename, 'w') as f:
            json.dump({
                "data": self.data,
                "config": self.config,
                "logs": self.log_messages
            }, f, indent=2)

    def load_from_file(self, filename: str):
        """Another responsibility - I/O."""
        with open(filename, 'r') as f:
            content = json.load(f)
        self.data = content.get("data", [])
        self.config = content.get("config", {})
        self.log_messages = content.get("logs", [])

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Another responsibility - validation."""
        required_keys = ["host", "port", "timeout"]
        for key in required_keys:
            if key not in config:
                return False
        if not isinstance(config["port"], int):
            return False
        if config["port"] < 1 or config["port"] > 65535:
            return False
        return True

    def generate_report(self) -> str:
        """Another responsibility - report generation."""
        lines = [
            "=== Ghostclaw Sample Report ===",
            f"Data items: {len(self.data)}",
            f"Config keys: {len(self.config)}",
            f"Log entries: {len(self.log_messages)}",
        ]
        return "\n".join(lines)


def unused_imports_and_variables():
    """
    Function with unused variables and imports.
    Ghostclaw should flag these as code smells.
    """
    import random  # This import is unused
    unused_var = "I'm never used"  # Unused variable
    x = 10
    y = 20
    z = x + y
    # z is computed but never used
    return None


def magic_numbers():
    """Demonstrate magic numbers in code."""
    result = []
    for i in range(86400):  # 86400 seconds in a day - should be a constant
        if i % 3600 == 0:    # 3600 seconds in an hour
            result.append(i)
    return result


def duplicate_code_example(data):
    """
    Function with duplicated logic that should be extracted.
    """
    # Duplicate block 1
    if isinstance(data, list):
        cleaned = []
        for item in data:
            if item is not None:
                cleaned.append(str(item).strip())
        data = cleaned

    # Some processing...
    processed = [x.upper() for x in data]

    # Duplicate block 2 (similar logic, should be DRY)
    if isinstance(processed, list):
        final = []
        for item in processed:
            if item is not None:
                final.append(item)
        processed = final

    return processed


if __name__ == "__main__":
    print("This is a sample Python module for Ghostclaw testing.")
    print("It contains various code quality issues for detection.")
