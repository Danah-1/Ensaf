"""
Ensaf Test Runner
=================
Run all tests and generate HTML report.

Usage:
    python run_tests.py          # Run all tests
    python run_tests.py unit     # Run unit tests only
    python run_tests.py integ    # Run integration tests only
    python run_tests.py system   # Run system tests only
"""

import subprocess
import sys
import os

def main():
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    level = sys.argv[1] if len(sys.argv) > 1 else 'all'

    # Map shorthand to file
    test_map = {
        'unit': 'test_unit.py',
        'integ': 'test_integration.py',
        'integration': 'test_integration.py',
        'system': 'test_system.py',
    }

    if level == 'all':
        target = test_dir
    elif level in test_map:
        target = os.path.join(test_dir, test_map[level])
    else:
        print(f"Unknown test level: {level}")
        print("Usage: python run_tests.py [all|unit|integ|system]")
        return

    print("=" * 60)
    print(f"  إنصاف - Ensaf Test Suite")
    print(f"  Running: {level.upper()} tests")
    print("=" * 60)

    # Run pytest with verbose output
    cmd = [
        sys.executable, '-m', 'pytest',
        target,
        '-v',
        '--tb=short',
        '-x',  # Stop on first failure for debugging
        f'--html=test_report.html',
        '--self-contained-html',
    ]

    # Fallback if pytest-html not installed
    try:
        result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
    except Exception:
        # Run without HTML report
        cmd_simple = [
            sys.executable, '-m', 'pytest',
            target,
            '-v',
            '--tb=short',
        ]
        result = subprocess.run(cmd_simple, cwd=os.path.dirname(__file__))

    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("  ✅ ALL TESTS PASSED")
    else:
        print("  ❌ SOME TESTS FAILED")
    print("=" * 60)

    return result.returncode

if __name__ == '__main__':
    sys.exit(main())
