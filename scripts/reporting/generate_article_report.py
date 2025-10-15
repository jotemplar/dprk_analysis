#!/usr/bin/env python3
"""Generate comprehensive report on article analysis findings"""

import sys
import os
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, List, Tuple

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from database.connection import get_session
from sqlalchemy import text


class ArticleReportGenerator:
    """Generate comprehensive analysis report for DPRK articles"""

    def __init__(self):
        self.session = get_session()
        self.report_data = {}

    def generate_comprehensive_report(self):
        """Generate full analysis report"""

        print("=" * 80)
        print("DPRK ARTICLE ANALYSIS - COMPREHENSIVE REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 1. Executive Summary
        self._generate_executive_summary()

        # 2. Statistical Overview
        self._generate_statistical_overview()

        # 3. Critical Findings
        self._generate_critical_findings()

        # 4. High Priority Articles
        self._generate_high_priority_articles()

        # 5. Category Analysis
        self._generate_category_analysis()

        # 6. Entity Analysis
        self._generate_entity_analysis()

        # 7. Human Rights Concerns
        self._generate_human_rights_analysis()

        # 8. Geographic Distribution
        self._generate_geographic_distribution()

        # 9. Source Domain Analysis
        self._generate_source_analysis()

        # 10. Export report data
        self._export_report_data()

        return self.report_data

    def _generate_executive_summary(self):
        """Generate executive summary section"""

        # Get key metrics
        stats = self.session.execute(text("""
            SELECT
                COUNT(DISTINCT as_table.id) as total_searches,
                COUNT(DISTINCT ar.id) as total_results,
                COUNT(DISTINCT ac.id) as total_content,
                COUNT(DISTINCT aa.id) as total_analyses,
                COUNT(CASE WHEN aa.concern_level = 'critical' THEN 1 END) as critical_count,
                COUNT(CASE WHEN aa.concern_level = 'high' THEN 1 END) as high_count,
                COUNT(CASE WHEN aa.refugee_mentions = true THEN 1 END) as refugee_mentions,
                COUNT(CASE WHEN array_length(aa.human_rights_issues, 1) > 0 THEN 1 END) as hr_violations
            FROM article_searches as_table
            LEFT JOIN article_results ar ON as_table.id = ar.search_id
            LEFT JOIN article_content ac ON ar.id = ac.result_id
            LEFT JOIN article_analysis aa ON ar.id = aa.result_id
            WHERE aa.error_message IS NULL
        """)).fetchone()

        print("\n" + "=" * 60)
        print("EXECUTIVE SUMMARY")
        print("=" * 60)

        print(f"""
The DPRK Article Analysis Pipeline has completed processing search terms from Pack 3,
analyzing content for sanctions violations, human rights concerns, and other critical
intelligence indicators.

KEY FINDINGS:
• Analyzed {stats.total_analyses} articles from {stats.total_searches} search queries
• Identified {stats.critical_count} CRITICAL and {stats.high_count} HIGH concern articles
• Found {stats.hr_violations} articles with human rights violations
• Detected {stats.refugee_mentions} articles mentioning refugees/defectors
• Success rate: {(stats.total_analyses/stats.total_content*100):.1f}% of scraped content analyzed

IMMEDIATE ATTENTION REQUIRED:
• {stats.critical_count + stats.high_count} articles require immediate review
• Multiple sanctions violations and labor exploitation cases identified
• Significant corporate involvement in potential violations detected
""")

        self.report_data['executive_summary'] = {
            'total_articles': stats.total_analyses,
            'critical_articles': stats.critical_count,
            'high_priority_articles': stats.high_count,
            'human_rights_concerns': stats.hr_violations,
            'refugee_mentions': stats.refugee_mentions
        }

    def _generate_statistical_overview(self):
        """Generate detailed statistics"""

        print("\n" + "=" * 60)
        print("STATISTICAL OVERVIEW")
        print("=" * 60)

        # Processing pipeline statistics
        pipeline_stats = self.session.execute(text("""
            SELECT
                COUNT(DISTINCT as_table.id) as searches,
                COUNT(DISTINCT as_table.category) as categories,
                COUNT(DISTINCT ar.id) as urls_collected,
                COUNT(DISTINCT ac.id) as content_scraped,
                COUNT(CASE WHEN ac.scrape_success = true THEN 1 END) as successful_scrapes,
                COUNT(DISTINCT aa.id) as articles_analyzed,
                AVG(ac.word_count) as avg_word_count,
                AVG(aa.confidence_score) as avg_confidence,
                AVG(aa.processing_time) as avg_processing_time
            FROM article_searches as_table
            LEFT JOIN article_results ar ON as_table.id = ar.search_id
            LEFT JOIN article_content ac ON ar.id = ac.result_id
            LEFT JOIN article_analysis aa ON ar.id = aa.result_id
        """)).fetchone()

        print(f"""
PROCESSING PIPELINE:
• Search Categories: {pipeline_stats.categories}
• Total Searches: {pipeline_stats.searches}
• URLs Collected: {pipeline_stats.urls_collected}
• Content Scraped: {pipeline_stats.successful_scrapes}/{pipeline_stats.content_scraped}
• Articles Analyzed: {pipeline_stats.articles_analyzed}

CONTENT METRICS:
• Average Article Length: {int(pipeline_stats.avg_word_count or 0)} words
• Average Confidence Score: {(pipeline_stats.avg_confidence or 0):.2f}
• Average Processing Time: {(pipeline_stats.avg_processing_time or 0):.1f}s per article
""")

        # Concern level distribution
        concern_dist = self.session.execute(text("""
            SELECT concern_level, COUNT(*) as count
            FROM article_analysis
            WHERE error_message IS NULL
            GROUP BY concern_level
            ORDER BY
                CASE concern_level
                    WHEN 'critical' THEN 4
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    ELSE 1
                END DESC
        """)).fetchall()

        print("\nCONCERN LEVEL DISTRIBUTION:")
        total_analyzed = sum(c.count for c in concern_dist)
        for level, count in concern_dist:
            pct = count/total_analyzed*100 if total_analyzed > 0 else 0
            bar = "█" * int(pct/2)
            print(f"  {level.upper():8s}: {count:3d} ({pct:5.1f}%) {bar}")

        self.report_data['statistics'] = {
            'pipeline': {
                'searches': pipeline_stats.searches,
                'categories': pipeline_stats.categories,
                'urls_collected': pipeline_stats.urls_collected,
                'content_scraped': pipeline_stats.content_scraped,
                'successful_scrapes': pipeline_stats.successful_scrapes,
                'articles_analyzed': pipeline_stats.articles_analyzed,
                'avg_word_count': float(pipeline_stats.avg_word_count or 0),
                'avg_confidence': float(pipeline_stats.avg_confidence or 0),
                'avg_processing_time': float(pipeline_stats.avg_processing_time or 0)
            },
            'concern_distribution': {c.concern_level: c.count for c in concern_dist}
        }

    def _generate_critical_findings(self):
        """Generate critical findings section"""

        print("\n" + "=" * 60)
        print("CRITICAL FINDINGS")
        print("=" * 60)

        # Get critical articles
        critical_articles = self.session.execute(text("""
            SELECT
                ar.title,
                ar.url,
                ar.source_domain,
                aa.summary,
                aa.concern_indicators,
                aa.human_rights_issues,
                aa.corporate_involvement,
                aa.government_entities
            FROM article_analysis aa
            JOIN article_results ar ON aa.result_id = ar.id
            WHERE aa.concern_level = 'critical'
            AND aa.error_message IS NULL
            ORDER BY aa.confidence_score DESC
            LIMIT 10
        """)).fetchall()

        if critical_articles:
            print("\nARTICLES REQUIRING IMMEDIATE ATTENTION:\n")
            for i, article in enumerate(critical_articles, 1):
                print(f"{i}. {article.title[:80]}...")
                print(f"   Source: {article.source_domain}")
                print(f"   Summary: {article.summary[:200]}...")
                if article.concern_indicators:
                    print(f"   Concerns: {', '.join(article.concern_indicators[:3])}")
                if article.human_rights_issues:
                    print(f"   HR Issues: {', '.join(article.human_rights_issues[:3])}")
                if article.corporate_involvement:
                    print(f"   Corporations: {', '.join(article.corporate_involvement[:3])}")
                print()

        self.report_data['critical_findings'] = [
            {
                'title': a.title,
                'url': a.url,
                'source': a.source_domain,
                'summary': a.summary,
                'concerns': a.concern_indicators,
                'hr_issues': a.human_rights_issues,
                'corporations': a.corporate_involvement
            } for a in critical_articles
        ]

    def _generate_high_priority_articles(self):
        """Generate high priority articles section"""

        print("\n" + "=" * 60)
        print("HIGH PRIORITY ARTICLES")
        print("=" * 60)

        # Get high priority articles
        high_priority = self.session.execute(text("""
            SELECT
                ar.title,
                ar.url,
                ar.source_domain,
                aa.summary,
                aa.key_insights,
                aa.confidence_score
            FROM article_analysis aa
            JOIN article_results ar ON aa.result_id = ar.id
            WHERE aa.concern_level = 'high'
            AND aa.error_message IS NULL
            ORDER BY aa.confidence_score DESC
            LIMIT 15
        """)).fetchall()

        if high_priority:
            print("\nSIGNIFICANT DEVELOPMENTS AND VIOLATIONS:\n")
            for i, article in enumerate(high_priority, 1):
                print(f"{i}. {article.title[:80]}...")
                print(f"   Confidence: {article.confidence_score:.2f}")
                print(f"   Source: {article.source_domain}")
                if article.key_insights:
                    print(f"   Key Insights: {article.key_insights[0] if article.key_insights else 'N/A'}")
                print()

        self.report_data['high_priority'] = [
            {
                'title': a.title,
                'url': a.url,
                'source': a.source_domain,
                'summary': a.summary,
                'insights': a.key_insights,
                'confidence': a.confidence_score
            } for a in high_priority
        ]

    def _generate_category_analysis(self):
        """Generate analysis by search category"""

        print("\n" + "=" * 60)
        print("CATEGORY ANALYSIS")
        print("=" * 60)

        category_stats = self.session.execute(text("""
            SELECT
                as_table.category,
                COUNT(DISTINCT ar.id) as articles,
                COUNT(CASE WHEN aa.concern_level IN ('critical', 'high') THEN 1 END) as high_concern,
                COUNT(CASE WHEN aa.refugee_mentions = true THEN 1 END) as refugee_mentions,
                AVG(aa.confidence_score) as avg_confidence
            FROM article_searches as_table
            JOIN article_results ar ON as_table.id = ar.search_id
            JOIN article_analysis aa ON ar.id = aa.result_id
            WHERE aa.error_message IS NULL
            GROUP BY as_table.category
            ORDER BY high_concern DESC
        """)).fetchall()

        print("\nFINDINGS BY SEARCH CATEGORY:\n")
        for cat in category_stats:
            print(f"{cat.category}:")
            print(f"  • Articles: {cat.articles}")
            print(f"  • High Concern: {cat.high_concern}")
            print(f"  • Refugee Mentions: {cat.refugee_mentions}")
            print(f"  • Avg Confidence: {cat.avg_confidence:.2f}")
            print()

        self.report_data['categories'] = [
            {
                'category': c.category,
                'articles': c.articles,
                'high_concern': c.high_concern,
                'refugee_mentions': c.refugee_mentions,
                'avg_confidence': float(c.avg_confidence or 0)
            } for c in category_stats
        ]

    def _generate_entity_analysis(self):
        """Generate entity extraction analysis"""

        print("\n" + "=" * 60)
        print("ENTITY ANALYSIS")
        print("=" * 60)

        # Corporate involvement - filter out non-entities
        corp_query = self.session.execute(text("""
            WITH corps AS (
                SELECT unnest(corporate_involvement) as corporation
                FROM article_analysis
                WHERE corporate_involvement IS NOT NULL
                AND array_length(corporate_involvement, 1) > 0
            )
            SELECT corporation, COUNT(*) as mentions
            FROM corps
            WHERE corporation NOT LIKE '%No specific%'
            AND corporation NOT LIKE '%are mentioned%'
            AND corporation NOT LIKE '%not mentioned%'
            AND corporation NOT LIKE '%None%'
            AND corporation NOT LIKE '%Unspecified%'
            GROUP BY corporation
            ORDER BY mentions DESC
            LIMIT 20
        """)).fetchall()

        if corp_query:
            print("\nTOP CORPORATIONS MENTIONED:")
            for corp, count in corp_query[:10]:
                print(f"  • {corp}: {count} mentions")

        # Government entities - filter out non-entities and consolidate similar names
        gov_query = self.session.execute(text("""
            WITH govs AS (
                SELECT unnest(government_entities) as entity
                FROM article_analysis
                WHERE government_entities IS NOT NULL
                AND array_length(government_entities, 1) > 0
            ),
            normalized AS (
                SELECT
                    CASE
                        -- Russian Government variations
                        WHEN entity ILIKE '%russian government%'
                            OR entity ILIKE '%government of russia%'
                            OR entity ILIKE '%russian federation%'
                            OR entity = 'Russia'
                            OR entity ILIKE '%government of the russian federation%'
                            THEN 'Russian Government'

                        -- North Korean Government variations
                        WHEN entity ILIKE '%north korea%government%'
                            OR entity ILIKE '%government of north korea%'
                            OR entity ILIKE '%dprk%government%'
                            OR entity ILIKE '%government of%dprk%'
                            OR entity ILIKE '%government of the dprk%'
                            OR entity ILIKE '%democratic people%republic of korea%government%'
                            THEN 'North Korean Government'

                        -- Chinese Government variations
                        WHEN entity ILIKE '%chinese government%'
                            OR entity ILIKE '%government of china%'
                            OR entity = 'China'
                            OR entity ILIKE '%chinese%prc%'
                            THEN 'Chinese Government'

                        -- UN variations
                        WHEN entity ILIKE '%united nations%'
                            THEN 'United Nations'

                        -- Russian Ministry of Defense
                        WHEN entity ILIKE '%russian%defense%'
                            OR entity ILIKE '%russian%ministry%defense%'
                            THEN 'Russian Ministry of Defense'

                        -- Chinese Communist Party
                        WHEN entity ILIKE '%chinese communist party%'
                            OR entity ILIKE '%ccp%'
                            THEN 'Chinese Communist Party'

                        -- Kim Jong-un specifically
                        WHEN entity ILIKE '%kim jong%un%'
                            THEN 'Kim Jong-un'

                        ELSE entity
                    END as normalized_entity
                FROM govs
            )
            SELECT normalized_entity as entity, COUNT(*) as mentions
            FROM normalized
            WHERE normalized_entity NOT LIKE '%No specific%'
            AND normalized_entity NOT LIKE '%are mentioned%'
            AND normalized_entity NOT LIKE '%not mentioned%'
            AND normalized_entity NOT LIKE '%None%'
            AND normalized_entity NOT LIKE '%Unspecified%'
            GROUP BY normalized_entity
            ORDER BY mentions DESC
            LIMIT 20
        """)).fetchall()

        if gov_query:
            print("\nTOP GOVERNMENT ENTITIES:")
            for entity, count in gov_query[:10]:
                print(f"  • {entity}: {count} mentions")

        self.report_data['entities'] = {
            'corporations': [{'name': c.corporation, 'mentions': c.mentions} for c in corp_query],
            'government': [{'name': g.entity, 'mentions': g.mentions} for g in gov_query]
        }

    def _generate_human_rights_analysis(self):
        """Generate human rights concerns analysis"""

        print("\n" + "=" * 60)
        print("HUMAN RIGHTS CONCERNS")
        print("=" * 60)

        # Articles with HR issues
        hr_articles = self.session.execute(text("""
            SELECT
                ar.title,
                ar.url,
                aa.human_rights_issues,
                aa.worker_conditions,
                aa.refugee_mentions
            FROM article_analysis aa
            JOIN article_results ar ON aa.result_id = ar.id
            WHERE array_length(aa.human_rights_issues, 1) > 0
            OR aa.worker_conditions IS NOT NULL
            OR aa.refugee_mentions = true
            ORDER BY aa.confidence_score DESC
            LIMIT 20
        """)).fetchall()

        # HR issue types
        hr_types = self.session.execute(text("""
            SELECT unnest(human_rights_issues) as issue, COUNT(*) as count
            FROM article_analysis
            WHERE human_rights_issues IS NOT NULL
            AND array_length(human_rights_issues, 1) > 0
            GROUP BY issue
            ORDER BY count DESC
            LIMIT 15
        """)).fetchall()

        print("\nHUMAN RIGHTS VIOLATION TYPES:")
        for issue, count in hr_types:
            print(f"  • {issue}: {count} occurrences")

        print("\nARTICLES WITH SIGNIFICANT HR CONCERNS:")
        for i, article in enumerate(hr_articles[:10], 1):
            print(f"\n{i}. {article.title[:80]}...")
            if article.human_rights_issues:
                print(f"   Issues: {', '.join(article.human_rights_issues[:3])}")
            if article.worker_conditions:
                print(f"   Worker Conditions: {article.worker_conditions[:100]}...")
            if article.refugee_mentions:
                print(f"   ⚠️  Refugee/Defector content")

        self.report_data['human_rights'] = {
            'violation_types': [{'issue': h.issue, 'count': h.count} for h in hr_types],
            'articles': [
                {
                    'title': a.title,
                    'url': a.url,
                    'issues': a.human_rights_issues,
                    'worker_conditions': a.worker_conditions,
                    'refugee_mentions': a.refugee_mentions
                } for a in hr_articles
            ]
        }

    def _generate_geographic_distribution(self):
        """Generate geographic distribution analysis"""

        print("\n" + "=" * 60)
        print("GEOGRAPHIC DISTRIBUTION")
        print("=" * 60)

        # Source domains by country/region
        domain_stats = self.session.execute(text("""
            SELECT
                ar.source_domain,
                COUNT(*) as articles,
                COUNT(CASE WHEN aa.concern_level IN ('critical', 'high') THEN 1 END) as high_concern
            FROM article_results ar
            JOIN article_analysis aa ON ar.id = aa.result_id
            WHERE aa.error_message IS NULL
            GROUP BY ar.source_domain
            ORDER BY articles DESC
            LIMIT 20
        """)).fetchall()

        print("\nTOP SOURCE DOMAINS:")
        for domain in domain_stats[:15]:
            concern_pct = domain.high_concern/domain.articles*100 if domain.articles > 0 else 0
            print(f"  • {domain.source_domain}: {domain.articles} articles ({concern_pct:.0f}% high concern)")

        self.report_data['geographic'] = [
            {
                'source_domain': d.source_domain,
                'articles': d.articles,
                'high_concern': d.high_concern
            } for d in domain_stats
        ]

    def _generate_source_analysis(self):
        """Generate source credibility analysis"""

        print("\n" + "=" * 60)
        print("SOURCE ANALYSIS")
        print("=" * 60)

        # Language distribution
        lang_stats = self.session.execute(text("""
            SELECT
                aa.original_language,
                COUNT(*) as count,
                AVG(aa.confidence_score) as avg_confidence
            FROM article_analysis aa
            WHERE aa.error_message IS NULL
            AND aa.original_language IS NOT NULL
            GROUP BY aa.original_language
            ORDER BY count DESC
        """)).fetchall()

        print("\nCONTENT BY LANGUAGE:")
        for lang in lang_stats:
            print(f"  • {lang.original_language}: {lang.count} articles (confidence: {lang.avg_confidence:.2f})")

        # Search type distribution
        search_stats = self.session.execute(text("""
            SELECT
                as_table.search_type,
                COUNT(DISTINCT ar.id) as articles,
                COUNT(CASE WHEN aa.concern_level IN ('critical', 'high') THEN 1 END) as high_concern
            FROM article_searches as_table
            JOIN article_results ar ON as_table.id = ar.search_id
            JOIN article_analysis aa ON ar.id = aa.result_id
            WHERE aa.error_message IS NULL
            GROUP BY as_table.search_type
        """)).fetchall()

        print("\nCONTENT BY SEARCH TYPE:")
        for stype in search_stats:
            print(f"  • {stype.search_type}: {stype.articles} articles ({stype.high_concern} high concern)")

        self.report_data['sources'] = {
            'languages': [
                {
                    'original_language': l.original_language,
                    'count': l.count,
                    'avg_confidence': float(l.avg_confidence or 0)
                } for l in lang_stats
            ],
            'search_types': [
                {
                    'search_type': s.search_type,
                    'articles': s.articles,
                    'high_concern': s.high_concern
                } for s in search_stats
            ]
        }

    def _export_report_data(self):
        """Export report data to JSON"""

        output_file = "reports/article_analysis_report.json"
        with open(output_file, 'w') as f:
            json.dump(self.report_data, f, indent=2, default=str)

        print(f"\n📄 Report data exported to: {output_file}")

        # Also generate HTML summary
        self._generate_html_summary()

    def _generate_html_summary(self):
        """Generate HTML summary report"""

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DPRK Article Analysis Report - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .critical {{
            background: #fee;
            border-left: 4px solid #f44;
            padding: 15px;
            margin: 10px 0;
        }}
        .high {{
            background: #ffeaa7;
            border-left: 4px solid #fdcb6e;
            padding: 15px;
            margin: 10px 0;
        }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h2 {{
            color: #2c3e50;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .article-item {{
            padding: 10px;
            border-bottom: 1px solid #eee;
        }}
        .url {{
            color: #667eea;
            text-decoration: none;
            font-size: 0.9em;
        }}
        .concern-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .badge-critical {{ background: #f44; color: white; }}
        .badge-high {{ background: #fdcb6e; color: #333; }}
        .badge-medium {{ background: #74b9ff; color: white; }}
        .badge-low {{ background: #55efc4; color: #333; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 DPRK Article Analysis Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{self.report_data['executive_summary']['total_articles']}</div>
            <div class="stat-label">Total Articles</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{self.report_data['executive_summary']['critical_articles']}</div>
            <div class="stat-label">Critical</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{self.report_data['executive_summary']['high_priority_articles']}</div>
            <div class="stat-label">High Priority</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{self.report_data['executive_summary']['human_rights_concerns']}</div>
            <div class="stat-label">HR Violations</div>
        </div>
    </div>

    <div class="section">
        <h2>🚨 Critical Findings</h2>
        {"".join([f'''
        <div class="critical">
            <strong>{finding['title'][:100]}...</strong><br>
            <span class="concern-badge badge-critical">CRITICAL</span><br>
            <p>{finding['summary'][:200]}...</p>
            <a href="{finding['url']}" class="url" target="_blank">View Article →</a>
        </div>
        ''' for finding in self.report_data.get('critical_findings', [])[:5]])}
    </div>

    <div class="section">
        <h2>⚠️ High Priority Articles</h2>
        {"".join([f'''
        <div class="high">
            <strong>{article['title'][:100]}...</strong><br>
            <span class="concern-badge badge-high">HIGH</span>
            <span style="float:right">Confidence: {article['confidence']:.2f}</span><br>
            <p>{article['summary'][:200] if article['summary'] else 'No summary'}...</p>
            <a href="{article['url']}" class="url" target="_blank">View Article →</a>
        </div>
        ''' for article in self.report_data.get('high_priority', [])[:10]])}
    </div>

    <div class="section">
        <h2>📊 Analysis by Category</h2>
        <table style="width:100%; border-collapse: collapse;">
            <tr>
                <th style="text-align:left; padding:10px; border-bottom:2px solid #667eea;">Category</th>
                <th style="text-align:center; padding:10px; border-bottom:2px solid #667eea;">Articles</th>
                <th style="text-align:center; padding:10px; border-bottom:2px solid #667eea;">High Concern</th>
                <th style="text-align:center; padding:10px; border-bottom:2px solid #667eea;">Confidence</th>
            </tr>
            {"".join([f'''
            <tr>
                <td style="padding:8px; border-bottom:1px solid #eee;">{cat.get('category', 'Unknown')}</td>
                <td style="text-align:center; padding:8px; border-bottom:1px solid #eee;">{cat.get('articles', 0)}</td>
                <td style="text-align:center; padding:8px; border-bottom:1px solid #eee;">{cat.get('high_concern', 0)}</td>
                <td style="text-align:center; padding:8px; border-bottom:1px solid #eee;">{cat.get('avg_confidence', 0):.2f}</td>
            </tr>
            ''' for cat in self.report_data.get('categories', [])])}
        </table>
    </div>

    <div class="section">
        <h2>🏢 Top Entities Mentioned</h2>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
            <div>
                <h3>Corporations</h3>
                <ul>
                {"".join([f"<li>{corp['name']}: {corp['mentions']} mentions</li>"
                         for corp in self.report_data.get('entities', {}).get('corporations', [])[:10]])}
                </ul>
            </div>
            <div>
                <h3>Government Entities</h3>
                <ul>
                {"".join([f"<li>{gov['name']}: {gov['mentions']} mentions</li>"
                         for gov in self.report_data.get('entities', {}).get('government', [])[:10]])}
                </ul>
            </div>
        </div>
    </div>

    <script>
        // Add interactive features if needed
        document.querySelectorAll('.concern-badge').forEach(badge => {{
            badge.style.cursor = 'pointer';
            badge.title = 'Click for details';
        }});
    </script>
</body>
</html>"""

        html_file = "reports/article_analysis_report.html"
        with open(html_file, 'w') as f:
            f.write(html_content)

        print(f"📄 HTML report generated: {html_file}")


def main():
    """Generate comprehensive article analysis report"""

    generator = ArticleReportGenerator()
    try:
        report_data = generator.generate_comprehensive_report()
        print("\n✅ Comprehensive report generation completed!")
        return report_data
    except Exception as e:
        print(f"\n❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
    finally:
        generator.session.close()


if __name__ == "__main__":
    main()