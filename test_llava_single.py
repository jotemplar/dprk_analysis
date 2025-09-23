#!/usr/bin/env python3
"""Test single image with LLaVA"""

import sys
from pathlib import Path
from database.connection import get_session
from database.models import CapturedImage, ContentAnalysis
from utils.ollama_analyzer import OllamaAnalyzer
from utils.image_preprocessor import ImagePreprocessor

def test_single_image():
    """Test LLaVA on a single image"""
    print("Starting test...")
    
    # Get a single image without analysis
    session = get_session()
    image = session.query(CapturedImage).outerjoin(
        ContentAnalysis, CapturedImage.id == ContentAnalysis.result_id
    ).filter(
        (ContentAnalysis.scene_description == None) |
        (ContentAnalysis.scene_description == '')
    ).first()
    
    if not image:
        print("No images need processing")
        return
        
    print(f"Testing with image: {image.file_path}")
    
    # Process image
    try:
        preprocessor = ImagePreprocessor(max_size=896)
        analyzer = OllamaAnalyzer(model="llava")
        
        # Preprocess
        processed = preprocessor.standardize_image(image.file_path)
        print(f"Preprocessed image (base64 length: {len(processed)})")
        
        # Analyze
        result = analyzer.analyze_image(image.file_path)
        print(f"Analysis result: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_single_image()
