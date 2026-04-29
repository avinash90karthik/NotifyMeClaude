"""Test that SQL queries use parameterized statements.

The bug: list_predictions used f-string interpolation for status_filter,
allowing SQL injection via crafted input.
"""

import os
import sqlite3
import pytest
import sys
import ast

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSQLInjectionPrevention:
    """Verify no raw string interpolation in SQL queries."""

    def test_prediction_db_no_fstring_sql(self):
        """prediction_db.py must not have f-string SQL with user input."""
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'scripts', 'ops', 'prediction_db.py'
        )
        with open(src_path) as f:
            source = f.read()

        # Parse AST and find f-strings containing SQL keywords inside execute() calls
        tree = ast.parse(source)

        dangerous_patterns = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Look for conn.execute(f"...") or .execute(f"...")
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == 'execute':
                    for arg in node.args:
                        if isinstance(arg, ast.JoinedStr):  # f-string
                            # Reconstruct f-string to check for user-controlled values
                            for val in arg.values:
                                if isinstance(val, ast.FormattedValue):
                                    # Check if the interpolated value references args.*
                                    val_src = ast.dump(val.value)
                                    if 'args' in val_src and 'status' in val_src.lower():
                                        dangerous_patterns.append(
                                            f"Line {node.lineno}: f-string SQL with args reference"
                                        )

        assert not dangerous_patterns, \
            f"Found dangerous f-string SQL patterns:\n" + "\n".join(dangerous_patterns)

    def test_list_predictions_uses_parameterized_query(self):
        """list_predictions must not interpolate status_filter directly into SQL."""
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'scripts', 'ops', 'prediction_db.py'
        )
        with open(src_path) as f:
            source = f.read()

        # Find the list_predictions function body
        in_func = False
        func_lines = []
        for line in source.split('\n'):
            if 'def list_predictions' in line:
                in_func = True
            elif in_func and line and not line[0].isspace() and line.strip().startswith('def '):
                break
            elif in_func:
                func_lines.append(line)

        func_source = '\n'.join(func_lines)

        # The old dangerous pattern: f"...WHERE status = '{args.status_filter}'"
        assert "'{args.status_filter}'" not in func_source, \
            "list_predictions still interpolates status_filter directly into SQL"

        # Must use parameterized query with ? placeholder
        assert 'WHERE status=?' in func_source, \
            "list_predictions should use ? placeholder for status filter"
