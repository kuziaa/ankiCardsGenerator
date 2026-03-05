#!/usr/bin/env python3
"""
Quick start script for the project.
Checks dependencies and runs deck generation.
"""

import subprocess
import sys
from pathlib import Path

def check_python_version():
    """Check Python version."""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_requirements():
    """Check if required packages are installed."""
    required = ['genanki', 'gtts', 'PIL', 'requests']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} not installed")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Install missing packages:")
        print(f"   pip install -r requirements.txt")
        return False
    
    return True

def check_config():
    """Check if configuration file exists."""
    config_path = Path("config.properties")
    sample_path = Path("config.properties.sample")
    
    if not config_path.exists():
        if sample_path.exists():
            print("⚠️  config.properties not found")
            print(f"   Copy from template: cp config.properties.sample config.properties")
        else:
            print("❌ Neither config.properties nor config.properties.sample found")
            return False
        return False
    
    print("✅ config.properties found")
    return True

def check_csv():
    """Check if CSV file with data exists."""
    csv_path = Path("src/resources/cards.csv")
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return False
    
    # Check that file is not empty
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if len(lines) < 2:  # At least header and one row
        print(f"⚠️  CSV file is almost empty ({len(lines)} rows)")
        return False
    
    print(f"✅ CSV file found ({len(lines)} rows)")
    return True

def main():
    """Main function for environment check and launch."""
    print("=" * 60)
    print("Anki Cards Generator - Environment Check")
    print("=" * 60)
    print()
    
    checks = [
        ("Python version", check_python_version),
        ("Dependencies", check_requirements),
        ("Configuration", check_config),
        ("CSV file", check_csv),
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n📋 Checking: {check_name}")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ Error during check: {e}")
            results.append((check_name, False))
    
    print("\n" + "=" * 60)
    print("Check Results:")
    print("=" * 60)
    
    all_passed = True
    for check_name, result in results:
        status = "✅ OK" if result else "❌ ERROR"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✨ All checks passed!")
        print("\n🚀 To run, execute:")
        print("   cd src")
        print("   python anki_generator.py")
    else:
        print("\n⚠️  Fix errors before running")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
