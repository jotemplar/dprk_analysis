#!/usr/bin/env python3
"""Quick test of llava model on a captured image"""

import sys
from pathlib import Path
from utils.ollama_analyzer import OllamaAnalyzer

# Get first image
images = list(Path("captured_data/images").glob("**/*.jpg"))
if not images:
    print("No images found")
    sys.exit(1)

test_image = str(images[0])
print(f"Testing with: {test_image}")
print(f"Image name: {images[0].name}\n")

# Analyze
analyzer = OllamaAnalyzer()
print(f"Using model: {analyzer.model}\n")

print("Analyzing image...")
analysis = analyzer.analyze_image(test_image)

if analysis:
    print("\n✅ Analysis successful!")
    print(f"Scene: {analysis.get('scene_description', 'N/A')[:100]}...")
    print(f"Personnel: {analysis.get('personnel_count', 0)} people")
    print(f"Environment: {analysis.get('environment_type', 'unknown')}")
    print(f"Concern level: {analysis.get('concern_level', 'unknown')}")
    print(f"Processing time: {analysis.get('processing_time', 0):.1f}s")
else:
    print("❌ Analysis failed")