#!/usr/bin/env python3
"""Export DPRK image analysis results to comprehensive spreadsheet"""

import pandas as pd
from datetime import datetime
from database.connection import get_session
from database.models import SearchResult, CapturedImage, ContentAnalysis, SearchQuery
from sqlalchemy import text
import json

def export_to_spreadsheet():
    """Export all data to Excel spreadsheet with multiple sheets"""

    session = get_session()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"dprk_analysis_export_{timestamp}.xlsx"

    print("="*60)
    print("EXPORTING DPRK IMAGE ANALYSIS TO SPREADSHEET")
    print("="*60)

    # Create Excel writer
    writer = pd.ExcelWriter(output_file, engine='openpyxl')

    try:
        # 1. Summary Sheet
        print("\n📊 Creating Summary sheet...")
        summary_data = []

        # Get overall statistics
        total_images = session.query(CapturedImage).count()
        total_results = session.query(SearchResult).count()
        total_analyzed = session.query(ContentAnalysis).count()
        with_ensemble = session.query(ContentAnalysis).filter(
            ContentAnalysis.ensemble_concern_level.isnot(None)
        ).count()

        # Get concern level distribution
        concern_dist = session.execute(text("""
            SELECT ensemble_concern_level, COUNT(*) as count
            FROM content_analysis
            WHERE ensemble_concern_level IS NOT NULL
            GROUP BY ensemble_concern_level
            ORDER BY count DESC
        """)).fetchall()

        summary_data.append(['Report Generated', datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        summary_data.append(['', ''])
        summary_data.append(['OVERALL STATISTICS', ''])
        summary_data.append(['Total Captured Images', total_images])
        summary_data.append(['Total Search Results', total_results])
        summary_data.append(['Total Analyzed (LLaVA)', total_analyzed])
        summary_data.append(['With Ensemble Analysis', with_ensemble])
        summary_data.append(['Pending Gemma Processing', total_analyzed - with_ensemble])
        summary_data.append(['', ''])
        summary_data.append(['ENSEMBLE CONCERN DISTRIBUTION', ''])

        for level, count in concern_dist:
            summary_data.append([f'{level.title()} Concern', count])

        df_summary = pd.DataFrame(summary_data, columns=['Metric', 'Value'])
        df_summary.to_excel(writer, sheet_name='Summary', index=False)

        # 2. Full Analysis Results Sheet
        print("📋 Creating Full Analysis Results sheet...")

        query = session.query(
            SearchResult.id,
            SearchResult.title,
            SearchResult.page_url,
            SearchResult.image_url,
            SearchResult.source_domain,
            SearchQuery.search_term,
            SearchQuery.theme,
            CapturedImage.file_path,
            CapturedImage.file_size,
            CapturedImage.image_width,
            CapturedImage.image_height,
            ContentAnalysis.scene_description,
            ContentAnalysis.concern_level,
            ContentAnalysis.personnel_count,
            ContentAnalysis.supervision_present,
            ContentAnalysis.activity_type,
            ContentAnalysis.confidence_score,
            ContentAnalysis.gemma_description,
            ContentAnalysis.gemma_concern_level,
            ContentAnalysis.ensemble_concern_level,
            ContentAnalysis.ensemble_confidence,
            ContentAnalysis.analyzed_at
        ).outerjoin(
            SearchQuery, SearchResult.query_id == SearchQuery.id
        ).outerjoin(
            CapturedImage, SearchResult.id == CapturedImage.result_id
        ).outerjoin(
            ContentAnalysis, SearchResult.id == ContentAnalysis.result_id
        ).all()

        results_data = []
        for row in query:
            results_data.append({
                'Result ID': row.id,
                'Title': row.title[:100] if row.title else '',
                'Page URL': row.page_url,
                'Image URL': row.image_url,
                'Source Domain': row.source_domain,
                'Search Query': row.search_term[:50] if row.search_term else '',
                'Theme': row.theme,
                'Image File': row.file_path.split('/')[-1] if row.file_path else '',
                'File Size (KB)': round(row.file_size/1024, 1) if row.file_size else None,
                'Width': row.image_width,
                'Height': row.image_height,
                'LLaVA Description': row.scene_description[:200] if row.scene_description else '',
                'LLaVA Concern': row.concern_level,
                'Personnel Count': row.personnel_count,
                'Supervision': 'Yes' if row.supervision_present else 'No' if row.supervision_present is not None else '',
                'Activity Type': row.activity_type,
                'LLaVA Confidence': round(row.confidence_score, 2) if row.confidence_score else None,
                'Gemma Description': row.gemma_description[:200] if row.gemma_description else '',
                'Gemma Concern': row.gemma_concern_level,
                'Ensemble Concern': row.ensemble_concern_level,
                'Ensemble Confidence': round(row.ensemble_confidence, 2) if row.ensemble_confidence else None,
                'Analysis Date': row.analyzed_at.strftime("%Y-%m-%d %H:%M") if row.analyzed_at else ''
            })

        df_results = pd.DataFrame(results_data)
        df_results.to_excel(writer, sheet_name='Full Analysis', index=False)

        # 3. High Concern Cases Sheet
        print("⚠️  Creating High Concern Cases sheet...")

        high_concern_query = session.query(
            SearchResult.id,
            SearchResult.title,
            SearchResult.page_url,
            SearchResult.source_domain,
            CapturedImage.file_path,
            ContentAnalysis.scene_description,
            ContentAnalysis.concern_level,
            ContentAnalysis.concern_indicators,
            ContentAnalysis.restriction_indicators,
            ContentAnalysis.gemma_description,
            ContentAnalysis.gemma_concern_level,
            ContentAnalysis.gemma_indicators,
            ContentAnalysis.ensemble_concern_level,
            ContentAnalysis.ensemble_confidence
        ).join(
            CapturedImage, SearchResult.id == CapturedImage.result_id
        ).join(
            ContentAnalysis, SearchResult.id == ContentAnalysis.result_id
        ).filter(
            ContentAnalysis.ensemble_concern_level.in_(['high', 'critical', 'medium'])
        ).all()

        high_concern_data = []
        for row in high_concern_query:
            # Combine indicators
            all_indicators = []
            if row.concern_indicators:
                all_indicators.extend(row.concern_indicators[:5])
            if row.restriction_indicators:
                all_indicators.extend(row.restriction_indicators[:5])
            if row.gemma_indicators:
                all_indicators.extend(row.gemma_indicators[:5])

            high_concern_data.append({
                'Result ID': row.id,
                'Title': row.title[:100] if row.title else '',
                'Source': row.source_domain,
                'Page URL': row.page_url,
                'Image File': row.file_path.split('/')[-1] if row.file_path else '',
                'LLaVA Concern': row.concern_level,
                'Gemma Concern': row.gemma_concern_level,
                'Ensemble Concern': row.ensemble_concern_level,
                'Ensemble Confidence': round(row.ensemble_confidence, 2) if row.ensemble_confidence else None,
                'LLaVA Description': row.scene_description[:300] if row.scene_description else '',
                'Gemma Description': row.gemma_description[:300] if row.gemma_description else '',
                'Combined Indicators': '; '.join(all_indicators[:10])
            })

        if high_concern_data:
            df_high_concern = pd.DataFrame(high_concern_data)
            df_high_concern.to_excel(writer, sheet_name='High Concern Cases', index=False)

        # 4. Search Queries Performance Sheet
        print("🔍 Creating Search Performance sheet...")

        search_perf = session.execute(text("""
            SELECT
                sq.search_term as search_query,
                sq.theme,
                sq.search_type as source_type,
                COUNT(DISTINCT sr.id) as total_results,
                COUNT(DISTINCT ci.id) as images_captured,
                COUNT(DISTINCT ca.id) as images_analyzed,
                COUNT(DISTINCT CASE WHEN ca.ensemble_concern_level IS NOT NULL THEN ca.id END) as with_ensemble,
                COUNT(DISTINCT CASE WHEN ca.ensemble_concern_level IN ('high', 'critical') THEN ca.id END) as high_concern
            FROM search_queries sq
            LEFT JOIN search_results sr ON sq.id = sr.query_id
            LEFT JOIN captured_images ci ON sr.id = ci.result_id
            LEFT JOIN content_analysis ca ON sr.id = ca.result_id
            GROUP BY sq.id, sq.search_term, sq.theme, sq.search_type
            ORDER BY high_concern DESC, images_captured DESC
        """)).fetchall()

        search_data = []
        for row in search_perf:
            search_data.append({
                'Search Query': row.search_query[:80],
                'Theme': row.theme,
                'Source Type': row.source_type,
                'Total Results': row.total_results,
                'Images Captured': row.images_captured,
                'Images Analyzed': row.images_analyzed,
                'With Ensemble': row.with_ensemble,
                'High Concern Found': row.high_concern
            })

        df_search = pd.DataFrame(search_data)
        df_search.to_excel(writer, sheet_name='Search Performance', index=False)

        # 5. Theme Analysis Sheet
        print("🎯 Creating Theme Analysis sheet...")

        theme_analysis = session.execute(text("""
            SELECT
                COALESCE(sq.theme, 'general') as theme,
                COUNT(DISTINCT sr.id) as total_results,
                COUNT(DISTINCT ci.id) as images_captured,
                COUNT(DISTINCT ca.id) as images_analyzed,
                COUNT(DISTINCT CASE WHEN ca.ensemble_concern_level = 'low' THEN ca.id END) as low_concern,
                COUNT(DISTINCT CASE WHEN ca.ensemble_concern_level = 'medium' THEN ca.id END) as medium_concern,
                COUNT(DISTINCT CASE WHEN ca.ensemble_concern_level = 'high' THEN ca.id END) as high_concern,
                COUNT(DISTINCT CASE WHEN ca.ensemble_concern_level = 'critical' THEN ca.id END) as critical_concern
            FROM search_queries sq
            LEFT JOIN search_results sr ON sq.id = sr.query_id
            LEFT JOIN captured_images ci ON sr.id = ci.result_id
            LEFT JOIN content_analysis ca ON sr.id = ca.result_id
            GROUP BY sq.theme
            ORDER BY (COUNT(DISTINCT CASE WHEN ca.ensemble_concern_level = 'high' THEN ca.id END) +
                      COUNT(DISTINCT CASE WHEN ca.ensemble_concern_level = 'critical' THEN ca.id END)) DESC
        """)).fetchall()

        theme_data = []
        for row in theme_analysis:
            theme_data.append({
                'Theme': row.theme.replace('_', ' ').title(),
                'Total Results': row.total_results,
                'Images Captured': row.images_captured,
                'Images Analyzed': row.images_analyzed,
                'Low Concern': row.low_concern,
                'Medium Concern': row.medium_concern,
                'High Concern': row.high_concern,
                'Critical Concern': row.critical_concern,
                'Total Concerning': row.medium_concern + row.high_concern + row.critical_concern
            })

        df_theme = pd.DataFrame(theme_data)
        df_theme.to_excel(writer, sheet_name='Theme Analysis', index=False)

        # Save the workbook
        writer.close()

        print(f"\n✅ Export completed successfully!")
        print(f"📁 Output file: {output_file}")
        print(f"📊 Sheets created:")
        print(f"   - Summary: Overview statistics")
        print(f"   - Full Analysis: All {len(results_data)} results with analysis")
        print(f"   - High Concern Cases: {len(high_concern_data)} concerning images")
        print(f"   - Search Performance: {len(search_data)} search queries analyzed")
        print(f"   - Theme Analysis: {len(theme_data)} themes summarized")

        return output_file

    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    export_to_spreadsheet()