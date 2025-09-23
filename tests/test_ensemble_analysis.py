#!/usr/bin/env python3
"""Test suite for ensemble analysis system"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.ollama_analyzer import OllamaAnalyzer
from utils.gemma_analyzer import GemmaAnalyzer
from utils.ensemble import (
    combine_analyses,
    get_agreement_level,
    create_consensus_description,
    calculate_priority_score,
    should_flag_for_review
)

class TestModelConnectivity:
    """Test model availability and connectivity"""

    def test_ollama_connection(self):
        """Test Ollama server connectivity"""
        analyzer = OllamaAnalyzer()
        assert analyzer.test_connection() == True, "Ollama server not available"

    def test_gemma_model_available(self):
        """Test Gemma model availability"""
        analyzer = GemmaAnalyzer()
        # Check model name is correct
        assert analyzer.model == "gemma3n:e4b"
        # Test connection
        assert analyzer.test_connection() == True, "Gemma model not available"

class TestEnsembleLogic:
    """Test ensemble combination logic"""

    def test_concern_level_averaging(self):
        """Test concern level averaging logic"""
        # Test perfect agreement
        llava_result = {'concern_level': 'high'}
        gemma_result = {'concern_level': 'severe'}  # Maps to 'high'
        combined = combine_analyses(llava_result, gemma_result)
        assert combined['ensemble_concern_level'] == 'high'
        assert combined['llava_score'] == 3
        assert combined['gemma_score'] == 3

    def test_concern_level_disagreement(self):
        """Test handling of disagreement between models"""
        llava_result = {'concern_level': 'low'}
        gemma_result = {'concern_level': 'extreme'}  # Maps to 'critical'
        combined = combine_analyses(llava_result, gemma_result)
        # Average of 1 and 4 = 2.5, which maps to 'high'
        assert combined['ensemble_concern_level'] == 'high'
        assert combined['agreement_level'] == 'low'

    def test_confidence_calculation(self):
        """Test confidence score based on agreement"""
        # Perfect agreement should give high confidence
        llava_result = {'concern_level': 'high'}
        gemma_result = {'concern_level': 'severe'}
        combined = combine_analyses(llava_result, gemma_result)
        assert combined['ensemble_confidence'] >= 0.9  # High confidence for agreement

        # Strong disagreement should give low confidence
        llava_result = {'concern_level': 'low'}
        gemma_result = {'concern_level': 'extreme'}
        combined = combine_analyses(llava_result, gemma_result)
        assert combined['ensemble_confidence'] <= 0.5  # Low confidence for disagreement

    def test_indicator_combination(self):
        """Test combining indicators from both models"""
        llava_result = {
            'concern_level': 'medium',
            'concern_indicators': ['no helmets', 'working at height'],
            'restriction_indicators': ['guards present']
        }
        gemma_result = {
            'concern_level': 'moderate',
            'exploitation_indicators': ['overcrowded', 'poor conditions'],
            'control_indicators': ['fenced compound']
        }
        combined = combine_analyses(llava_result, gemma_result)

        # Check all indicators are included
        assert 'no helmets' in combined['combined_indicators']
        assert 'guards present' in combined['combined_indicators']
        assert 'overcrowded' in combined['combined_indicators']
        assert 'fenced compound' in combined['combined_indicators']

    def test_agreement_level_classification(self):
        """Test agreement level classification"""
        assert get_agreement_level(0) == 'perfect'
        assert get_agreement_level(0.5) == 'high'
        assert get_agreement_level(1.5) == 'moderate'
        assert get_agreement_level(3) == 'low'

class TestPromptOptimization:
    """Test that prompts contain key humanitarian indicators"""

    def test_llava_prompt_indicators(self):
        """Test llava prompt contains required indicators"""
        analyzer = OllamaAnalyzer()
        prompt = analyzer._create_analysis_prompt()

        # Check for key humanitarian indicators
        assert 'safety equipment' in prompt.lower()
        assert 'overcrowded' in prompt.lower() or 'crowded' in prompt.lower()
        assert 'supervision' in prompt.lower()
        assert 'health' in prompt.lower()
        assert 'exploitation' in prompt.lower() or 'concern' in prompt.lower()

    def test_gemma_prompt_indicators(self):
        """Test gemma prompt contains humanitarian perspective"""
        analyzer = GemmaAnalyzer()
        prompt = analyzer._create_analysis_prompt()

        # Check for humanitarian focus
        assert 'humanitarian' in prompt.lower()
        assert 'exploitation' in prompt.lower()
        assert 'control' in prompt.lower()
        assert 'welfare' in prompt.lower()
        assert 'severity' in prompt.lower()

class TestPriorityScoring:
    """Test priority scoring for review flagging"""

    def test_high_priority_scoring(self):
        """Test that critical concerns get high priority"""
        ensemble_result = {
            'ensemble_concern_level': 'critical',
            'ensemble_confidence': 0.9,
            'combined_indicators': ['no safety', 'guards', 'overcrowded', 'injuries', 'forced labor']
        }
        llava_result = {'personnel_count': 15, 'supervision_present': True}
        gemma_result = {}

        score = calculate_priority_score(ensemble_result, llava_result, gemma_result)
        assert score > 10  # High score for critical concern

    def test_review_flagging(self):
        """Test images are correctly flagged for review"""
        # Should flag high concern with high confidence
        ensemble_result = {
            'ensemble_concern_level': 'high',
            'ensemble_confidence': 0.8,
            'agreement_level': 'high',
            'llava_score': 3,
            'gemma_score': 3,
            'combined_indicators': []
        }
        assert should_flag_for_review(ensemble_result) == True

        # Should not flag low concern with high confidence
        ensemble_result = {
            'ensemble_concern_level': 'low',
            'ensemble_confidence': 0.9,
            'agreement_level': 'perfect',
            'llava_score': 1,
            'gemma_score': 1,
            'combined_indicators': []
        }
        assert should_flag_for_review(ensemble_result) == False

        # Should flag disagreement on high stakes
        ensemble_result = {
            'ensemble_concern_level': 'medium',
            'ensemble_confidence': 0.5,
            'agreement_level': 'low',
            'llava_score': 4,
            'gemma_score': 1,
            'combined_indicators': []
        }
        assert should_flag_for_review(ensemble_result) == True

class TestConsensusDescription:
    """Test consensus description generation"""

    def test_consensus_with_agreement(self):
        """Test consensus description when models agree"""
        llava_result = {
            'concern_level': 'high',
            'scene_description': 'Workers without safety equipment',
            'personnel_count': 10,
            'supervision_present': True
        }
        gemma_result = {
            'concern_level': 'severe',
            'standard_concern_level': 'high',
            'scene_description': 'Dangerous working conditions observed'
        }

        description = create_consensus_description(llava_result, gemma_result)
        assert 'Workers without safety' in description
        assert 'Personnel count: 10' in description
        assert 'Supervision/control present' in description

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, '-v'])