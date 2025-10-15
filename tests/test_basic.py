#!/usr/bin/env python3
"""Basic test of DPRK system components"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_database():
    """Test database connection and models"""
    print("\n1. Testing Database Connection...")
    try:
        from database.connection import get_session
        from database.models import SearchQuery, SearchResult

        session = get_session()
        count = session.query(SearchQuery).count()
        print(f"   ✓ Database connected")
        print(f"   ✓ Found {count} search queries in database")
        session.close()
        return True
    except Exception as e:
        print(f"   ✗ Database error: {e}")
        return False

def test_search_terms():
    """Test search terms loading"""
    print("\n2. Testing Search Terms...")
    try:
        from search_terms.dprk_images_search_terms import search_terms_comprehensive
        print(f"   ✓ Loaded {len(search_terms_comprehensive)} search terms")

        # Show sample terms
        print("   Sample terms:")
        for term in search_terms_comprehensive[:3]:
            print(f"      - {term[:50]}...")
        return True
    except Exception as e:
        print(f"   ✗ Search terms error: {e}")
        return False

def test_directory_structure():
    """Test directory structure"""
    print("\n3. Testing Directory Structure...")

    directories = [
        Path("/Volumes/X5/_CODE_PROJECTS/DPRK/captured_data/images"),
        Path("/Volumes/X5/_CODE_PROJECTS/DPRK/captured_data/screenshots"),
        Path("/Volumes/X5/_CODE_PROJECTS/DPRK/reports"),
        Path("/Volumes/X5/_CODE_PROJECTS/DPRK/logs")
    ]

    all_exist = True
    for dir_path in directories:
        if dir_path.exists():
            print(f"   ✓ {dir_path.name}/ exists")
        else:
            print(f"   ✗ {dir_path.name}/ missing")
            all_exist = False

    return all_exist

def test_env_config():
    """Test environment configuration"""
    print("\n4. Testing Environment Configuration...")
    from dotenv import load_dotenv
    load_dotenv()

    required_vars = [
        "DB_NAME",
        "SERP_API_KEY",
        "OLLAMA_HOST",
        "IMAGE_STORAGE_PATH"
    ]

    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✓ {var} is configured")
        else:
            print(f"   ✗ {var} is missing")
            all_set = False

    return all_set

def test_ollama_connection():
    """Test Ollama connection"""
    print("\n5. Testing Ollama Connection...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("   ✓ Ollama server is running")
            data = response.json()
            if 'models' in data and data['models']:
                print(f"   ✓ Found {len(data['models'])} models installed")
                for model in data['models'][:3]:
                    print(f"      - {model['name']}")
            else:
                print("   ⚠ No models installed. Run: ollama pull llava")
            return True
        else:
            print("   ✗ Ollama server returned error")
            return False
    except:
        print("   ✗ Ollama server not running. Run: ollama serve")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("DPRK SYSTEM BASIC TESTS")
    print("=" * 60)

    results = {
        "Database": test_database(),
        "Search Terms": test_search_terms(),
        "Directories": test_directory_structure(),
        "Environment": test_env_config(),
        "Ollama": test_ollama_connection()
    }

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:15} : {status}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All basic tests passed!")
        print("\nTo run the full pipeline:")
        print("1. Install dependencies: uv pip install -r requirements.txt")
        print("2. Install Playwright: uv run playwright install chromium")
        print("3. Start Ollama: ollama serve")
        print("4. Run pipeline: uv run python main.py test")
    else:
        print("✗ Some tests failed. Please fix issues above.")
    print("=" * 60)

if __name__ == "__main__":
    main()