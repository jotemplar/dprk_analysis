# Russian OSINT Search Pipeline

A specialized search pipeline for DPRK-related OSINT using Yandex and Google Russia search engines. Processes queries from CSV files and generates comprehensive Excel and HTML reports.

## Overview

This pipeline enables:
- **Yandex Search**: Native Russian search engine with better coverage of Russian sites
- **Google Russia**: Google search localized to Russia with Russian language preference
- **Sequential Processing**: Processes all queries from CSV in sequence
- **Database Storage**: Stores all results in PostgreSQL with full metadata
- **Excel Export**: Comprehensive spreadsheet with search term attribution
- **HTML Reports**: Interactive dashboard for result visualization

## Features

- **Dual Engine Support**: Yandex and Google Russia search engines
- **Engine Selection**: CSV-based engine hints for per-query engine selection
- **Top 10 Results**: Configurable result count (default 10 per query)
- **Source Attribution**: Complete search metadata in exports
- **Resume Capability**: Skip already completed queries
- **Rate Limiting**: Configurable delays between queries
- **Error Handling**: Retry logic with exponential backoff

## Database Schema

### Tables Created

1. **russian_searches**: Search query metadata
   - query_id, language, engine, location
   - theme, sector, region, time_filter, site
   - query_text, search_status, results_count

2. **russian_search_results**: Search results
   - position, url, title, snippet
   - source_domain, published_date
   - scrape_status, analysis_status

3. **russian_search_content**: Scraped content (optional)
   - raw_html, markdown_content, cleaned_text
   - word_count, language, author

## CSV Format

The CSV file must have these columns:

```csv
id,language,engine_hint,theme,sector,region,time_filter,site,query
ru_construction_00001,ru,Yandex,portal_slice,стройка,Приморский край,2023..2025,hh.ru,"site:hh.ru ""рабочие из КНДР"" стройка Приморский край"
ru_construction_00002,ru,Google,portal_slice,стройка,Приморский край,2023..2025,superjob.ru,"КНДР рабочие стройка"
```

### Column Descriptions

- **id**: Unique query identifier
- **language**: Language code (ru, en, etc.)
- **engine_hint**: Search engine to use (Yandex or Google)
- **theme**: Query theme/category
- **sector**: Industry sector
- **region**: Geographic region
- **time_filter**: Time range filter
- **site**: Target website (if any)
- **query**: The actual search query

## Setup

### 1. Create Database Tables

```bash
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python database/create_russian_tables.py
```

This creates three new tables in the `dprk` database:
- russian_searches
- russian_search_results
- russian_search_content

### 2. Verify Environment

Ensure `.env` file contains:
```
SERP_API_KEY=your_serp_api_key
DB_NAME=dprk
SEARCH_RATE_LIMIT=400
```

## Usage

### Process All Queries

Run searches for all queries in the CSV:

```bash
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python process_russian_searches.py \
  --csv dprk_osint_queries_with_social_and_portals_v1_3.csv \
  --num-results 10 \
  --delay 2.0
```

**Parameters:**
- `--csv`: Path to CSV file (default: dprk_osint_queries_with_social_and_portals_v1_3.csv)
- `--num-results`: Number of results per query (default: 10)
- `--delay`: Delay between queries in seconds (default: 2.0)
- `--no-resume`: Process all queries, don't skip completed ones

### Resume After Interruption

The script automatically resumes and skips completed queries:

```bash
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python process_russian_searches.py
```

### Force Reprocess All

To reprocess all queries (ignore completion status):

```bash
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python process_russian_searches.py --no-resume
```

### Export to Excel

Generate comprehensive Excel report with all results:

```bash
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python export_russian_searches_to_excel.py \
  --output russian_results_$(date +%Y%m%d).xlsx
```

**Excel Output Includes:**
- Summary sheet with statistics
- Search Results sheet with:
  - Query ID, Engine, Location, Language
  - Theme, Sector, Region, Time Filter
  - Site, Query Text
  - Position, URL (as hyperlink), Title, Snippet
  - Source Domain, Published Date, Searched At

### Generate HTML Report

Create interactive HTML dashboard:

```bash
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python generate_russian_search_report.py \
  --output russian_report_$(date +%Y%m%d).html
```

**HTML Report Includes:**
- Statistics dashboard with metrics
- Engine breakdown (Yandex vs Google)
- Theme analysis
- Recent results with metadata
- Interactive styling with hover effects

## CSV File Details

The provided CSV contains **755 queries** organized by:
- **Themes**: portal_slice, etc.
- **Sectors**: Construction (стройка), etc.
- **Regions**: Приморский край, etc.
- **Sites**: hh.ru, superjob.ru, rabota.ru, etc.

### Query Distribution

The queries target:
- Job portals (hh.ru, superjob.ru, zarplata.ru)
- Classified sites (avito.ru)
- Construction sites (stroyka.ru)
- Other specialized portals

## Example Workflow

### Complete Pipeline Run

```bash
# 1. Create database tables (first time only)
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python database/create_russian_tables.py

# 2. Process all searches
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python process_russian_searches.py \
  --csv dprk_osint_queries_with_social_and_portals_v1_3.csv \
  --num-results 10 \
  --delay 2.0

# 3. Export to Excel
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python export_russian_searches_to_excel.py

# 4. Generate HTML report
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python generate_russian_search_report.py

# 5. Open report in browser
open russian_osint_report_*.html
```

### Test Run (2 Queries)

```bash
# Create test CSV
cat > test_queries.csv << 'EOF'
id,language,engine_hint,theme,sector,region,time_filter,site,query
test_001,ru,Yandex,test,стройка,Приморский край,2023..2025,hh.ru,"КНДР рабочие"
test_002,ru,Google,test,стройка,Приморский край,2023..2025,superjob.ru,"северокорейские рабочие"
EOF

# Run test
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python process_russian_searches.py \
  --csv test_queries.csv \
  --num-results 5 \
  --delay 1

# Export test results
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python export_russian_searches_to_excel.py \
  --output test_results.xlsx

PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python generate_russian_search_report.py \
  --output test_report.html
```

## Performance Estimates

With the full CSV (755 queries):
- **Search Time**: ~30-40 minutes (2 second delay between queries)
- **Results Expected**: 7,550 results (assuming 10 per query)
- **API Calls**: 755 calls (one per query)
- **Database Size**: ~5-10 MB for metadata
- **Excel File Size**: ~2-5 MB
- **HTML Report**: ~1-2 MB

## Database Queries

### Check Progress

```sql
-- Overall statistics
SELECT
  COUNT(*) as total_queries,
  SUM(CASE WHEN search_status = 'completed' THEN 1 ELSE 0 END) as completed,
  SUM(CASE WHEN search_status = 'pending' THEN 1 ELSE 0 END) as pending,
  SUM(results_count) as total_results
FROM russian_searches;

-- Engine breakdown
SELECT
  engine,
  COUNT(*) as queries,
  SUM(results_count) as results,
  AVG(results_count) as avg_per_query
FROM russian_searches
GROUP BY engine;

-- Theme breakdown
SELECT
  theme,
  COUNT(*) as queries,
  SUM(results_count) as results
FROM russian_searches
GROUP BY theme
ORDER BY results DESC;
```

### View Recent Results

```sql
SELECT
  rs.query_id,
  rs.query_text,
  rs.engine,
  rsr.position,
  rsr.title,
  rsr.url,
  rsr.source_domain
FROM russian_search_results rsr
JOIN russian_searches rs ON rsr.search_id = rs.id
ORDER BY rs.searched_at DESC, rsr.position
LIMIT 20;
```

### Reset Specific Query

```sql
-- Reset a single query to reprocess it
UPDATE russian_searches
SET search_status = 'pending', results_count = 0
WHERE query_id = 'ru_construction_00001';

-- Delete its results
DELETE FROM russian_search_results
WHERE search_id IN (
  SELECT id FROM russian_searches WHERE query_id = 'ru_construction_00001'
);
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'database'`:

```bash
# Always use PYTHONPATH
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python script.py
```

### SERP API Issues

If searches fail:
1. Check API key in `.env`
2. Verify rate limit setting
3. Check SERP API dashboard for quota
4. Try with longer `--delay` (e.g., 3.0 seconds)

### Empty Results

If getting 0 results:
- Some queries may genuinely have no results
- Yandex may have stricter filtering
- Try Google engine as alternative
- Verify query syntax is correct

### Database Connection

If database errors occur:

```bash
# Test connection
psql -U postgres -d dprk -c "SELECT COUNT(*) FROM russian_searches;"

# Recreate tables if needed
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python database/create_russian_tables.py
```

## Files Created

### Source Files
- `database/russian_search_models.py` - Database models
- `database/create_russian_tables.py` - Table creation script
- `search/serp_russia_client.py` - SERP API client for Yandex/Google Russia
- `process_russian_searches.py` - Main search processing script
- `export_russian_searches_to_excel.py` - Excel export script
- `generate_russian_search_report.py` - HTML report generator

### Output Files
- `russian_osint_results_YYYYMMDD_HHMMSS.xlsx` - Excel report
- `russian_osint_report_YYYYMMDD_HHMMSS.html` - HTML dashboard

## Integration with Existing System

This pipeline integrates with the existing DPRK OSINT system:
- Uses same database (`dprk`)
- Uses same connection module
- Uses same environment variables
- Compatible with existing article/image pipelines
- Follows same naming conventions

## Next Steps

After running searches, you can:
1. **Scrape Content**: Add content scraping for results
2. **AI Analysis**: Analyze scraped content with LLM
3. **Entity Extraction**: Extract organizations, locations, people
4. **Dashboard**: Create unified dashboard with image/article data
5. **Monitoring**: Set up regular scheduled searches

## Support

For issues:
1. Check DESIGN_DOCUMENT.md for system architecture
2. Check README.md for general setup
3. Verify database connection with `psql -U postgres -d dprk`
4. Check SERP API quota at https://serpapi.com/dashboard

## Credits

Part of the DPRK Research and Analysis System
- Database: PostgreSQL
- Search API: SERP API (Yandex + Google Russia)
- Export: OpenPyXL
- Reports: HTML/CSS with responsive design
