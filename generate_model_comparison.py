#!/usr/bin/env python3
"""Generate comprehensive model comparison report between gemma3n:e4b and gemma3:12b"""

import pandas as pd
from datetime import datetime
from database.connection import get_session
from database.models import ContentAnalysis
from sqlalchemy import text
import json


def generate_model_comparison():
    """Generate detailed comparison report between gemma3n:e4b and gemma3:12b models"""

    session = get_session()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"model_comparison_report_{timestamp}.xlsx"

    print("="*60)
    print("MODEL COMPARISON REPORT GENERATOR")
    print("="*60)
    print("Comparing: gemma3n:e4b vs gemma3:12b")

    # Create Excel writer
    writer = pd.ExcelWriter(output_file, engine='openpyxl')

    try:
        # 1. Overview Statistics
        print("\n📊 Gathering overview statistics...")

        stats_query = session.execute(text("""
            SELECT
                COUNT(*) as total_analyzed,
                COUNT(CASE WHEN gemma_description IS NOT NULL THEN 1 END) as with_gemma3n,
                COUNT(CASE WHEN gemma12b_description IS NOT NULL THEN 1 END) as with_gemma12b,
                COUNT(CASE WHEN gemma_description IS NOT NULL
                      AND gemma12b_description IS NOT NULL THEN 1 END) as with_both,
                AVG(CASE WHEN gemma_processing_time IS NOT NULL
                    THEN gemma_processing_time END) as avg_gemma3n_time,
                AVG(CASE WHEN gemma12b_processing_time IS NOT NULL
                    THEN gemma12b_processing_time END) as avg_gemma12b_time
            FROM content_analysis
        """))
        stats = stats_query.fetchone()

        overview_data = [
            ['Report Generated', datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ['', ''],
            ['MODEL COMPARISON OVERVIEW', ''],
            ['Total Images Analyzed', stats.total_analyzed],
            ['Processed with gemma3n:e4b', stats.with_gemma3n],
            ['Processed with gemma3:12b', stats.with_gemma12b],
            ['Processed with both models', stats.with_both],
            ['', ''],
            ['PERFORMANCE METRICS', ''],
            ['Avg Processing Time - gemma3n:e4b', f'{stats.avg_gemma3n_time:.2f} seconds' if stats.avg_gemma3n_time else 'N/A'],
            ['Avg Processing Time - gemma3:12b', f'{stats.avg_gemma12b_time:.2f} seconds' if stats.avg_gemma12b_time else 'N/A'],
            ['Speed Difference', f'{abs(stats.avg_gemma12b_time - stats.avg_gemma3n_time):.2f} seconds'
             if stats.avg_gemma3n_time and stats.avg_gemma12b_time else 'N/A']
        ]

        df_overview = pd.DataFrame(overview_data, columns=['Metric', 'Value'])
        df_overview.to_excel(writer, sheet_name='Overview', index=False)

        # 2. Concern Level Agreement Analysis
        print("📈 Analyzing concern level agreements...")

        agreement_query = session.execute(text("""
            SELECT
                gemma_concern_level,
                gemma12b_concern_level,
                COUNT(*) as count
            FROM content_analysis
            WHERE gemma_concern_level IS NOT NULL
            AND gemma12b_concern_level IS NOT NULL
            GROUP BY gemma_concern_level, gemma12b_concern_level
            ORDER BY count DESC
        """))

        agreement_data = []
        total_comparisons = 0
        exact_matches = 0

        for row in agreement_query:
            agreement_data.append({
                'Gemma3n:e4b Level': row.gemma_concern_level,
                'Gemma3:12b Level': row.gemma12b_concern_level,
                'Count': row.count,
                'Agreement': 'Yes' if row.gemma_concern_level == row.gemma12b_concern_level else 'No'
            })
            total_comparisons += row.count
            if row.gemma_concern_level == row.gemma12b_concern_level:
                exact_matches += row.count

        if agreement_data:
            df_agreement = pd.DataFrame(agreement_data)
            df_agreement.to_excel(writer, sheet_name='Concern Agreement', index=False)

            agreement_rate = (exact_matches / total_comparisons * 100) if total_comparisons > 0 else 0
            print(f"   Agreement rate: {agreement_rate:.1f}%")

        # 3. Disagreement Cases
        print("⚠️  Finding disagreement cases...")

        disagreement_query = session.execute(text("""
            SELECT
                result_id,
                scene_description,
                gemma_concern_level,
                gemma_description,
                gemma12b_concern_level,
                gemma12b_description,
                ensemble_concern_level
            FROM content_analysis
            WHERE gemma_concern_level IS NOT NULL
            AND gemma12b_concern_level IS NOT NULL
            AND gemma_concern_level != gemma12b_concern_level
            ORDER BY
                CASE
                    WHEN gemma_concern_level = 'critical' OR gemma12b_concern_level = 'critical' THEN 4
                    WHEN gemma_concern_level = 'high' OR gemma12b_concern_level = 'high' THEN 3
                    WHEN gemma_concern_level = 'medium' OR gemma12b_concern_level = 'medium' THEN 2
                    ELSE 1
                END DESC
            LIMIT 100
        """))

        disagreement_data = []
        for row in disagreement_query:
            disagreement_data.append({
                'Result ID': row.result_id,
                'LLaVA Description': row.scene_description[:200] if row.scene_description else '',
                'Gemma3n:e4b Concern': row.gemma_concern_level,
                'Gemma3n:e4b Analysis': row.gemma_description[:200] if row.gemma_description else '',
                'Gemma3:12b Concern': row.gemma12b_concern_level,
                'Gemma3:12b Analysis': row.gemma12b_description[:200] if row.gemma12b_description else '',
                'Ensemble Decision': row.ensemble_concern_level if row.ensemble_concern_level else 'N/A'
            })

        if disagreement_data:
            df_disagreement = pd.DataFrame(disagreement_data)
            df_disagreement.to_excel(writer, sheet_name='Disagreement Cases', index=False)
            print(f"   Found {len(disagreement_data)} disagreement cases")

        # 4. Performance by Concern Level
        print("📊 Analyzing performance by concern level...")

        performance_query = session.execute(text("""
            SELECT
                concern_level,
                COUNT(CASE WHEN gemma_concern_level IS NOT NULL THEN 1 END) as gemma3n_count,
                COUNT(CASE WHEN gemma12b_concern_level IS NOT NULL THEN 1 END) as gemma12b_count,
                AVG(CASE WHEN gemma_processing_time IS NOT NULL THEN gemma_processing_time END) as avg_gemma3n_time,
                AVG(CASE WHEN gemma12b_processing_time IS NOT NULL THEN gemma12b_processing_time END) as avg_gemma12b_time
            FROM content_analysis
            WHERE concern_level IS NOT NULL
            GROUP BY concern_level
            ORDER BY
                CASE concern_level
                    WHEN 'critical' THEN 4
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    ELSE 1
                END DESC
        """))

        performance_data = []
        for row in performance_query:
            performance_data.append({
                'LLaVA Concern Level': row.concern_level,
                'Gemma3n:e4b Processed': row.gemma3n_count,
                'Gemma3:12b Processed': row.gemma12b_count,
                'Avg Time gemma3n:e4b (sec)': round(row.avg_gemma3n_time, 2) if row.avg_gemma3n_time else 0,
                'Avg Time gemma3:12b (sec)': round(row.avg_gemma12b_time, 2) if row.avg_gemma12b_time else 0
            })

        if performance_data:
            df_performance = pd.DataFrame(performance_data)
            df_performance.to_excel(writer, sheet_name='Performance Analysis', index=False)

        # 5. Indicator Comparison
        print("🔍 Comparing indicators detected...")

        # Get sample of images with both analyses for indicator comparison
        indicator_query = session.execute(text("""
            SELECT
                result_id,
                concern_indicators,
                restriction_indicators,
                gemma_indicators
            FROM content_analysis
            WHERE gemma_indicators IS NOT NULL
            AND array_length(gemma_indicators, 1) > 0
            LIMIT 50
        """))

        indicator_comparison = []
        for row in indicator_query:
            gemma3n_indicators = row.gemma_indicators[:5] if row.gemma_indicators else []
            gemma_indicators = row.gemma_indicators[:5] if row.gemma_indicators else []

            # Find overlapping indicators
            overlap = []
            for g3n in gemma3n_indicators:
                for g12b in gemma_indicators:
                    if g3n.lower() in g12b.lower() or g12b.lower() in g3n.lower():
                        overlap.append(g3n)
                        break

            indicator_comparison.append({
                'Result ID': row.result_id,
                'Gemma3n:e4b Indicators': '; '.join(gemma3n_indicators),
                'Gemma3:12b Indicators': '; '.join(gemma_indicators),
                'Overlapping': '; '.join(overlap) if overlap else 'None',
                'Ensemble Combined': '; '.join(row.gemma_indicators[:5]) if row.gemma_indicators else 'N/A'
            })

        if indicator_comparison:
            df_indicators = pd.DataFrame(indicator_comparison)
            df_indicators.to_excel(writer, sheet_name='Indicator Comparison', index=False)

        # 6. Model Tendency Analysis
        print("📊 Analyzing model tendencies...")

        tendency_query = session.execute(text("""
            SELECT
                'gemma3n:e4b' as model,
                COUNT(CASE WHEN gemma_concern_level = 'low' THEN 1 END) as low_count,
                COUNT(CASE WHEN gemma_concern_level = 'medium' THEN 1 END) as medium_count,
                COUNT(CASE WHEN gemma_concern_level = 'high' THEN 1 END) as high_count,
                COUNT(CASE WHEN gemma_concern_level = 'critical' THEN 1 END) as critical_count,
                COUNT(*) as total
            FROM content_analysis
            WHERE gemma_concern_level IS NOT NULL
            UNION ALL
            SELECT
                'gemma3:12b' as model,
                COUNT(CASE WHEN gemma12b_concern_level = 'low' THEN 1 END) as low_count,
                COUNT(CASE WHEN gemma12b_concern_level = 'medium' THEN 1 END) as medium_count,
                COUNT(CASE WHEN gemma12b_concern_level = 'high' THEN 1 END) as high_count,
                COUNT(CASE WHEN gemma12b_concern_level = 'critical' THEN 1 END) as critical_count,
                COUNT(*) as total
            FROM content_analysis
            WHERE gemma12b_concern_level IS NOT NULL
        """))

        tendency_data = []
        for row in tendency_query:
            total = row.total if row.total > 0 else 1
            tendency_data.append({
                'Model': row.model,
                'Low (%)': round(row.low_count * 100 / total, 1),
                'Medium (%)': round(row.medium_count * 100 / total, 1),
                'High (%)': round(row.high_count * 100 / total, 1),
                'Critical (%)': round(row.critical_count * 100 / total, 1),
                'Total Analyzed': row.total
            })

        if tendency_data:
            df_tendency = pd.DataFrame(tendency_data)
            df_tendency.to_excel(writer, sheet_name='Model Tendencies', index=False)

        # Save the workbook
        writer.close()

        print(f"\n✅ Model comparison report completed!")
        print(f"📁 Output file: {output_file}")
        print(f"📊 Sheets created:")
        print(f"   - Overview: Overall statistics and performance")
        print(f"   - Concern Agreement: Agreement matrix between models")
        print(f"   - Disagreement Cases: Top 100 cases where models disagree")
        print(f"   - Performance Analysis: Processing times by concern level")
        print(f"   - Indicator Comparison: Sample of indicator detection")
        print(f"   - Model Tendencies: Distribution of concern levels by model")

        # Print summary insights
        if stats.with_both > 0:
            print(f"\n🔍 Key Insights:")
            print(f"   - Agreement rate: {agreement_rate:.1f}%")
            print(f"   - Images analyzed by both: {stats.with_both}")

            if stats.avg_gemma3n_time and stats.avg_gemma12b_time:
                speed_factor = stats.avg_gemma12b_time / stats.avg_gemma3n_time
                faster_model = "gemma3n:e4b" if speed_factor > 1 else "gemma3:12b"
                print(f"   - Faster model: {faster_model} ({abs(1-speed_factor)*100:.0f}% faster)")

        return output_file

    except Exception as e:
        print(f"\n❌ Report generation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    generate_model_comparison()