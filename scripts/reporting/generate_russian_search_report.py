"""Generate HTML report for Russian OSINT search results"""

import os
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session, joinedload
from database.connection import get_session
from database.russian_search_models import RussianSearch, RussianSearchResult


def fetch_report_data(session: Session) -> Dict:
    """
    Fetch data for report generation

    Args:
        session: Database session

    Returns:
        Dictionary with report data
    """
    # Get all searches with results
    searches = session.query(RussianSearch).options(
        joinedload(RussianSearch.results)
    ).order_by(RussianSearch.query_id).all()

    # Calculate statistics
    total_queries = len(searches)
    completed_queries = sum(1 for s in searches if s.search_status == 'completed')
    total_results = sum(s.results_count for s in searches)

    yandex_queries = sum(1 for s in searches if s.engine == 'yandex')
    google_queries = sum(1 for s in searches if s.engine == 'google')

    # Group by theme
    themes = {}
    for search in searches:
        theme = search.theme or 'Unknown'
        if theme not in themes:
            themes[theme] = {
                'count': 0,
                'results': 0,
                'searches': []
            }
        themes[theme]['count'] += 1
        themes[theme]['results'] += search.results_count
        themes[theme]['searches'].append(search)

    # Group by engine
    engines = {
        'yandex': {'count': yandex_queries, 'results': 0},
        'google': {'count': google_queries, 'results': 0}
    }

    for search in searches:
        engines[search.engine]['results'] += search.results_count

    return {
        'total_queries': total_queries,
        'completed_queries': completed_queries,
        'total_results': total_results,
        'yandex_queries': yandex_queries,
        'google_queries': google_queries,
        'themes': themes,
        'engines': engines,
        'searches': searches,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def generate_html_report(data: Dict, output_path: str):
    """
    Generate HTML report

    Args:
        data: Report data dictionary
        output_path: Path to save HTML file
    """
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Russian OSINT Search Results Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}

        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}

        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
        }}

        .stat-card h3 {{
            color: #7f8c8d;
            font-size: 0.9em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}

        .stat-card .number {{
            font-size: 3em;
            font-weight: 700;
            color: #2c3e50;
            margin: 10px 0;
        }}

        .stat-card.primary .number {{
            color: #3498db;
        }}

        .stat-card.success .number {{
            color: #2ecc71;
        }}

        .stat-card.warning .number {{
            color: #f39c12;
        }}

        .stat-card.info .number {{
            color: #9b59b6;
        }}

        .content {{
            padding: 40px;
        }}

        .section {{
            margin-bottom: 40px;
        }}

        .section h2 {{
            font-size: 1.8em;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
        }}

        .theme-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
        }}

        .theme-card h3 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}

        .theme-stats {{
            display: flex;
            gap: 20px;
            margin-top: 10px;
            color: #7f8c8d;
        }}

        .theme-stats span {{
            font-weight: 600;
        }}

        .results-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            overflow: hidden;
        }}

        .results-table thead {{
            background: #2c3e50;
            color: white;
        }}

        .results-table th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .results-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}

        .results-table tbody tr:hover {{
            background: #f8f9fa;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .badge.yandex {{
            background: #ff4444;
            color: white;
        }}

        .badge.google {{
            background: #4285f4;
            color: white;
        }}

        .badge.completed {{
            background: #2ecc71;
            color: white;
        }}

        .badge.pending {{
            background: #f39c12;
            color: white;
        }}

        .badge.failed {{
            background: #e74c3c;
            color: white;
        }}

        .result-item {{
            background: white;
            border: 1px solid #ecf0f1;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }}

        .result-item h4 {{
            color: #2c3e50;
            margin-bottom: 8px;
        }}

        .result-item a {{
            color: #3498db;
            text-decoration: none;
            font-size: 0.9em;
            word-break: break-all;
        }}

        .result-item a:hover {{
            text-decoration: underline;
        }}

        .result-snippet {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 8px;
            line-height: 1.5;
        }}

        .result-meta {{
            display: flex;
            gap: 15px;
            margin-top: 10px;
            font-size: 0.85em;
            color: #95a5a6;
        }}

        .footer {{
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 0.9em;
        }}

        .search-details {{
            background: #ecf0f1;
            padding: 10px 15px;
            border-radius: 6px;
            margin: 10px 0;
            font-size: 0.9em;
        }}

        .search-details strong {{
            color: #2c3e50;
        }}

        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}

            .theme-stats {{
                flex-direction: column;
                gap: 10px;
            }}

            .results-table {{
                font-size: 0.85em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Russian OSINT Search Results</h1>
            <p>Yandex and Google Russia Search Analysis</p>
            <p style="margin-top: 10px; font-size: 0.9em;">Generated: {data['generated_at']}</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card primary">
                <h3>Total Queries</h3>
                <div class="number">{data['total_queries']}</div>
            </div>
            <div class="stat-card success">
                <h3>Completed</h3>
                <div class="number">{data['completed_queries']}</div>
            </div>
            <div class="stat-card warning">
                <h3>Total Results</h3>
                <div class="number">{data['total_results']}</div>
            </div>
            <div class="stat-card info">
                <h3>Avg per Query</h3>
                <div class="number">{data['total_results'] / max(data['completed_queries'], 1):.1f}</div>
            </div>
        </div>

        <div class="content">
            <div class="section">
                <h2>Search Engines</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                    <div class="theme-card">
                        <h3><span class="badge yandex">Yandex</span></h3>
                        <div class="theme-stats">
                            <div>Queries: <span>{data['engines']['yandex']['count']}</span></div>
                            <div>Results: <span>{data['engines']['yandex']['results']}</span></div>
                        </div>
                    </div>
                    <div class="theme-card">
                        <h3><span class="badge google">Google Russia</span></h3>
                        <div class="theme-stats">
                            <div>Queries: <span>{data['engines']['google']['count']}</span></div>
                            <div>Results: <span>{data['engines']['google']['results']}</span></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>Themes Breakdown</h2>
"""

    # Add theme cards
    for theme, theme_data in sorted(data['themes'].items(), key=lambda x: x[1]['results'], reverse=True):
        html += f"""
                <div class="theme-card">
                    <h3>{theme}</h3>
                    <div class="theme-stats">
                        <div>Queries: <span>{theme_data['count']}</span></div>
                        <div>Results: <span>{theme_data['results']}</span></div>
                        <div>Avg: <span>{theme_data['results'] / max(theme_data['count'], 1):.1f}</span></div>
                    </div>
                </div>
"""

    html += """
            </div>

            <div class="section">
                <h2>Recent Results</h2>
"""

    # Add recent results (limit to first 50)
    result_count = 0
    max_results_to_show = 50

    for search in data['searches']:
        if search.results_count > 0 and result_count < max_results_to_show:
            html += f"""
                <div style="margin-bottom: 30px;">
                    <div class="search-details">
                        <strong>Query:</strong> {search.query_text}<br>
                        <strong>ID:</strong> {search.query_id} |
                        <strong>Engine:</strong> <span class="badge {search.engine}">{search.engine}</span> |
                        <strong>Theme:</strong> {search.theme} |
                        <strong>Sector:</strong> {search.sector} |
                        <strong>Region:</strong> {search.region}
                    </div>
"""

            for result in search.results[:5]:  # Show top 5 results per query
                if result_count >= max_results_to_show:
                    break

                html += f"""
                    <div class="result-item">
                        <h4>{result.title or 'No title'}</h4>
                        <a href="{result.url}" target="_blank">{result.url[:100]}{'...' if len(result.url) > 100 else ''}</a>
                        {f'<div class="result-snippet">{result.snippet}</div>' if result.snippet else ''}
                        <div class="result-meta">
                            <div>Position: #{result.position}</div>
                            <div>Domain: {result.source_domain}</div>
                        </div>
                    </div>
"""
                result_count += 1

            html += "</div>"

    if result_count >= max_results_to_show:
        html += f"""
                <div style="text-align: center; padding: 20px; color: #7f8c8d;">
                    <p>Showing first {max_results_to_show} results. See Excel export for complete data.</p>
                </div>
"""

    html += """
            </div>
        </div>

        <div class="footer">
            <p>DPRK OSINT Research Project - Russian Search Analysis</p>
            <p style="margin-top: 5px; opacity: 0.8;">For complete results, see the Excel export file</p>
        </div>
    </div>
</body>
</html>
"""

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML report saved to: {output_path}")


def generate_report(output_filename: str = None):
    """
    Main report generation function

    Args:
        output_filename: Custom output filename (optional)
    """
    session = get_session()

    try:
        print("Fetching data from database...")
        data = fetch_report_data(session)

        if data['total_queries'] == 0:
            print("No data found in database")
            return

        print(f"Found {data['total_queries']} queries with {data['total_results']} results")

        # Generate output filename
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"reports/russian_osint_report_{timestamp}.html"

        # Generate HTML report
        print("Generating HTML report...")
        generate_html_report(data, output_filename)

        print(f"\nReport generated successfully!")
        print(f"Open in browser: file://{os.path.abspath(output_filename)}")

    finally:
        session.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate HTML report for Russian OSINT searches')
    parser.add_argument('--output', type=str, help='Output filename')

    args = parser.parse_args()

    generate_report(args.output)


if __name__ == '__main__':
    main()
