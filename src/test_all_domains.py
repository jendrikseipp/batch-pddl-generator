#!/usr/bin/env python3
"""
Test script to validate all domains work correctly in dry mode.
This script tests that all domains can generate configurations without errors.
"""

import sys
import os
import subprocess
from pathlib import Path

# File is now in src directory, so import directly
from domains import get_domains


def test_domain(domain_name, max_configs=5):
    """Test a single domain by generating configurations in dry mode."""
    print(f"\n=== Testing {domain_name} domain ===")
    
    # Create temporary directories that the script expects
    generators_dir = "tasks"  # This contains the domain subdirectories (relative to src/)
    destdir = "/tmp"  # Dummy directory since we're using --dry-run
    
    cmd = [
        sys.executable,
        "generate-instances.py",
        generators_dir,
        domain_name,
        destdir,
        "--dry-run",
        "--num-random-seeds", str(max_configs)
    ]
    
    try:
        # Special timeout for schedule domain (it has a very large config space)
        timeout = 120 if domain_name == "schedule" else 30
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent  # This is now src/, so commands run from src/
        )
        
        if result.returncode == 0:
            # Parse number of configurations from output
            lines = result.stdout.strip().split('\n')
            num_configs = 0
            
            # Look for "Number of configurations: X" line
            for line in lines:
                if line.startswith('Number of configurations:'):
                    try:
                        num_configs = int(line.split(':')[1].strip())
                        break
                    except (ValueError, IndexError):
                        pass
            
            print(f"✅ SUCCESS: Generated {num_configs} configurations")
            return True
        else:
            print(f"❌ FAILED: Return code {result.returncode}")
            if result.stderr:
                print(f"   STDERR: {result.stderr}")
            if result.stdout:
                print(f"   STDOUT: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT: Domain took longer than 30 seconds")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    """Test all domains and report results."""
    print("Testing all domains with configuration generation...")
    print("=" * 60)
    
    domains = get_domains()
    domain_names = list(domains.keys())
    
    print(f"Found {len(domain_names)} domains to test:")
    for name in sorted(domain_names):
        print(f"  - {name}")
    
    print("\nStarting domain tests...")
    
    passed = []
    failed = []
    
    for domain_name in sorted(domain_names):
        success = test_domain(domain_name, max_configs=3)
        if success:
            passed.append(domain_name)
        else:
            failed.append(domain_name)
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print(f"✅ PASSED: {len(passed)}/{len(domain_names)} domains")
    if passed:
        print("   Successful domains:", ", ".join(passed))
    
    if failed:
        print(f"❌ FAILED: {len(failed)} domains")
        print("   Failed domains:", ", ".join(failed))
        return 1
    else:
        print("\n🎉 All domains working correctly!")
        return 0


if __name__ == "__main__":
    sys.exit(main())