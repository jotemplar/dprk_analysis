"""Ollama analyzer with structured outputs using Pydantic validation"""

import os
import json
import base64
import time
from pathlib import Path
from typing import Dict, Optional, List
import ollama
from dotenv import load_dotenv
from utils.analysis_models import ImageAnalysisResult, create_json_prompt

load_dotenv()


class StructuredOllamaAnalyzer:
    """Analyze images using Ollama with structured JSON outputs"""

    def __init__(self, model=None):
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        if model:
            self.model = model
        else:
            self.model = os.getenv("OLLAMA_MODEL", "llava")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", 300))
        self.client = ollama.Client(host=self.host)
        self.max_retries = 3

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 for analysis"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def analyze_image(self, image_path: str) -> Optional[Dict]:
        """
        Analyze image with structured output and validation

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with validated analysis results
        """
        try:
            # Check if file exists
            if not Path(image_path).exists():
                print(f"   ✗ Image file not found: {image_path}")
                return None

            # Encode image
            image_base64 = self.encode_image(image_path)

            # Try to get structured response with retries
            for attempt in range(self.max_retries):
                try:
                    # Start timing
                    start_time = time.time()

                    # Create JSON prompt
                    prompt = create_json_prompt()

                    # Send to Ollama
                    response = self.client.generate(
                        model=self.model,
                        prompt=prompt,
                        images=[image_base64],
                        options={
                            "temperature": 0.2,  # Lower for more consistent JSON
                            "num_predict": 2000,
                            "top_p": 0.9
                        }
                    )

                    # Calculate processing time
                    processing_time = time.time() - start_time

                    # Parse and validate response
                    result = self._parse_json_response(response['response'])

                    if result:
                        # Add metadata
                        result['processing_time'] = processing_time
                        result['analysis_model'] = self.model

                        print(f"   ✓ Image analyzed in {processing_time:.1f}s (structured)")
                        return result

                except json.JSONDecodeError as e:
                    print(f"   ⚠️ Attempt {attempt + 1}: JSON parse error: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(1)  # Brief pause before retry
                    continue

            # If all attempts failed, try fallback parsing
            print("   ⚠️ Falling back to text parsing")
            return self._fallback_text_parsing(response.get('response', ''))

        except Exception as e:
            print(f"   ✗ Error analyzing image: {e}")
            return None

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """Parse and validate JSON response using Pydantic"""
        try:
            # Try to extract JSON from response
            json_str = self._extract_json(response_text)

            # Parse JSON
            json_data = json.loads(json_str)

            # Validate with Pydantic
            analysis = ImageAnalysisResult(**json_data)

            # Convert to dict for database storage
            return analysis.dict()

        except (json.JSONDecodeError, ValueError) as e:
            # Try to find and fix common JSON issues
            fixed_json = self._fix_json_issues(response_text)
            if fixed_json:
                try:
                    json_data = json.loads(fixed_json)
                    analysis = ImageAnalysisResult(**json_data)
                    return analysis.dict()
                except:
                    pass
            raise e

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text"""
        # Remove any markdown code blocks
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]

        # Find JSON boundaries
        start = text.find('{')
        end = text.rfind('}') + 1

        if start >= 0 and end > start:
            return text[start:end]

        return text

    def _fix_json_issues(self, text: str) -> Optional[str]:
        """Attempt to fix common JSON formatting issues"""
        try:
            # Extract potential JSON
            text = self._extract_json(text)

            # Fix common issues
            # Replace single quotes with double quotes
            text = text.replace("'", '"')

            # Fix boolean values
            text = text.replace('True', 'true').replace('False', 'false')
            text = text.replace('None', 'null')

            # Try to add missing commas
            import re
            # Add comma after } if followed by "
            text = re.sub(r'}\s*"', '},"', text)
            # Add comma after ] if followed by "
            text = re.sub(r']\s*"', '],"', text)
            # Add comma after number/boolean if followed by "
            text = re.sub(r'(\d|true|false|null)\s*"', r'\1,"', text)

            return text
        except:
            return None

    def _fallback_text_parsing(self, response_text: str) -> Dict:
        """Fallback to basic text parsing if JSON fails"""
        # Create a minimal valid result
        result = ImageAnalysisResult()

        # Try to extract key information
        lines = response_text.lower()

        # Extract concern level
        if 'critical' in lines:
            result.concern_level = 'critical'
        elif 'high' in lines:
            result.concern_level = 'high'
        elif 'medium' in lines:
            result.concern_level = 'medium'
        else:
            result.concern_level = 'low'

        # Extract basic description (first 500 chars)
        result.scene_description = response_text[:500].strip()

        # Look for personnel count
        import re
        numbers = re.findall(r'\b(\d+)\s*(?:people|persons?|workers?|men|women)\b', lines)
        if numbers:
            result.personnel_count = int(numbers[0])

        # Check for supervision
        if any(word in lines for word in ['guard', 'supervisor', 'overseer', 'monitor']):
            result.supervision_present = True

        # Set low confidence for fallback parsing
        result.confidence_score = 0.3

        return result.dict()

    def batch_analyze(self, image_paths: List[str]) -> List[Dict]:
        """Analyze multiple images with structured outputs"""
        results = []
        total = len(image_paths)

        print(f"\n🔍 Analyzing {total} images with structured outputs")
        print("=" * 50)

        for i, path in enumerate(image_paths, 1):
            print(f"\n[{i}/{total}] Analyzing: {Path(path).name}")
            analysis = self.analyze_image(path)
            if analysis:
                results.append(analysis)

            # Small delay between analyses
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
                print(f"  Available models: {model_names[:5]}")
            return True
        except Exception as e:
            print(f"✗ Cannot connect to Ollama at {self.host}: {e}")
            return False

    def ensure_model(self) -> bool:
        """Ensure the required model is available"""
        try:
            models = self.client.list()
            if 'models' not in models:
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