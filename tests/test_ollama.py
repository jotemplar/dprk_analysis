#!/usr/bin/env python3
"""Test Ollama image analysis with a captured image"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utils.ollama_analyzer import OllamaAnalyzer

def test_ollama():
    print("=" * 60)
    print("TESTING OLLAMA IMAGE ANALYSIS")
    print("=" * 60)

    # Initialize analyzer
    analyzer = OllamaAnalyzer()

    # Test connection
    print("\n1. Testing Ollama connection...")
    if not analyzer.test_connection():
        print("❌ Failed to connect to Ollama")
        return False

    # Ensure model
    print("\n2. Ensuring llava model...")
    if not analyzer.ensure_model():
        print("❌ Failed to ensure model")
        return False

    # Find a test image
    print("\n3. Finding test image...")
    test_images = list(Path("captured_data/images").glob("**/*.jpg"))

    if not test_images:
        print("❌ No images found to test")
        return False

    test_image = str(test_images[0])
    print(f"   Using: {test_image}")

    # Analyze image
    print("\n4. Analyzing image...")
    analysis = analyzer.analyze_image(test_image)

    if not analysis:
        print("❌ Analysis failed")
        return False

    # Display results
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)

    print(f"\n📍 Scene: {analysis.get('scene_description', 'N/A')[:200]}...")
    print(f"\n🏭 Environment: {analysis.get('environment_type', 'N/A')}")
    print(f"\n👥 Personnel Count: {analysis.get('personnel_count', 0)}")
    print(f"👤 Personnel Types: {', '.join(analysis.get('personnel_types', []))}")
    print(f"\n🔧 Activity Type: {analysis.get('activity_type', 'N/A')}")
    print(f"📝 Activity: {analysis.get('activity_description', 'N/A')[:200]}...")
    print(f"\n⚠️  Concern Level: {analysis.get('concern_level', 'N/A')}")
    print(f"👮 Supervision Present: {analysis.get('supervision_present', False)}")

    if analysis.get('concern_indicators'):
        print(f"\n🚨 Concern Indicators:")
        for indicator in analysis.get('concern_indicators', [])[:3]:
            print(f"   - {indicator[:100]}")

    print(f"\n⏱️  Processing Time: {analysis.get('processing_time', 0):.1f}s")
    print(f"🎯 Confidence Score: {analysis.get('confidence_score', 0):.2f}")

    print("\n" + "=" * 60)
    print("✅ OLLAMA TEST SUCCESSFUL!")
    print("=" * 60)

    return True

if __name__ == "__main__":
    success = test_ollama()
    sys.exit(0 if success else 1)