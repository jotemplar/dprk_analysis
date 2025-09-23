#!/usr/bin/env python3
"""Ensemble combination logic for multi-model analysis"""

from typing import Dict, List, Optional

def combine_analyses(llava_result: Dict, gemma_result: Dict) -> Dict:
    """
    Combine two model outputs for higher confidence analysis

    Args:
        llava_result: Analysis from llava model
        gemma_result: Analysis from gemma model

    Returns:
        Combined analysis with ensemble confidence and concern level
    """
    # Map concern levels to numerical scores
    concern_map = {
        # Standard levels (llava)
        'low': 1,
        'medium': 2,
        'high': 3,
        'critical': 4,
        # Gemma-specific levels
        'minimal': 1,
        'moderate': 2,
        'severe': 3,
        'extreme': 4
    }

    # Get concern scores
    llava_score = concern_map.get(llava_result.get('concern_level', 'low'), 1)

    # Handle both Gemma field names
    gemma_concern = gemma_result.get('concern_level') or gemma_result.get('standard_concern_level', 'low')
    gemma_score = concern_map.get(gemma_concern, 1)

    # Calculate average score
    avg_score = (llava_score + gemma_score) / 2

    # Map back to concern level
    if avg_score >= 3.5:
        ensemble_level = 'critical'
    elif avg_score >= 2.5:
        ensemble_level = 'high'
    elif avg_score >= 1.5:
        ensemble_level = 'medium'
    else:
        ensemble_level = 'low'

    # Calculate confidence based on agreement
    # Higher confidence when models agree, lower when they disagree
    score_difference = abs(llava_score - gemma_score)
    confidence = 1.0 - (score_difference * 0.25)  # Max penalty of 0.75 for complete disagreement

    # Boost confidence if both models show high concern
    if llava_score >= 3 and gemma_score >= 3:
        confidence = min(1.0, confidence + 0.1)

    # Combine indicators from both models
    combined_indicators = set()

    # Add llava indicators
    if llava_result.get('concern_indicators'):
        combined_indicators.update(llava_result['concern_indicators'])
    if llava_result.get('restriction_indicators'):
        combined_indicators.update(llava_result['restriction_indicators'])

    # Add gemma indicators
    if gemma_result.get('exploitation_indicators'):
        combined_indicators.update(gemma_result['exploitation_indicators'])
    if gemma_result.get('control_indicators'):
        combined_indicators.update(gemma_result['control_indicators'])
    if gemma_result.get('welfare_concerns'):
        combined_indicators.update(gemma_result['welfare_concerns'])

    # Create consensus description
    consensus_description = create_consensus_description(llava_result, gemma_result)

    return {
        'ensemble_concern_level': ensemble_level,
        'ensemble_confidence': round(confidence, 2),
        'llava_score': llava_score,
        'gemma_score': gemma_score,
        'agreement_level': get_agreement_level(score_difference),
        'combined_indicators': list(combined_indicators)[:10],  # Limit to top 10
        'consensus_description': consensus_description
    }

def get_agreement_level(score_difference: float) -> str:
    """Categorize the level of agreement between models"""
    if score_difference == 0:
        return 'perfect'
    elif score_difference <= 1:
        return 'high'
    elif score_difference <= 2:
        return 'moderate'
    else:
        return 'low'

def create_consensus_description(llava_result: Dict, gemma_result: Dict) -> str:
    """Create a consensus description from both model outputs"""
    descriptions = []

    # Get concern levels
    llava_concern = llava_result.get('concern_level', 'unknown')
    gemma_concern = gemma_result.get('concern_level') or gemma_result.get('standard_concern_level', 'unknown')

    # Start with agreement statement
    if llava_concern == gemma_concern:
        descriptions.append(f"Both models agree on {llava_concern} concern level.")
    else:
        descriptions.append(f"Models show {llava_concern} (llava) and {gemma_concern} (gemma) concern levels.")

    # Add key findings from llava
    if llava_result.get('scene_description'):
        descriptions.append(f"Visual analysis: {llava_result['scene_description'][:200]}")

    # Add key findings from gemma
    if gemma_result.get('scene_description'):
        descriptions.append(f"Humanitarian perspective: {gemma_result['scene_description'][:200]}")

    # Add personnel count if available
    if llava_result.get('personnel_count', 0) > 0:
        descriptions.append(f"Personnel count: {llava_result['personnel_count']}")

    # Add supervision status
    if llava_result.get('supervision_present'):
        descriptions.append("Supervision/control present")

    return ' '.join(descriptions)

def calculate_priority_score(ensemble_result: Dict, llava_result: Dict, gemma_result: Dict) -> float:
    """
    Calculate a priority score for further investigation

    Higher scores indicate images that need more attention
    """
    score = 0.0

    # Base score from concern level
    concern_scores = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
    score += concern_scores.get(ensemble_result['ensemble_concern_level'], 0) * 2

    # Boost for high confidence
    score += ensemble_result['ensemble_confidence'] * 2

    # Boost for multiple indicators
    indicator_count = len(ensemble_result.get('combined_indicators', []))
    score += min(indicator_count * 0.5, 3)  # Cap at 3 points

    # Boost for personnel presence
    if llava_result.get('personnel_count', 0) > 5:
        score += 1
    if llava_result.get('personnel_count', 0) > 10:
        score += 1

    # Boost for supervision/restriction
    if llava_result.get('supervision_present'):
        score += 1

    return round(score, 2)

def should_flag_for_review(ensemble_result: Dict) -> bool:
    """Determine if an image should be flagged for human review"""
    # Flag if high/critical concern with high confidence
    if ensemble_result['ensemble_concern_level'] in ['high', 'critical'] and \
       ensemble_result['ensemble_confidence'] >= 0.75:
        return True

    # Flag if models strongly disagree on high-stakes classification
    if ensemble_result['agreement_level'] == 'low' and \
       (ensemble_result['llava_score'] >= 3 or ensemble_result['gemma_score'] >= 3):
        return True

    # Flag if many concerning indicators
    if len(ensemble_result.get('combined_indicators', [])) >= 5:
        return True

    return False