#!/usr/bin/env python3
"""Analyze remaining unanalyzed images"""

import sys
from pathlib import Path
from database.connection import get_session
from database.models import SearchResult, CapturedImage, ContentAnalysis
from utils.ollama_analyzer import OllamaAnalyzer

def analyze_remaining(batch_size=50):
    """Analyze remaining unanalyzed images"""
    session = get_session()
    analyzer = OllamaAnalyzer()

    print("=" * 60)
    print("ANALYZING REMAINING IMAGES")
    print("=" * 60)

    # Get unanalyzed images
    unanalyzed = session.query(CapturedImage).join(
        SearchResult
    ).filter(
        SearchResult.analysis_status == 'pending'
    ).all()

    total = len(unanalyzed)
    print(f"\n📊 Found {total} unanalyzed images")

    if total == 0:
        print("✅ All images already analyzed!")
        return

    # Estimate time
    est_time = (total * 25) / 60  # 25 seconds per image average
    print(f"⏱️  Estimated time: {est_time:.1f} minutes")

    response = input(f"\nAnalyze all {total} images? (y/n/number): ").strip().lower()

    if response == 'n':
        print("Cancelled")
        return
    elif response.isdigit():
        batch_size = int(response)
        print(f"Will analyze {batch_size} images")
        unanalyzed = unanalyzed[:batch_size]
    elif response != 'y':
        print("Invalid response, cancelled")
        return

    print(f"\n🔍 Starting analysis of {len(unanalyzed)} images...")

    for i, captured in enumerate(unanalyzed, 1):
        print(f"\n[{i}/{len(unanalyzed)}] Analyzing {Path(captured.file_path).name}")

        # Analyze image
        analysis = analyzer.analyze_image(captured.file_path)

        if analysis and 'error_message' not in analysis:
            # Check if analysis already exists
            existing = session.query(ContentAnalysis).filter_by(
                result_id=captured.result_id
            ).first()

            if not existing:
                content_analysis = ContentAnalysis(
                    result_id=captured.result_id,
                    scene_description=analysis.get('scene_description', ''),
                    location_assessment=analysis.get('location_assessment', ''),
                    environment_type=analysis.get('environment_type', 'unknown'),
                    personnel_count=analysis.get('personnel_count', 0),
                    personnel_types=analysis.get('personnel_types', []),
                    uniform_identification=analysis.get('uniform_identification', ''),
                    activity_type=analysis.get('activity_type', 'unknown'),
                    activity_description=analysis.get('activity_description', ''),
                    concern_level=analysis.get('concern_level', 'low'),
                    concern_indicators=analysis.get('concern_indicators', []),
                    supervision_present=analysis.get('supervision_present', False),
                    restriction_indicators=analysis.get('restriction_indicators', []),
                    analysis_model=analysis.get('analysis_model', ''),
                    confidence_score=analysis.get('confidence_score', 0.0),
                    processing_time=analysis.get('processing_time', 0.0)
                )
                session.add(content_analysis)

            # Update search result status
            search_result = session.query(SearchResult).filter_by(
                id=captured.result_id
            ).first()
            if search_result:
                search_result.analysis_status = 'completed'

            session.commit()
            print(f"   ✓ Analysis saved - Concern: {analysis.get('concern_level', 'unknown')}")
        else:
            print(f"   ✗ Analysis failed")

    session.close()

    print("\n" + "=" * 60)
    print("✅ ANALYSIS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        batch_size = int(sys.argv[1])
        analyze_remaining(batch_size)
    else:
        analyze_remaining()