#!/usr/bin/env python3
"""Test script for the delete command functionality."""

import subprocess
import sys
from pathlib import Path

def run_command(cmd_args):
    """Run a vector-agent command and return the result."""
    # Use the venv Python executable
    venv_python = Path(".venv/Scripts/python.exe")
    if venv_python.exists():
        python_exe = str(venv_python)
    else:
        python_exe = sys.executable
    
    cmd = [python_exe, "-m", "vector.agent"] + cmd_args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def test_delete_help():
    """Test that the delete command shows up in help."""
    print("🧪 Testing delete command help...")
    
    returncode, stdout, stderr = run_command(["--help"])
    
    if returncode != 0:
        print(f"❌ Help command failed: {stderr}")
        return False
    
    if "delete" not in stdout:
        print("❌ Delete command not found in help")
        print("Help output:", stdout)
        return False
    
    print("✅ Delete command appears in help")
    return True

def test_delete_command_help():
    """Test the delete command's own help."""
    print("🧪 Testing delete command specific help...")
    
    returncode, stdout, stderr = run_command(["delete", "--help"])
    
    if returncode != 0:
        print(f"❌ Delete help command failed: {stderr}")
        return False
    
    expected_args = ["--document-id", "--name", "--no-cleanup", "--force"]
    for arg in expected_args:
        if arg not in stdout:
            print(f"❌ Expected argument {arg} not found in delete help")
            print("Delete help output:", stdout)
            return False
    
    print("✅ Delete command help shows correct arguments")
    return True

def test_delete_validation():
    """Test that delete command validates required arguments."""
    print("🧪 Testing delete command argument validation...")
    
    # Test with no arguments (should fail)
    returncode, stdout, stderr = run_command(["delete"])
    
    if returncode == 0:
        print("❌ Delete command should fail without arguments")
        return False
    
    if "one of the arguments --document-id --name is required" not in stderr:
        print("❌ Expected error message not found")
        print("Stderr:", stderr)
        return False
    
    print("✅ Delete command properly validates arguments")
    return True

def main():
    """Run all tests."""
    print("🚀 Testing delete command implementation...\n")
    
    tests = [
        test_delete_help,
        test_delete_command_help, 
        test_delete_validation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
        print()
    
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())