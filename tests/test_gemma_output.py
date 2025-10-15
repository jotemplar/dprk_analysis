#!/usr/bin/env python3
"""Test what Gemma3:12b returns"""

from utils.ollama_analyzer import OllamaAnalyzer
from database.connection import get_session
from database.models import CapturedImage

def test_gemma_output():
    # Get one image
    session = get_session()
    image = session.query(CapturedImage).first()
    
    if image:
        print(f"Testing with image: {image.file_path}")
        
        # Analyze with Gemma3:12b
        analyzer = OllamaAnalyzer(model="gemma3:12b")
        result = analyzer.analyze_image(image.file_path)
        
        print("\nGemma3:12b returned:")
        print(f"Keys: {result.keys()}")
        print(f"scene_description: '{result.get('scene_description', 'NOT FOUND')}'")
        print(f"scene_description length: {len(result.get('scene_description', ''))}")
        print(f"concern_level: {result.get('concern_level')}")
        
        # Check if it's empty
        if not result.get('scene_description'):
            print("\n⚠️ WARNING: scene_description is empty!")
            print(f"Full result: {result}")
    
    session.close()

if __name__ == "__main__":
    test_gemma_output()
