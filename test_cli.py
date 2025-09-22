#!/usr/bin/env python3
"""Test script for the vector CLI."""

import json
import random
import subprocess
import sys

def run_cli_command(args):
    """Run a CLI command and return the result."""
    cmd = ["E:/02-regscout/.venv/Scripts/python.exe", "e:/02-regscout/vector_cli.py"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def generate_random_vector(size=128):
    """Generate a random vector of specified size."""
    return [round(random.uniform(-1, 1), 4) for _ in range(size)]

def test_cli():
    """Test the CLI functionality."""
    print("🧪 Testing Vector CLI functionality...")
    
    # Test 1: List collections
    print("\n1. Testing list-collections...")
    code, stdout, stderr = run_cli_command(["list-collections"])
    if code == 0:
        print("✅ List collections works")
        print(stdout.strip())
    else:
        print(f"❌ Error: {stderr}")
        return
    
    # Test 2: Create a test collection
    print("\n2. Testing create-collection...")
    code, stdout, stderr = run_cli_command([
        "create-collection", "cli_test_collection", "--vector-size", "128"
    ])
    if code == 0:
        print("✅ Create collection works")
        print(stdout.strip())
    else:
        print(f"❌ Error: {stderr}")
        return
    
    # Test 3: Get collection info
    print("\n3. Testing collection-info...")
    code, stdout, stderr = run_cli_command(["collection-info", "cli_test_collection"])
    if code == 0:
        print("✅ Collection info works")
        print(stdout.strip())
    else:
        print(f"❌ Error: {stderr}")
    
    # Test 4: Insert a point
    print("\n4. Testing insert-point...")
    vector = generate_random_vector(128)
    vector_json = json.dumps(vector)
    payload = json.dumps({"test": "data", "type": "example"})
    
    code, stdout, stderr = run_cli_command([
        "insert-point", "cli_test_collection", "1", vector_json, "--payload", payload
    ])
    if code == 0:
        print("✅ Insert point works")
        print(stdout.strip())
    else:
        print(f"❌ Error: {stderr}")
    
    # Test 5: Insert another point
    print("\n5. Testing insert another point...")
    vector2 = generate_random_vector(128)
    vector2_json = json.dumps(vector2)
    payload2 = json.dumps({"test": "data2", "type": "example2"})
    
    code, stdout, stderr = run_cli_command([
        "insert-point", "cli_test_collection", "2", vector2_json, "--payload", payload2
    ])
    if code == 0:
        print("✅ Insert second point works")
        print(stdout.strip())
    else:
        print(f"❌ Error: {stderr}")
    
    # Test 6: Search
    print("\n6. Testing search...")
    query_vector = generate_random_vector(128)
    query_json = json.dumps(query_vector)
    
    code, stdout, stderr = run_cli_command([
        "search", "cli_test_collection", query_json, "--top-k", "2"
    ])
    if code == 0:
        print("✅ Search works")
        print(stdout.strip())
    else:
        print(f"❌ Error: {stderr}")
    
    # Test 7: List documents (should show none since we inserted points, not documents)
    print("\n7. Testing list-documents...")
    code, stdout, stderr = run_cli_command(["list-documents", "cli_test_collection"])
    if code == 0:
        print("✅ List documents works")
        print(stdout.strip())
    else:
        print(f"❌ Error: {stderr}")
    
    # Test 8: Clean up - delete collection
    print("\n8. Testing delete-collection...")
    code, stdout, stderr = run_cli_command([
        "delete-collection", "cli_test_collection", "--force"
    ])
    if code == 0:
        print("✅ Delete collection works")
        print(stdout.strip())
    else:
        print(f"❌ Error: {stderr}")
    
    print("\n🎉 CLI testing completed!")

if __name__ == "__main__":
    test_cli()