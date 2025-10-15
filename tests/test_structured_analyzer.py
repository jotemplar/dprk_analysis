#!/usr/bin/env python3
"""Test the structured Ollama analyzer with Gemma3:12b"""

from utils.ollama_structured import StructuredOllamaAnalyzer
from database.connection import get_session
from database.models import CapturedImage
import json


def test_structured_analyzer():
    """Test the improved analyzer with structured outputs"""
    print("=" * 60)
    print("Testing Structured Ollama Analyzer with Gemma3:12b")
    print("=" * 60)

    # Get a test image (preferably PNG to avoid JPEG issues)
    session = get_session()
    # Try to get a PNG first, fallback to any image
    image = session.query(CapturedImage).filter(
        CapturedImage.file_path.like('%.png')
    ).first()
    if not image:
        image = session.query(CapturedImage).limit(10).all()[5] if session.query(CapturedImage).count() > 5 else None

    if not image:
        print("No images found in database")
        return

    print(f"\n📷 Test image: {image.file_path}")

    # Test with Gemma3:12b
    print("\n🔍 Testing with Gemma3:12b model...")
    analyzer = StructuredOllamaAnalyzer(model="gemma3:12b")

    # Check connection
    if not analyzer.test_connection():
        print("Failed to connect to Ollama")
        return

    # Analyze image
    result = analyzer.analyze_image(image.file_path)

    if result:
        print("\n✅ Analysis successful!")
        print("\n📊 Structured Output:")
        print("-" * 40)

        # Print key fields
        print(f"Scene Description: {result.get('scene_description', 'N/A')[:100]}...")
        print(f"Concern Level: {result.get('concern_level', 'N/A')}")
        print(f"Personnel Count: {result.get('personnel_count', 0)}")
        print(f"Activity Type: {result.get('activity_type', 'N/A')}")
        print(f"Supervision Present: {result.get('supervision_present', False)}")
        print(f"Confidence Score: {result.get('confidence_score', 0.0):.2f}")

        # Check if description is not empty
        if result.get('scene_description'):
            print("\n✅ Scene description is populated!")
        else:
            print("\n⚠️ Warning: Scene description is empty")

        # Show concern indicators if any
        if result.get('concern_indicators'):
            print(f"\n🚨 Concern Indicators:")
            for indicator in result['concern_indicators'][:3]:
                print(f"  - {indicator}")

        # Save full result for inspection
        with open('test_structured_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("\n📁 Full result saved to test_structured_result.json")

    else:
        print("\n❌ Analysis failed")

    session.close()


if __name__ == "__main__":
    test_structured_analyzer()