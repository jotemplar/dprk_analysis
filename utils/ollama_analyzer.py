"""Ollama local LLM for sensitive image content analysis"""

import os
import json
import base64
import time
from pathlib import Path
from typing import Dict, Optional, List
import ollama
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

class OllamaAnalyzer:
    """Analyze images using local Ollama LLM for sensitive content"""

    def __init__(self, model=None):
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        # Allow model override via parameter, else use env or default to llava
        if model:
            self.model = model
        else:
            self.model = "llava" if "OLLAMA_MODEL" not in os.environ else os.getenv("OLLAMA_MODEL", "llava")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", 300))
        self.client = ollama.Client(host=self.host)

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 for analysis"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def analyze_image(self, image_path: str) -> Optional[Dict]:
        """
        Analyze a single image for sensitive content

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with analysis results
        """
        try:
            # Check if file exists
            if not Path(image_path).exists():
                print(f"   ✗ Image file not found: {image_path}")
                return None

            # Encode image
            image_base64 = self.encode_image(image_path)

            # Create analysis prompt
            prompt = self._create_analysis_prompt()

            # Start timing
            start_time = time.time()

            # Send to Ollama for analysis
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                images=[image_base64],
                options={
                    "temperature": 0.3,
                    "num_predict": 1000
                }
            )

            # Calculate processing time
            processing_time = time.time() - start_time

            # Parse response
            analysis = self._parse_analysis_response(response['response'])
            analysis['processing_time'] = processing_time
            analysis['analysis_model'] = self.model

            print(f"   ✓ Image analyzed in {processing_time:.1f}s")
            return analysis

        except Exception as e:
            print(f"   ✗ Error analyzing image: {e}")
            return None

    def _create_analysis_prompt(self) -> str:
        """Create prompt for image analysis aligned with humanitarian objectives"""
        return """Analyze this image focusing on humanitarian conditions and welfare indicators:

1. WORKING CONDITIONS ASSESSMENT:
   - Presence/absence of safety equipment (helmets, harnesses, protective gear, gloves, safety boots)
   - Environmental hazards (heights without barriers, exposed machinery, extreme weather, poor lighting)
   - Signs of physical strain, exhaustion, or fatigue in workers
   - Quality and adequacy of tools and equipment
   - Visible safety violations or dangerous practices

2. LIVING CONDITIONS EVALUATION:
   - Housing quality (overcrowded rooms, deteriorated buildings, temporary/makeshift structures)
   - Sleeping arrangements (beds per room, personal space availability)
   - Sanitation facilities if visible (bathrooms, washing areas)
   - Isolation from local community (remote location, separated compounds)
   - Perimeter restrictions (fences, walls, barriers, controlled access)

3. SUPERVISION & CONTROL INDICATORS:
   - Visible guards, handlers, or supervisors not engaged in work
   - Workers wearing uniforms suggesting institutional control
   - Group formations indicating controlled or restricted movement
   - Surveillance equipment, cameras, or watchtowers
   - Restricted access points, gates, or checkpoints
   - Workers accompanied by non-working escorts

4. HEALTH & WELFARE OBSERVATIONS:
   - Physical appearance suggesting malnutrition (thin, gaunt appearance)
   - Inadequate clothing for weather conditions (cold/heat exposure)
   - Visible injuries, illness, or untreated medical conditions
   - Workers operating in extreme weather without protection
   - Absence of rest areas, break facilities, or shade/shelter
   - Signs of continuous work without adequate breaks

5. CONCERN LEVEL CLASSIFICATION:
   Rate the overall humanitarian concern level:
   - CRITICAL: Immediate danger, severe exploitation, or life-threatening conditions
   - HIGH: Multiple serious concerns, systematic safety violations, harsh conditions
   - MEDIUM: Some concerning elements, substandard conditions, supervision present
   - LOW: Minor concerns, basic conditions met, standard workplace environment

   List specific visual evidence supporting your classification.
   Note any indicators of forced labor, restriction of movement, or exploitation.

Provide detailed, objective observations based only on visible evidence in the image."""

    def _parse_analysis_response(self, response_text: str) -> Dict:
        """Parse the LLM response into structured data"""
        try:
            # Initialize result dictionary
            result = {
                'scene_description': '',
                'location_assessment': '',
                'environment_type': 'unknown',
                'personnel_count': 0,
                'personnel_types': [],
                'uniform_identification': '',
                'activity_type': 'unknown',
                'activity_description': '',
                'concern_level': 'low',
                'concern_indicators': [],
                'supervision_present': False,
                'restriction_indicators': [],
                'confidence_score': 0.0,
                'raw_analysis': response_text
            }

            # Parse response text
            lines = response_text.split('\n')
            current_section = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Detect sections
                if 'SCENE DESCRIPTION' in line.upper():
                    current_section = 'scene'
                elif 'LOCATION ASSESSMENT' in line.upper():
                    current_section = 'location'
                elif 'PERSONNEL' in line.upper():
                    current_section = 'personnel'
                elif 'ACTIVITY' in line.upper():
                    current_section = 'activity'
                elif 'WORKING CONDITIONS' in line.upper() or 'CONDITIONS' in line.upper():
                    current_section = 'conditions'
                elif 'CONCERN' in line.upper():
                    current_section = 'concern'
                else:
                    # Add content to appropriate section
                    if current_section == 'scene':
                        result['scene_description'] += line + ' '
                    elif current_section == 'location':
                        result['location_assessment'] += line + ' '
                        # Extract environment type
                        if 'industrial' in line.lower():
                            result['environment_type'] = 'industrial'
                        elif 'military' in line.lower():
                            result['environment_type'] = 'military'
                        elif 'educational' in line.lower():
                            result['environment_type'] = 'educational'
                        elif 'residential' in line.lower():
                            result['environment_type'] = 'residential'
                    elif current_section == 'personnel':
                        # Extract personnel count
                        import re
                        numbers = re.findall(r'\d+', line)
                        if numbers:
                            result['personnel_count'] = int(numbers[0])
                        # Extract personnel types
                        if 'worker' in line.lower():
                            result['personnel_types'].append('workers')
                        if 'soldier' in line.lower():
                            result['personnel_types'].append('soldiers')
                        if 'supervisor' in line.lower() or 'guard' in line.lower():
                            result['personnel_types'].append('supervisors')
                            result['supervision_present'] = True
                        if 'uniform' in line.lower():
                            result['uniform_identification'] += line + ' '
                    elif current_section == 'activity':
                        result['activity_description'] += line + ' '
                        if 'construction' in line.lower():
                            result['activity_type'] = 'construction'
                        elif 'military' in line.lower() or 'training' in line.lower():
                            result['activity_type'] = 'military'
                        elif 'education' in line.lower() or 'classroom' in line.lower():
                            result['activity_type'] = 'educational'
                    elif current_section == 'concern':
                        if 'low' in line.lower():
                            result['concern_level'] = 'low'
                        elif 'medium' in line.lower():
                            result['concern_level'] = 'medium'
                        elif 'high' in line.lower():
                            result['concern_level'] = 'high'
                        elif 'critical' in line.lower():
                            result['concern_level'] = 'critical'
                        # Extract concern indicators
                        if 'guard' in line.lower() or 'restriction' in line.lower():
                            result['restriction_indicators'].append(line)
                        if any(word in line.lower() for word in ['concern', 'issue', 'problem']):
                            result['concern_indicators'].append(line)

            # Calculate confidence score based on detail level
            detail_score = len(result['scene_description']) / 100  # More detail = higher confidence
            result['confidence_score'] = min(0.95, max(0.3, detail_score))

            return result

        except Exception as e:
            print(f"   ✗ Error parsing analysis response: {e}")
            return {
                'error_message': str(e),
                'raw_analysis': response_text,
                'confidence_score': 0.0
            }

    def batch_analyze(self, image_paths: List[str]) -> List[Dict]:
        """
        Analyze multiple images in sequence

        Args:
            image_paths: List of image file paths

        Returns:
            List of analysis results
        """
        results = []
        total = len(image_paths)

        print(f"\n🔍 Analyzing {total} images with local LLM")
        print("=" * 50)

        for i, path in enumerate(image_paths, 1):
            print(f"\n[{i}/{total}] Analyzing: {Path(path).name}")
            analysis = self.analyze_image(path)
            if analysis:
                results.append(analysis)

            # Small delay between analyses to avoid overload
            if i < total:
                time.sleep(1)

        print(f"\n✓ Completed analysis of {len(results)}/{total} images")
        return results

    def test_connection(self) -> bool:
        """Test connection to Ollama server"""
        try:
            models = self.client.list()
            print(f"✓ Connected to Ollama at {self.host}")
            if 'models' in models:
                model_names = [m.get('name', 'unknown') for m in models.get('models', [])]
                print(f"  Available models: {model_names[:5]}")  # Show first 5
            return True
        except Exception as e:
            print(f"✗ Cannot connect to Ollama at {self.host}: {e}")
            print("  Please ensure Ollama is running: ollama serve")
            return False

    def ensure_model(self) -> bool:
        """Ensure the required model is available"""
        try:
            # Check if model exists
            models = self.client.list()
            if 'models' not in models:
                print("✗ Cannot get model list")
                return False

            model_names = [m.get('name', '') for m in models.get('models', [])]

            if self.model not in model_names and not any(self.model in name for name in model_names):
                print(f"⚠ Model {self.model} not found. Pulling it now...")
                self.client.pull(self.model)
                print(f"✓ Model {self.model} pulled successfully")
            else:
                print(f"✓ Model {self.model} is available")

            return True

        except Exception as e:
            print(f"✗ Error ensuring model: {e}")
            return False

    def generate_text_response(self, prompt: str) -> Optional[str]:
        """
        Generate text response using Ollama for text analysis

        Args:
            prompt: The text prompt to analyze

        Returns:
            Generated response text or None if failed
        """
        try:
            start_time = time.time()

            # Use chat API for text generation
            response = self.client.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                options={
                    'temperature': 0.1,
                    'num_predict': 2000
                }
            )

            processing_time = time.time() - start_time
            response_text = response.get('message', {}).get('content', '')

            if not response_text:
                print(f"   ✗ Empty response from {self.model}")
                return None

            print(f"   ✓ Generated {len(response_text)} chars in {processing_time:.1f}s")
            return response_text

        except Exception as e:
            print(f"   ✗ Error generating text response: {e}")
            return None