#!/usr/bin/env python3
"""Gemma model analyzer for second-pass humanitarian analysis"""

from typing import Dict, Optional
import time
from .ollama_analyzer import OllamaAnalyzer

class GemmaAnalyzer(OllamaAnalyzer):
    """Specialized analyzer using Gemma model for humanitarian perspective"""

    def __init__(self):
        """Initialize with Gemma model"""
        super().__init__(model="gemma3n:e4b")
        print(f"✨ Initialized GemmaAnalyzer with model: {self.model}")

    def _create_analysis_prompt(self) -> str:
        """Create Gemma-specific prompt with different perspective for ensemble diversity"""
        return """Analyze this image from a humanitarian and human rights perspective. Focus on identifying evidence of concerning conditions.

DETAILED ANALYSIS REQUIRED:

1. EXPLOITATION INDICATORS:
   Describe any visible evidence of:
   - Workers without proper safety equipment in hazardous conditions
   - Overcrowded or substandard living/working spaces
   - People working in extreme weather without adequate protection
   - Signs of exhaustion, malnutrition, or physical distress
   - Dangerous working conditions or safety violations

2. CONTROL & RESTRICTION:
   Look for and describe:
   - Guards, supervisors, or handlers watching workers
   - Fenced or walled compounds suggesting restricted movement
   - Group formations indicating controlled movement
   - Surveillance equipment or watchtowers
   - Isolated locations away from populated areas
   - Uniform clothing suggesting institutional control

3. LIVING STANDARD ASSESSMENT:
   Evaluate and describe:
   - Quality of visible housing or dormitories
   - Crowding levels if multiple people are visible
   - Condition of buildings (deteriorated, temporary, makeshift)
   - Presence or absence of basic amenities
   - Personal space and privacy indicators
   - Sanitation and hygiene conditions if observable

4. PHYSICAL WELFARE:
   Note any evidence of:
   - Thin or malnourished appearance
   - Inadequate clothing for conditions
   - Injuries or untreated medical conditions
   - Physical exhaustion or strain
   - Working without rest or breaks
   - Exposure to health hazards

5. SEVERITY RATING:
   Based on your observations, rate the humanitarian concern level:
   - EXTREME: Life-threatening conditions, severe exploitation evident
   - SEVERE: Multiple serious concerns, systematic mistreatment indicators
   - MODERATE: Some concerning conditions, substandard treatment
   - MINIMAL: Few concerns, mostly acceptable conditions

Provide specific visual evidence for each observation.
Focus on factual description of what is visible in the image.
Be detailed about any concerning conditions you observe."""

    def _parse_analysis_response(self, response_text: str) -> Dict:
        """Parse Gemma model response with focus on humanitarian indicators"""
        try:
            # Initialize result dictionary with Gemma-specific fields
            result = {
                'scene_description': '',
                'exploitation_indicators': [],
                'control_indicators': [],
                'living_conditions': '',
                'welfare_concerns': [],
                'concern_level': 'minimal',
                'confidence_score': 0.0,
                'raw_analysis': response_text
            }

            # Parse response text
            lines = response_text.split('\n')
            current_section = None
            current_content = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Detect sections
                if 'EXPLOITATION' in line.upper():
                    current_section = 'exploitation'
                    current_content = []
                elif 'CONTROL' in line.upper() or 'RESTRICTION' in line.upper():
                    current_section = 'control'
                    current_content = []
                elif 'LIVING' in line.upper() and 'STANDARD' in line.upper():
                    current_section = 'living'
                    current_content = []
                elif 'WELFARE' in line.upper():
                    current_section = 'welfare'
                    current_content = []
                elif 'SEVERITY' in line.upper() or 'RATING' in line.upper():
                    current_section = 'severity'
                    current_content = []
                elif current_section and not line.startswith(('1.', '2.', '3.', '4.', '5.')):
                    # Add content to current section
                    if line.startswith('-'):
                        current_content.append(line[1:].strip())
                    else:
                        current_content.append(line)

                    # Process based on section
                    if current_section == 'exploitation':
                        result['exploitation_indicators'] = current_content
                    elif current_section == 'control':
                        result['control_indicators'] = current_content
                    elif current_section == 'living':
                        result['living_conditions'] = ' '.join(current_content)
                    elif current_section == 'welfare':
                        result['welfare_concerns'] = current_content
                    elif current_section == 'severity':
                        severity_text = ' '.join(current_content).lower()
                        if 'extreme' in severity_text:
                            result['concern_level'] = 'extreme'
                            result['confidence_score'] = 0.95
                        elif 'severe' in severity_text:
                            result['concern_level'] = 'severe'
                            result['confidence_score'] = 0.85
                        elif 'moderate' in severity_text:
                            result['concern_level'] = 'moderate'
                            result['confidence_score'] = 0.75
                        else:
                            result['concern_level'] = 'minimal'
                            result['confidence_score'] = 0.65

            # Create scene description from collected indicators
            if result['exploitation_indicators'] or result['control_indicators']:
                descriptions = []
                if result['exploitation_indicators']:
                    descriptions.append(f"Exploitation concerns: {', '.join(result['exploitation_indicators'][:3])}")
                if result['control_indicators']:
                    descriptions.append(f"Control indicators: {', '.join(result['control_indicators'][:3])}")
                if result['welfare_concerns']:
                    descriptions.append(f"Welfare issues: {', '.join(result['welfare_concerns'][:3])}")
                result['scene_description'] = '. '.join(descriptions)

            # Map Gemma concern levels to standard levels for compatibility
            concern_map = {
                'extreme': 'critical',
                'severe': 'high',
                'moderate': 'medium',
                'minimal': 'low'
            }
            result['standard_concern_level'] = concern_map.get(result['concern_level'], 'low')

            return result

        except Exception as e:
            print(f"   ⚠️  Error parsing Gemma response: {e}")
            # Return basic result on parse error
            return {
                'scene_description': response_text[:500] if response_text else '',
                'concern_level': 'low',
                'exploitation_indicators': [],
                'control_indicators': [],
                'welfare_concerns': [],
                'confidence_score': 0.5,
                'raw_analysis': response_text
            }

    def analyze_image(self, image_path: str) -> Optional[Dict]:
        """Analyze image with Gemma model for humanitarian perspective"""
        print(f"   🔍 Analyzing with Gemma model: {image_path}")
        result = super().analyze_image(image_path)

        if result:
            # Add Gemma-specific metadata
            result['analysis_model'] = 'gemma3n:e4b'
            result['analysis_type'] = 'humanitarian_perspective'

        return result