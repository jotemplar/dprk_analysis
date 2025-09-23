#!/usr/bin/env python3
"""Export article analysis data to Excel spreadsheet"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

sys.path.append(str(Path(__file__).parent))

from database.connection import get_session
from sqlalchemy import text

def export_articles_to_excel():
    """Export comprehensive article analysis to Excel"""

    session = get_session()
    output_file = f"dprk_article_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    print("📊 Exporting article analysis to Excel...")

    # Create Excel writer
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:

        # 1. Main Analysis Data
        print("  📝 Exporting main analysis data...")
        main_query = """
        SELECT
            ar.id,
            asrch.category as search_category,
            asrch.search_term,
            ar.title,
            ar.url,
            ar.source_domain,
            ar.snippet,
            ar.published_date,
            ac.word_count,
            ac.language,
            aa.concern_level,
            aa.confidence_score,
            aa.summary,
            aa.worker_conditions,
            aa.refugee_mentions,
            aa.original_language,
            aa.processing_time,
            aa.analyzed_at
        FROM article_results ar
        LEFT JOIN article_searches asrch ON ar.search_id = asrch.id
        LEFT JOIN article_content ac ON ar.id = ac.result_id
        LEFT JOIN article_analysis aa ON ar.id = aa.result_id
        WHERE aa.error_message IS NULL
        ORDER BY
            CASE aa.concern_level
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
                ELSE 5
            END,
            aa.confidence_score DESC
        """

        df_main = pd.read_sql(text(main_query), session.bind)

        # Remove timezone info from datetime columns for Excel compatibility
        datetime_columns = ['published_date', 'analyzed_at']
        for col in datetime_columns:
            if col in df_main.columns and pd.api.types.is_datetime64_any_dtype(df_main[col]):
                df_main[col] = df_main[col].dt.tz_localize(None)

        df_main.to_excel(writer, sheet_name='Main Analysis', index=False)

        # 2. High Priority Articles
        print("  ⚠️  Exporting high priority articles...")
        high_priority_query = """
        SELECT
            asrch.category as search_category,
            asrch.search_term,
            ar.title,
            ar.url,
            ar.source_domain,
            aa.concern_level,
            aa.confidence_score,
            aa.summary,
            array_to_string(aa.concern_indicators, '; ') as concern_indicators,
            array_to_string(aa.human_rights_issues, '; ') as human_rights_issues
        FROM article_results ar
        JOIN article_searches asrch ON ar.search_id = asrch.id
        JOIN article_analysis aa ON ar.id = aa.result_id
        WHERE aa.concern_level IN ('critical', 'high')
        AND aa.error_message IS NULL
        ORDER BY
            CASE aa.concern_level
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
            END,
            aa.confidence_score DESC
        """

        df_priority = pd.read_sql(text(high_priority_query), session.bind)
        df_priority.to_excel(writer, sheet_name='High Priority', index=False)

        # 3. Entities Analysis
        print("  🏢 Exporting entities analysis...")

        # Corporate entities
        corp_query = """
        WITH corps AS (
            SELECT
                ar.id,
                ar.title,
                ar.url,
                asrch.category as search_category,
                unnest(aa.corporate_involvement) as corporation
            FROM article_analysis aa
            JOIN article_results ar ON aa.result_id = ar.id
            JOIN article_searches asrch ON ar.search_id = asrch.id
            WHERE aa.corporate_involvement IS NOT NULL
            AND array_length(aa.corporate_involvement, 1) > 0
        )
        SELECT
            corporation as entity_name,
            'Corporation' as entity_type,
            COUNT(DISTINCT id) as article_count,
            string_agg(DISTINCT search_category, ', ' ORDER BY search_category) as search_categories,
            string_agg(DISTINCT title || ' (' || url || ')', '; ') as articles_with_urls
        FROM corps
        WHERE corporation NOT LIKE '%No specific%'
        AND corporation NOT LIKE '%are mentioned%'
        GROUP BY corporation
        ORDER BY article_count DESC
        """

        # Government entities (with consolidation)
        gov_query = """
        WITH govs AS (
            SELECT
                ar.id,
                ar.title,
                ar.url,
                asrch.category as search_category,
                unnest(aa.government_entities) as entity
            FROM article_analysis aa
            JOIN article_results ar ON aa.result_id = ar.id
            JOIN article_searches asrch ON ar.search_id = asrch.id
            WHERE aa.government_entities IS NOT NULL
        ),
        normalized AS (
            SELECT
                id,
                title,
                url,
                search_category,
                CASE
                    WHEN entity ILIKE '%russian government%'
                        OR entity ILIKE '%government of russia%'
                        OR entity = 'Russia'
                        THEN 'Russian Government'
                    WHEN entity ILIKE '%north korea%government%'
                        OR entity ILIKE '%dprk%government%'
                        THEN 'North Korean Government'
                    WHEN entity ILIKE '%chinese government%'
                        OR entity = 'China'
                        THEN 'Chinese Government'
                    WHEN entity ILIKE '%united states%'
                        OR entity ILIKE '%u.s.%government%'
                        THEN 'United States Government'
                    WHEN entity ILIKE '%united nations%'
                        OR entity ILIKE '%u.n.%'
                        THEN 'United Nations'
                    ELSE entity
                END as normalized_entity
            FROM govs
        )
        SELECT
            normalized_entity as entity_name,
            'Government' as entity_type,
            COUNT(DISTINCT id) as article_count,
            string_agg(DISTINCT search_category, ', ' ORDER BY search_category) as search_categories,
            string_agg(DISTINCT title || ' (' || url || ')', '; ') as articles_with_urls
        FROM normalized
        WHERE normalized_entity NOT LIKE '%No specific%'
        GROUP BY normalized_entity
        ORDER BY article_count DESC
        """

        df_corps = pd.read_sql(text(corp_query), session.bind)
        df_govs = pd.read_sql(text(gov_query), session.bind)
        df_entities = pd.concat([df_corps, df_govs], ignore_index=True)
        df_entities = df_entities.sort_values('article_count', ascending=False)
        df_entities.to_excel(writer, sheet_name='Entities', index=False)

        # 4. Key Insights
        print("  💡 Exporting key insights...")
        insights_query = """
        WITH insights AS (
            SELECT
                ar.id,
                ar.title,
                ar.url,
                aa.concern_level,
                unnest(aa.key_insights) as insight
            FROM article_analysis aa
            JOIN article_results ar ON aa.result_id = ar.id
            WHERE aa.key_insights IS NOT NULL
            AND array_length(aa.key_insights, 1) > 0
        )
        SELECT
            insight,
            COUNT(*) as frequency,
            string_agg(DISTINCT concern_level, ', ' ORDER BY concern_level) as concern_levels,
            string_agg(DISTINCT title, '; ' ORDER BY title) as example_articles
        FROM insights
        WHERE insight IS NOT NULL AND insight != ''
        GROUP BY insight
        HAVING COUNT(*) > 1
        ORDER BY frequency DESC
        LIMIT 100
        """

        df_insights = pd.read_sql(text(insights_query), session.bind)
        df_insights.to_excel(writer, sheet_name='Key Insights', index=False)

        # 5. Human Rights Issues
        print("  ⚖️  Exporting human rights issues...")
        hr_query = """
        WITH hr_issues AS (
            SELECT
                ar.id,
                ar.title,
                ar.url,
                aa.concern_level,
                unnest(aa.human_rights_issues) as issue
            FROM article_analysis aa
            JOIN article_results ar ON aa.result_id = ar.id
            WHERE aa.human_rights_issues IS NOT NULL
            AND array_length(aa.human_rights_issues, 1) > 0
        )
        SELECT
            issue as human_rights_issue,
            COUNT(*) as frequency,
            COUNT(CASE WHEN concern_level IN ('critical', 'high') THEN 1 END) as high_priority_count,
            string_agg(DISTINCT title, '; ' ORDER BY title) as example_articles
        FROM hr_issues
        WHERE issue IS NOT NULL AND issue != ''
        GROUP BY issue
        ORDER BY frequency DESC
        """

        df_hr = pd.read_sql(text(hr_query), session.bind)
        df_hr.to_excel(writer, sheet_name='Human Rights', index=False)

        # 6. Concern Indicators
        print("  🚨 Exporting concern indicators...")
        concern_query = """
        WITH indicators AS (
            SELECT
                ar.id,
                ar.title,
                aa.concern_level,
                unnest(aa.concern_indicators) as indicator
            FROM article_analysis aa
            JOIN article_results ar ON aa.result_id = ar.id
            WHERE aa.concern_indicators IS NOT NULL
            AND array_length(aa.concern_indicators, 1) > 0
        )
        SELECT
            indicator,
            COUNT(*) as frequency,
            COUNT(CASE WHEN concern_level = 'critical' THEN 1 END) as critical_count,
            COUNT(CASE WHEN concern_level = 'high' THEN 1 END) as high_count,
            COUNT(CASE WHEN concern_level = 'medium' THEN 1 END) as medium_count,
            COUNT(CASE WHEN concern_level = 'low' THEN 1 END) as low_count
        FROM indicators
        WHERE indicator IS NOT NULL AND indicator != ''
        GROUP BY indicator
        ORDER BY
            COUNT(CASE WHEN concern_level = 'critical' THEN 1 END) * 4 +
            COUNT(CASE WHEN concern_level = 'high' THEN 1 END) * 3 +
            COUNT(CASE WHEN concern_level = 'medium' THEN 1 END) * 2 +
            COUNT(CASE WHEN concern_level = 'low' THEN 1 END) DESC
        """

        df_concern = pd.read_sql(text(concern_query), session.bind)
        df_concern.to_excel(writer, sheet_name='Concern Indicators', index=False)

        # 7. Search Performance Analysis
        print("  🔍 Generating search performance analysis...")
        search_perf_query = """
        SELECT
            asrch.category,
            asrch.search_term,
            COUNT(DISTINCT ar.id) as total_articles,
            COUNT(DISTINCT CASE WHEN aa.concern_level IN ('critical', 'high') THEN ar.id END) as high_priority_count,
            COUNT(DISTINCT CASE WHEN aa.concern_level = 'critical' THEN ar.id END) as critical_count,
            AVG(aa.confidence_score) as avg_confidence_score,
            COUNT(DISTINCT
                CASE WHEN array_length(aa.corporate_involvement, 1) > 0
                THEN ar.id END
            ) as articles_with_corporations,
            COUNT(DISTINCT
                CASE WHEN array_length(aa.government_entities, 1) > 0
                THEN ar.id END
            ) as articles_with_govs,
            COUNT(DISTINCT
                CASE WHEN array_length(aa.human_rights_issues, 1) > 0
                THEN ar.id END
            ) as articles_with_hr_issues,
            MIN(ar.published_date) as earliest_article,
            MAX(ar.published_date) as latest_article
        FROM article_searches asrch
        JOIN article_results ar ON ar.search_id = asrch.id
        LEFT JOIN article_analysis aa ON ar.id = aa.result_id
        WHERE aa.error_message IS NULL
        GROUP BY asrch.category, asrch.search_term
        ORDER BY
            asrch.category,
            high_priority_count DESC,
            total_articles DESC
        """

        df_search_perf = pd.read_sql(text(search_perf_query), session.bind)

        # Remove timezone info from datetime columns
        datetime_cols = ['earliest_article', 'latest_article']
        for col in datetime_cols:
            if col in df_search_perf.columns and pd.api.types.is_datetime64_any_dtype(df_search_perf[col]):
                df_search_perf[col] = df_search_perf[col].dt.tz_localize(None)

        df_search_perf.to_excel(writer, sheet_name='Search Performance', index=False)

        # 8. Summary Statistics
        print("  📈 Generating summary statistics...")
        stats_data = []

        # Overall stats
        total_articles = session.execute(text("SELECT COUNT(*) FROM article_results")).scalar()
        analyzed_articles = session.execute(text("SELECT COUNT(*) FROM article_analysis WHERE error_message IS NULL")).scalar()

        stats_data.append(["Total Articles", total_articles])
        stats_data.append(["Successfully Analyzed", analyzed_articles])
        stats_data.append(["Analysis Success Rate", f"{(analyzed_articles/total_articles*100):.1f}%"])
        stats_data.append(["", ""])

        # Concern level distribution
        concern_stats = session.execute(text("""
            SELECT concern_level, COUNT(*) as count
            FROM article_analysis
            WHERE error_message IS NULL
            GROUP BY concern_level
            ORDER BY
                CASE concern_level
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                END
        """)).fetchall()

        stats_data.append(["Concern Level Distribution", ""])
        for level, count in concern_stats:
            percentage = (count/analyzed_articles*100) if analyzed_articles > 0 else 0
            stats_data.append([f"  {level.capitalize()}", f"{count} ({percentage:.1f}%)"])
        stats_data.append(["", ""])

        # Top sources
        source_stats = session.execute(text("""
            SELECT ar.source_domain, COUNT(*) as count
            FROM article_results ar
            JOIN article_analysis aa ON ar.id = aa.result_id
            WHERE aa.error_message IS NULL
            GROUP BY ar.source_domain
            ORDER BY count DESC
            LIMIT 10
        """)).fetchall()

        stats_data.append(["Top Sources", ""])
        for source, count in source_stats:
            stats_data.append([f"  {source}", count])

        df_stats = pd.DataFrame(stats_data, columns=['Metric', 'Value'])
        df_stats.to_excel(writer, sheet_name='Summary', index=False)

        # Apply formatting to Summary sheet
        workbook = writer.book
        worksheet = workbook['Summary']

        # Header formatting
        header_font = Font(bold=True, size=12)
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")

        for cell in worksheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.font = Font(bold=True, color="FFFFFF", size=12)

        # Adjust column widths
        worksheet.column_dimensions['A'].width = 30
        worksheet.column_dimensions['B'].width = 20

    session.close()

    print(f"\n✅ Excel export completed: {output_file}")
    print(f"   📊 Sheets created:")
    print(f"      - Summary: Overall statistics")
    print(f"      - Main Analysis: All analyzed articles with search terms")
    print(f"      - High Priority: Critical and high concern articles with search data")
    print(f"      - Entities: Corporate and government entities with URLs")
    print(f"      - Key Insights: Recurring themes and patterns")
    print(f"      - Human Rights: Human rights issues identified")
    print(f"      - Concern Indicators: Distribution of concern indicators")
    print(f"      - Search Performance: Analysis of search term effectiveness")

    return output_file

if __name__ == "__main__":
    export_articles_to_excel()