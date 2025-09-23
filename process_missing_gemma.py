#!/usr/bin/env python3
"""Process images from first run that are missing second pass (Gemma) analysis"""

import sys
import time
from pathlib import Path
from datetime import datetime
from database.connection import get_session
from database.models import ContentAnalysis, CapturedImage, SearchResult
from utils.gemma_analyzer import GemmaAnalyzer
from utils.ensemble import combine_analyses, calculate_priority_score, should_flag_for_review
from sqlalchemy import text

def process_missing_gemma_analysis(limit=None, only_high_concern=False):
    """
    Find and process images without Gemma analysis

    Args:
        limit: Maximum number of images to process
        only_high_concern: Only process images with high/critical llava concern levels
    """
    session = get_session()
    analyzer = GemmaAnalyzer()

    print("=" * 60)
    print("PROCESSING MISSING GEMMA ANALYSES")
    print("=" * 60)

    try:
        # Test Gemma connection first
        print("\n🔧 Testing Gemma model connection...")
        if not analyzer.test_connection():
            print("❌ Gemma model not available. Please ensure ollama is running with gemma3n:e4b")
            return
        print("✅ Gemma model ready")

        # Query for images with llava analysis but no gemma analysis
        query = session.query(ContentAnalysis)

        # Filter for missing gemma analysis
        query = query.filter(ContentAnalysis.gemma_description.is_(None))

        # Optionally filter for high concern only
        if only_high_concern:
            query = query.filter(ContentAnalysis.concern_level.in_(['high', 'critical']))
            print("📌 Filtering for high/critical concern images only")

        missing_gemma = query.all()
        total_missing = len(missing_gemma)

        if limit and limit < total_missing:
            missing_gemma = missing_gemma[:limit]
            print(f"\n📊 Found {total_missing} images missing Gemma analysis")
            print(f"📌 Processing limited to {limit} images")
        else:
            print(f"\n📊 Found {total_missing} images needing Gemma analysis")

        if total_missing == 0:
            print("✅ All images already have Gemma analysis!")
            return

        # Statistics tracking
        processed_count = 0
        high_concern_count = 0
        flagged_for_review = 0
        failed_count = 0
        start_time = time.time()

        print(f"🚀 Starting processing at {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)

        for i, analysis in enumerate(missing_gemma, 1):
            try:
                # Get image path
                captured = session.query(CapturedImage).filter_by(
                    result_id=analysis.result_id
                ).first()

                if not captured or not captured.file_path:
                    print(f"[{i}/{len(missing_gemma)}] ⚠️  No image file found for result_id: {analysis.result_id}")
                    continue

                # Get search result for context
                result = session.query(SearchResult).filter_by(
                    id=analysis.result_id
                ).first()

                filename = Path(captured.file_path).name
                print(f"\n[{i}/{len(missing_gemma)}] Processing {filename[:50]}...")
                print(f"   Original concern: {analysis.concern_level}")

                # Run Gemma analysis
                gemma_result = analyzer.analyze_image(captured.file_path)

                if gemma_result and 'error_message' not in gemma_result:
                    # Update database with Gemma results
                    analysis.gemma_description = gemma_result.get('scene_description', '')

                    # Handle both possible field names for concern level
                    gemma_concern = gemma_result.get('standard_concern_level') or gemma_result.get('concern_level', 'low')
                    analysis.gemma_concern_level = gemma_concern

                    # Store indicators
                    gemma_indicators = []
                    if gemma_result.get('exploitation_indicators'):
                        gemma_indicators.extend(gemma_result['exploitation_indicators'])
                    if gemma_result.get('control_indicators'):
                        gemma_indicators.extend(gemma_result['control_indicators'])
                    if gemma_result.get('welfare_concerns'):
                        gemma_indicators.extend(gemma_result['welfare_concerns'])
                    analysis.gemma_indicators = gemma_indicators[:10]  # Limit to 10

                    analysis.gemma_processing_time = gemma_result.get('processing_time', 0)

                    # Calculate ensemble results
                    llava_result = {
                        'concern_level': analysis.concern_level,
                        'concern_indicators': analysis.concern_indicators or [],
                        'restriction_indicators': analysis.restriction_indicators or [],
                        'scene_description': analysis.scene_description,
                        'personnel_count': analysis.personnel_count,
                        'supervision_present': analysis.supervision_present
                    }

                    combined = combine_analyses(llava_result, gemma_result)

                    analysis.ensemble_concern_level = combined['ensemble_concern_level']
                    analysis.ensemble_confidence = combined['ensemble_confidence']

                    # Calculate priority score
                    priority = calculate_priority_score(combined, llava_result, gemma_result)

                    # Check if should flag for review
                    if should_flag_for_review(combined):
                        flagged_for_review += 1
                        flag_marker = "🚩"
                    else:
                        flag_marker = "  "

                    session.commit()

                    print(f"   ✓ Gemma analysis: {gemma_concern}")
                    print(f"   ✓ Ensemble: {combined['ensemble_concern_level']} (confidence: {combined['ensemble_confidence']})")
                    print(f"   {flag_marker} Agreement: {combined['agreement_level']} | Priority: {priority}")

                    processed_count += 1

                    # Track high concern
                    if combined['ensemble_concern_level'] in ['high', 'critical']:
                        high_concern_count += 1
                        if result:
                            print(f"   📍 Source: {result.source_domain}")

                    # Progress update every 10 images
                    if i % 10 == 0:
                        elapsed = (time.time() - start_time) / 60
                        rate = processed_count / elapsed if elapsed > 0 else 0
                        eta = ((len(missing_gemma) - i) / rate) if rate > 0 else 0
                        print(f"\n📊 Progress: {i}/{len(missing_gemma)} | "
                              f"Elapsed: {elapsed:.1f}min | "
                              f"Rate: {rate:.1f}/min | "
                              f"ETA: {eta:.1f}min")

                else:
                    print(f"   ✗ Gemma analysis failed")
                    failed_count += 1

            except Exception as e:
                print(f"   ✗ Error processing: {e}")
                failed_count += 1
                session.rollback()
                continue

        # Final summary
        elapsed_total = (time.time() - start_time) / 60

        print("\n" + "=" * 60)
        print("✅ GEMMA PROCESSING COMPLETED")
        print("=" * 60)
        print(f"⏱️  Total time: {elapsed_total:.1f} minutes")
        print(f"✓ Successfully processed: {processed_count}/{len(missing_gemma)}")
        print(f"⚠️  High/Critical ensemble: {high_concern_count}")
        print(f"🚩 Flagged for review: {flagged_for_review}")
        print(f"✗ Failed: {failed_count}")
        print(f"🕐 Completed at: {datetime.now().strftime('%H:%M:%S')}")

        # Query for overall statistics
        total_with_ensemble = session.query(ContentAnalysis).filter(
            ContentAnalysis.ensemble_concern_level.isnot(None)
        ).count()

        print(f"\n📈 Database Statistics:")
        print(f"   Total with ensemble analysis: {total_with_ensemble}")

        # Show distribution of ensemble concern levels
        concern_dist = session.execute(text("""
            SELECT ensemble_concern_level, COUNT(*) as count
            FROM content_analysis
            WHERE ensemble_concern_level IS NOT NULL
            GROUP BY ensemble_concern_level
            ORDER BY count DESC
        """)).fetchall()

        if concern_dist:
            print(f"\n📊 Ensemble Concern Distribution:")
            for level, count in concern_dist:
                print(f"   {level}: {count}")

    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()

    finally:
        session.close()

def main():
    """Main entry point with argument parsing"""
    import argparse

    parser = argparse.ArgumentParser(description='Process images missing Gemma analysis')
    parser.add_argument('--limit', type=int, help='Limit number of images to process')
    parser.add_argument('--high-only', action='store_true',
                        help='Only process images with high/critical llava concern')
    parser.add_argument('--test', action='store_true',
                        help='Test mode - process only 5 images')

    args = parser.parse_args()

    if args.test:
        print("🧪 TEST MODE - Processing 5 images only")
        process_missing_gemma_analysis(limit=5, only_high_concern=args.high_only)
    else:
        process_missing_gemma_analysis(limit=args.limit, only_high_concern=args.high_only)

if __name__ == "__main__":
    main()