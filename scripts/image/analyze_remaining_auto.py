#!/usr/bin/env python3
"""Automatically analyze remaining unanalyzed images without user input"""

import sys
import time
from pathlib import Path
from datetime import datetime
from database.connection import get_session
from database.models import SearchResult, CapturedImage, ContentAnalysis
from utils.ollama_analyzer import OllamaAnalyzer

def analyze_remaining_auto(max_images=None):
    """Analyze remaining unanalyzed images automatically"""
    session = get_session()
    analyzer = OllamaAnalyzer()

    print("=" * 60)
    print("ANALYZING REMAINING IMAGES (AUTOMATIC)")
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

    # Limit if specified
    if max_images:
        unanalyzed = unanalyzed[:max_images]
        print(f"📌 Limiting to {max_images} images")

    # Start time
    start_time = time.time()
    est_time = (len(unanalyzed) * 25) / 60  # 25 seconds per image average
    print(f"⏱️  Estimated time: {est_time:.1f} minutes")
    print(f"🚀 Starting at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"\n{'='*60}\n")

    analyzed_count = 0
    high_concern_count = 0
    failed_count = 0

    for i, captured in enumerate(unanalyzed, 1):
        try:
            filename = Path(captured.file_path).name
            print(f"[{i}/{len(unanalyzed)}] Analyzing {filename[:50]}...", end="")
            sys.stdout.flush()

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

                concern = analysis.get('concern_level', 'unknown')
                print(f" ✓ ({concern})")

                analyzed_count += 1
                if concern in ['high', 'critical']:
                    high_concern_count += 1
            else:
                print(" ✗ Failed")
                failed_count += 1

            # Progress update every 10 images
            if i % 10 == 0:
                elapsed = (time.time() - start_time) / 60
                remaining = (elapsed / i) * (len(unanalyzed) - i)
                print(f"\n📊 Progress: {i}/{len(unanalyzed)} | "
                      f"Time: {elapsed:.1f}min | "
                      f"Remaining: {remaining:.1f}min\n")

        except Exception as e:
            print(f" ✗ Error: {str(e)[:50]}")
            failed_count += 1
            continue

    session.close()

    # Final summary
    elapsed_total = (time.time() - start_time) / 60

    print("\n" + "=" * 60)
    print("✅ ANALYSIS COMPLETED")
    print("=" * 60)
    print(f"⏱️  Total time: {elapsed_total:.1f} minutes")
    print(f"✓ Successfully analyzed: {analyzed_count}")
    print(f"⚠️  High/Critical concern: {high_concern_count}")
    print(f"✗ Failed: {failed_count}")
    print(f"🕐 Completed at: {datetime.now().strftime('%H:%M:%S')}")

    return analyzed_count

if __name__ == "__main__":
    if len(sys.argv) > 1:
        max_images = int(sys.argv[1])
        analyze_remaining_auto(max_images)
    else:
        analyze_remaining_auto()