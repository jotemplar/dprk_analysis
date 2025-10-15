# Yandex Search Fix - Implementation Notes

## Problem
Yandex searches were returning 0 results consistently.

## Root Causes Identified

After reviewing the [SERP API Yandex documentation](https://serpapi.com/yandex-search-api), three critical issues were found:

### 1. Wrong Pagination Parameter
**Before**: `"page": page`
**After**: `"p": page`

The Yandex API uses `p` for pagination, not `page`.

### 2. Missing Localization Parameters
**Before**: No location/language parameters
**After**: Added proper Russian localization:
```python
"yandex_domain": "yandex.ru",  # Russian Yandex domain
"lang": "ru",                   # Russian language
"lr": "213"                     # Location ID for Russia (Moscow region)
```

### 3. Wrong Python Class
**Before**: `YandexSearch(params)` (doesn't exist in serpapi-python)
**After**: `GoogleSearch(params)` (works for all engines including Yandex)

## Implementation Changes

### File: `search/serp_russia_client.py`

**Import Statement**:
```python
# Before
from serpapi import GoogleSearch, YandexSearch

# After
from serpapi import GoogleSearch
```

**Search Parameters**:
```python
# Before
params = {
    "api_key": self.api_key,
    "engine": "yandex",
    "text": query,
    "page": page  # WRONG
}

# After
params = {
    "api_key": self.api_key,
    "engine": "yandex",
    "text": query,
    "p": page,                  # CORRECT pagination
    "yandex_domain": "yandex.ru",  # Russian domain
    "lang": "ru",                   # Russian language
    "lr": "213"                     # Russia location (Moscow)
}
```

**Search Execution**:
```python
# Before
search = YandexSearch(params)  # Class doesn't exist

# After
search = GoogleSearch(params)  # Correct class for all engines
```

## Verification Results

### Test Query: Simple Russian Word
```python
query = "кофе"  # Coffee in Russian
results = client.search_yandex(query, num_results=3)
```

**Result**: ✅ 3 results returned
- a-kofe.ru
- taberacoffee.ru
- shop.tastycoffee.ru

### Test Query: Complex Site-Specific Search
```python
query = 'site:hh.ru "рабочие из КНДР" стройка Приморский край'
results = client.search_yandex(query, num_results=5)
```

**Result**: ✅ 5 results returned from various hh.ru subdomains

### Full Pipeline Test (3 Queries)
```bash
./run_russian_pipeline.sh search --csv test_3queries.csv --num-results 5
```

**Results**:
- Query 1 (site:hh.ru): ✅ 5 results
- Query 2 (site:superjob.ru): ✅ 5 results
- Query 3 (site:rabota.ru): ✅ 5 results

**Total**: 15/15 results successfully stored in database

## Key Insights from SERP API Documentation

### Yandex Location IDs
- `213` = Moscow region (Russia)
- `84` = United States (default for yandex.com)
- Full list: https://serpapi.com/yandex-locations

### Yandex Domains
- `yandex.ru` = Russian domain (best for Russian content)
- `yandex.com` = International domain
- Full list: https://serpapi.com/yandex-domains

### Yandex Languages
- `ru` = Russian
- `en` = English
- Can use multiple: `ru,en` for mixed results
- Full list: https://serpapi.com/yandex-languages

### Pagination
- Parameter: `p` (not `page`)
- Starts at 0
- Returns ~10 results per page
- Example: `p=0` (page 1), `p=1` (page 2), etc.

## Additional Improvements Made

### Debug Output
Added status logging to help diagnose issues:
```python
if "search_metadata" in results:
    print(f"    Status: {results['search_metadata'].get('status', 'Unknown')}")
```

### Error Handling
Added traceback printing for better debugging:
```python
except Exception as e:
    print(f"Error searching Yandex: {e}")
    import traceback
    traceback.print_exc()
    return []
```

## Performance Notes

### Rate Limiting
- Default: 400 requests/minute
- Current delay: 2 seconds between queries
- Configurable via `--delay` parameter

### Results Per Query
- Default: 10 results
- Tested with 5 results successfully
- Configurable via `--num-results` parameter

## Recommendations for Full Run

### Optimal Settings
```bash
./run_russian_pipeline.sh search \
  --csv dprk_osint_queries_with_social_and_portals_v1_3.csv \
  --num-results 10 \
  --delay 2.0
```

**Expected Results** for 755 queries:
- Execution time: 25-40 minutes
- Total results: ~7,550 (10 per query average)
- Success rate: Should be near 100% with proper queries

### Monitoring
```bash
# In separate terminal
watch -n 10 "./run_russian_pipeline.sh status"
```

## Troubleshooting

### If Still Getting 0 Results

1. **Check API Key**: Verify SERP_API_KEY in `.env`
2. **Check API Quota**: Visit https://serpapi.com/dashboard
3. **Test Simple Query**: Try searching for a common Russian word
4. **Check Response**: Look for error messages in search metadata

### Common Issues

**Issue**: All queries return 0 results
**Solution**: Verify API key and quota

**Issue**: Some queries return 0 results
**Solution**: Normal - some specific queries may have no matches

**Issue**: Rate limiting errors
**Solution**: Increase `--delay` parameter

## Testing Commands

### Test Single Query
```bash
PYTHONPATH=/Volumes/X5/_CODE_PROJECTS/DPRK python -c "
from search.serp_russia_client import SerpRussiaClient
client = SerpRussiaClient()
results = client.search_yandex('кофе', num_results=5)
print(f'Found {len(results)} results')
"
```

### Test CSV Processing
```bash
./run_russian_pipeline.sh search \
  --csv test_3queries.csv \
  --num-results 5 \
  --delay 1
```

### Check Results
```bash
./run_russian_pipeline.sh status
```

## Files Modified

1. **search/serp_russia_client.py**
   - Fixed import statement
   - Updated Yandex parameters
   - Changed to GoogleSearch class
   - Added debug output

## Status: ✅ FIXED AND TESTED

Yandex searches are now fully functional and ready for production use with the full 755-query dataset.
