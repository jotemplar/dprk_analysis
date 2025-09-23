#!/usr/bin/env python3
"""Apply ensemble analysis combining llava and gemma3:12b results"""

import argparse
from datetime import datetime
from database.connection import get_session
from database.models import ContentAnalysis
from sqlalchemy import text


class EnsembleAnalyzer:
    """Combine multiple model analyses into ensemble results"""

    def __init__(self):
        self.concern_scores = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }

    def combine_concern_levels(self, llava_concern: str, gemma_concern: str) -> tuple:
        """
        Combine concern levels from two models
        Returns: (ensemble_level, confidence)
        """
        llava_score = self.concern_scores.get(llava_concern, 1)
        gemma_score = self.concern_scores.get(gemma_concern, 1)

        # Calculate average and determine ensemble level
        avg_score = (llava_score + gemma_score) / 2

        # Determine ensemble concern level
        if avg_score >= 3.5:
            ensemble_level = 'critical'
        elif avg_score >= 2.5:
            ensemble_level = 'high'
        elif avg_score >= 1.5:
            ensemble_level = 'medium'
        else:
            ensemble_level = 'low'

        # Calculate confidence based on agreement
        score_difference = abs(llava_score - gemma_score)
        if score_difference == 0:
            confidence = 1.0  # Perfect agreement
        elif score_difference == 1:
            confidence = 0.75  # Close agreement
        elif score_difference == 2:
            confidence = 0.5  # Moderate disagreement
        else:
            confidence = 0.25  # Strong disagreement

        # Boost confidence for high concern cases
        if ensemble_level in ['high', 'critical']:
            confidence = min(1.0, confidence + 0.1)

        return ensemble_level, confidence

    def combine_indicators(self, llava_indicators: list, gemma_indicators: list) -> list:
        """Combine and deduplicate indicators from both models"""
        all_indicators = []

        # Add all indicators, avoiding duplicates
        if llava_indicators:
            all_indicators.extend(llava_indicators)

        if gemma_indicators:
            for indicator in gemma_indicators:
                # Check for similar indicators (simple similarity check)
                is_duplicate = False
                for existing in all_indicators:
                    if indicator.lower() in existing.lower() or existing.lower() in indicator.lower():
                        is_duplicate = True
                        break
                if not is_duplicate:
                    all_indicators.append(indicator)

        # Limit to most important indicators
        return all_indicators[:15]

    def process_ensemble_analysis(self, session, limit=None, force_update=False):
        """Apply ensemble analysis to all images with both analyses"""

        print("="*60)
        print("ENSEMBLE ANALYSIS - Combining llava + gemma3:12b")
        print("="*60)

        # Find images with both analyses
        if force_update:
            # Process all with both analyses
            query = session.execute(text("""
                SELECT id, result_id, concern_level, concern_indicators, restriction_indicators,
                       gemma_concern_level, gemma_indicators
                FROM content_analysis
                WHERE concern_level IS NOT NULL
                AND gemma_concern_level IS NOT NULL
                ORDER BY result_id
            """))
        else:
            # Only process those without ensemble analysis
            query = session.execute(text("""
                SELECT id, result_id, concern_level, concern_indicators, restriction_indicators,
                       gemma_concern_level, gemma_indicators
                FROM content_analysis
                WHERE concern_level IS NOT NULL
                AND gemma_concern_level IS NOT NULL
                AND ensemble_concern_level IS NULL
                ORDER BY result_id
            """))

        records = query.fetchall()
        total_records = len(records)

        if limit and limit < total_records:
            records = records[:limit]
            print(f"📊 Found {total_records} images with both analyses")
            print(f"📌 Processing limited to {limit} images")
        else:
            print(f"📊 Processing {total_records} images for ensemble analysis")

        if total_records == 0:
            print("✅ No images to process!")
            return

        # Process each record
        processed_count = 0
        concern_distribution = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        high_confidence_count = 0

        print("\nApplying ensemble analysis...")
        print("-" * 60)

        for record in records:
            # Combine concern levels
            ensemble_level, confidence = self.combine_concern_levels(
                record.concern_level,
                record.gemma_concern_level
            )

            # Combine indicators
            llava_indicators = []
            if record.concern_indicators:
                llava_indicators.extend(record.concern_indicators)
            if record.restriction_indicators:
                llava_indicators.extend(record.restriction_indicators)

            ensemble_indicators = self.combine_indicators(
                llava_indicators,
                record.gemma_indicators if record.gemma_indicators else []
            )

            # Update database
            content_analysis = session.query(ContentAnalysis).get(record.id)
            if content_analysis:
                content_analysis.ensemble_concern_level = ensemble_level
                content_analysis.ensemble_confidence = confidence
                content_analysis.ensemble_indicators = ensemble_indicators

                processed_count += 1
                concern_distribution[ensemble_level] += 1

                if confidence >= 0.75:
                    high_confidence_count += 1

                # Show progress for high concern cases
                if ensemble_level in ['high', 'critical']:
                    print(f"   🚨 Result {record.result_id}: {ensemble_level} "
                          f"(confidence: {confidence:.2f})")
                elif processed_count % 50 == 0:
                    print(f"   📊 Processed {processed_count}/{len(records)} images...")

        # Commit all changes
        session.commit()

        # Summary statistics
        print("\n" + "="*60)
        print("✅ ENSEMBLE ANALYSIS COMPLETED")
        print("="*60)
        print(f"📊 Total processed: {processed_count}")
        print(f"🎯 High confidence (≥75%): {high_confidence_count} "
              f"({high_confidence_count*100/processed_count:.1f}%)")

        print("\n📈 Concern Level Distribution:")
        for level in ['critical', 'high', 'medium', 'low']:
            count = concern_distribution[level]
            percentage = count * 100 / processed_count if processed_count > 0 else 0
            bar = "█" * int(percentage / 2)
            print(f"   {level.upper():8s}: {count:4d} ({percentage:5.1f}%) {bar}")

        # Find images with disagreement
        disagreement_query = session.execute(text("""
            SELECT COUNT(*) as count
            FROM content_analysis
            WHERE ensemble_confidence < 0.5
            AND ensemble_confidence IS NOT NULL
        """))
        disagreement_count = disagreement_query.scalar()

        if disagreement_count > 0:
            print(f"\n⚠️  Model disagreement (confidence < 50%): {disagreement_count} images")
            print("   These may require manual review")

        return processed_count


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Apply ensemble analysis to combined model results')
    parser.add_argument('--limit', type=int,
                        help='Limit number of images to process')
    parser.add_argument('--force-update', action='store_true',
                        help='Re-calculate ensemble for all images (including existing)')

    args = parser.parse_args()

    session = get_session()

    try:
        # Check if we have data to process
        check_query = session.execute(text("""
            SELECT
                COUNT(*) as total_images,
                COUNT(CASE WHEN concern_level IS NOT NULL THEN 1 END) as with_llava,
                COUNT(CASE WHEN gemma_concern_level IS NOT NULL THEN 1 END) as with_gemma,
                COUNT(CASE WHEN concern_level IS NOT NULL
                      AND gemma_concern_level IS NOT NULL THEN 1 END) as with_both,
                COUNT(CASE WHEN ensemble_concern_level IS NOT NULL THEN 1 END) as with_ensemble
            FROM content_analysis
        """))
        stats = check_query.fetchone()

        print("\n📊 Current Analysis Status:")
        print(f"   Total images analyzed: {stats.total_images}")
        print(f"   With LLaVA analysis: {stats.with_llava}")
        print(f"   With gemma3:12b analysis: {stats.with_gemma}")
        print(f"   With both analyses: {stats.with_both}")
        print(f"   With ensemble results: {stats.with_ensemble}")

        if stats.with_both == 0:
            print("\n❌ No images have both LLaVA and gemma3:12b analyses!")
            print("   Please run both model processors first:")
            print("   - python process_missing_llava_parallel.py")
            print("   - python process_gemma_structured.py")
            return

        pending = stats.with_both - stats.with_ensemble
        if pending == 0 and not args.force_update:
            print("\n✅ All images already have ensemble analysis!")
            print("   Use --force-update to recalculate")
            return

        print(f"\n🎯 Ready to process {pending} images for ensemble analysis")

        # Apply ensemble analysis
        analyzer = EnsembleAnalyzer()
        processed = analyzer.process_ensemble_analysis(
            session,
            limit=args.limit,
            force_update=args.force_update
        )

        print(f"\n✨ Successfully completed ensemble analysis for {processed} images")

    except Exception as e:
        print(f"\n❌ Ensemble analysis failed: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()

    finally:
        session.close()


if __name__ == "__main__":
    main()