# Russian OSINT Search - Quick Commands

## Setup (One-Time)

```bash
# Create database tables
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python database/create_russian_tables.py
```

## Full Production Run

```bash
# Process all 755 queries from CSV
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python process_russian_searches.py \
  --csv dprk_osint_queries_with_social_and_portals_v1_3.csv \
  --num-results 10 \
  --delay 2.0

# Export to Excel
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python export_russian_searches_to_excel.py

# Generate HTML report
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python generate_russian_search_report.py

# Open report
open russian_osint_report_*.html
```

## Quick Test (2 Queries)

```bash
# Use test CSV
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python process_russian_searches.py \
  --csv test_russian_queries.csv \
  --num-results 5 \
  --delay 1

# Export test results
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python export_russian_searches_to_excel.py \
  --output test_results.xlsx

# Generate test report
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python generate_russian_search_report.py \
  --output test_report.html

# Open test report
open test_report.html
```

## Common Operations

### Resume After Interruption
```bash
# Automatically skips completed queries
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python process_russian_searches.py
```

### Force Reprocess All
```bash
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python process_russian_searches.py --no-resume
```

### Custom Output Names
```bash
# Export with custom filename
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python export_russian_searches_to_excel.py \
  --output my_results.xlsx

# Report with custom filename
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python generate_russian_search_report.py \
  --output my_report.html
```

### Process Subset of Queries
```bash
# Create custom CSV with specific queries
head -100 dprk_osint_queries_with_social_and_portals_v1_3.csv > first_100.csv

# Process only those
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python process_russian_searches.py \
  --csv first_100.csv
```

## Database Queries

### Check Progress
```bash
psql -U postgres -d dprk -c "
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN search_status = 'completed' THEN 1 ELSE 0 END) as done,
  SUM(results_count) as results
FROM russian_searches;"
```

### View Results
```bash
psql -U postgres -d dprk -c "
SELECT query_id, engine, results_count, searched_at
FROM russian_searches
WHERE search_status = 'completed'
ORDER BY searched_at DESC
LIMIT 10;"
```

### Reset Single Query
```bash
psql -U postgres -d dprk -c "
UPDATE russian_searches
SET search_status = 'pending', results_count = 0
WHERE query_id = 'ru_construction_00001';"
```

### Reset All
```bash
psql -U postgres -d dprk -c "
TRUNCATE TABLE russian_search_results CASCADE;
TRUNCATE TABLE russian_searches CASCADE;"
```

## Monitoring Progress

### Watch Progress Live
```bash
watch -n 5 "psql -U postgres -d dprk -t -c \"
SELECT
  CONCAT(
    'Progress: ',
    SUM(CASE WHEN search_status = 'completed' THEN 1 ELSE 0 END),
    '/',
    COUNT(*),
    ' queries | ',
    SUM(results_count),
    ' results'
  )
FROM russian_searches;\""
```

### Check Last 5 Searches
```bash
psql -U postgres -d dprk -c "
SELECT
  query_id,
  engine,
  results_count,
  TO_CHAR(searched_at, 'HH24:MI:SS') as time
FROM russian_searches
WHERE searched_at IS NOT NULL
ORDER BY searched_at DESC
LIMIT 5;"
```

## Typical Workflow

```bash
# 1. Setup (first time only)
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python database/create_russian_tables.py

# 2. Run searches (can take 30-40 minutes for full set)
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python process_russian_searches.py

# 3. Check progress while running (in another terminal)
watch -n 10 "psql -U postgres -d dprk -t -c 'SELECT COUNT(*) FROM russian_searches WHERE search_status = \"completed\"'"

# 4. After completion, generate reports
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python export_russian_searches_to_excel.py
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python generate_russian_search_report.py

# 5. Open reports
open russian_osint_results_*.xlsx
open russian_osint_report_*.html
```

## Environment Variables

Required in `.env`:
```
SERP_API_KEY=your_api_key_here
DB_NAME=dprk
DB_USER=postgres
DB_PASSWORD=your_password
SEARCH_RATE_LIMIT=400
```

## File Sizes (Estimates)

For full 755-query run:
- Excel file: ~2-5 MB
- HTML report: ~1-2 MB
- Database storage: ~5-10 MB

## Performance

- **Search Rate**: ~30 queries per minute (with 2s delay)
- **Total Time**: ~25-40 minutes for 755 queries
- **Expected Results**: ~7,550 (assuming 10 per query)
- **API Calls**: 755 total

## Troubleshooting

### Script Won't Run
```bash
# Always use PYTHONPATH
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python script.py
```

### Database Connection Failed
```bash
# Test connection
psql -U postgres -d dprk -c "SELECT 1;"

# Verify .env settings
grep "DB_" .env
```

### Empty Results
```bash
# Check SERP API key
grep SERP_API_KEY .env

# Try with longer delay
python process_russian_searches.py --delay 3.0
```

## Quick Tips

1. **Resume is automatic** - Script skips completed queries by default
2. **Use --no-resume** only if you want to reprocess everything
3. **Monitor in separate terminal** while searches run
4. **Increase --delay** if hitting rate limits
5. **Excel export** works even if searches are incomplete
6. **HTML report** shows current state of database
