# DPRK Research and Analysis System

A comprehensive system for searching, capturing, and analyzing both **images** and **text content** related to North Korean workers and military personnel in Russia, designed for human rights documentation and research purposes.

**Latest Update (v3.1.0)**: Enhanced reporting with comprehensive Excel exports including search term attribution, interactive HTML dashboards combining article and image analysis, and advanced entity consolidation with government/corporate deduplication. Complete article analysis pipeline now processes 381 articles with 68 high-priority findings identified.

## 🚀 Quick Command Reference

```bash
# First-time setup (one command)
./setup.sh

# Daily operations
./run.sh test    # Test with 2 queries (~2 min)
./run.sh full    # Full pipeline (~30-60 min)
./run.sh basic   # System health check

# Enhanced Analysis Pipeline (Image Processing)
python process_missing_llava_parallel.py     # Process images missing LLaVA analysis
python process_all_gemma12b_parallel.py      # Process all images with Gemma3:12b
python apply_ensemble_analysis.py            # Apply ensemble combining both models
python export_to_spreadsheet.py              # Export comprehensive analysis results

# Text Article Processing Pipeline
python main_article_pipeline.py --status     # Check current article processing status
python main_article_pipeline.py --full       # Run complete article pipeline (search→scrape→analyze)
python process_article_searches.py           # Execute search terms from pack 3 (58 queries)
python process_article_content.py            # Scrape article content (50 concurrent scrapers)
python process_article_analysis.py           # Analyze articles with Gemma3:12b

# Reporting and Export
python generate_article_report.py            # Generate HTML/JSON analysis reports
python export_articles_to_excel.py           # Export articles with search term attribution
python serve_dashboard.py                    # Launch interactive dashboard server

# Key maintenance
uv run --no-project python init_database.py  # Reset database
ollama serve                                  # Start LLM service
psql -U postgres -d dprk                      # Database access
du -sh captured_data/                         # Check storage
```

## Overview

This system automates the process of:
- **Image Pipeline**: Searching, capturing, downloading, and analyzing images using multilingual search terms
- **Text Pipeline**: Searching for articles, scraping content, and analyzing text using AI models
- Capturing screenshots of search results for visual context
- Downloading and storing images with comprehensive metadata
- Analyzing both images and text using local LLM for sensitive content
- Storing all results in a PostgreSQL database for research and reporting

## Features

### Image Analysis Pipeline
- **Multilingual Search**: Supports 104 image search terms in English, Russian, Korean, Chinese, and French
- **Themed Search Terms**: Organized by exploitation themes (construction, dorms, handlers, community, financial)
- **Image Capture**: Downloads images and captures screenshots of search results
- **Ensemble AI Analysis**: Combines multiple models (LLaVA + Gemma3:12b) for higher accuracy
- **Parallel Processing**: 4 concurrent AI analysis threads for faster processing
- **Image Standardization**: Automatic resizing to 896x896 for optimal model performance
- **Metadata Extraction**: Extracts EXIF data, GPS coordinates, and other metadata

### Text Article Pipeline (New!)
- **Article Search**: 58 specialized text search queries across 7 categories
- **High-Performance Scraping**: 50 concurrent Firecrawl scrapers for optimal throughput
- **Content Extraction**: Markdown and HTML content with metadata
- **AI Text Analysis**: Gemma3:12b analysis for DPRK relevance and concern levels
- **Multilingual Support**: English, Russian, Korean, and Chinese text processing
- **Site-Specific Targeting**: VK, Telegram, forums, and government sites

### Shared Infrastructure
- **Humanitarian Focus**: Specialized prompts for detecting exploitation and poor conditions
- **Local Analysis**: Uses Ollama for sensitive content analysis to avoid cloud filtering
- **Database Storage**: PostgreSQL database with comprehensive schema for all data
- **Batch Processing**: Concurrent downloads and efficient pipeline processing
- **Privacy-Focused**: Local LLM analysis for sensitive content
- **Comprehensive Export**: Excel spreadsheets with multiple analysis sheets

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Ollama (for local LLM)
- Chrome/Chromium (for Playwright)

### Setup

1. **Clone the repository**:
```bash
cd /Volumes/X5/_CODE_PROJECTS/DPRK
```

2. **Install Python dependencies**:
```bash
uv pip install -r requirements.txt
uv run playwright install chromium
```

3. **Set up Ollama**:
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve

# Pull required models
ollama pull llava
ollama pull gemma3:12b     # For ensemble analysis
ollama pull gemma3n:e4b    # Optional, for comparison
```

4. **Configure environment**:
- Copy `.env.example` to `.env` (already done)
- Update API keys and database credentials in `.env`

5. **Initialize database**:
```bash
python init_database.py
```

## Quick Start Commands

### Essential Setup (One-time)
```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run automated setup (creates venv, installs deps, initializes DB)
./setup.sh

# Or manual setup:
uv venv                                  # Create virtual environment
uv pip install -r requirements.txt      # Install Python dependencies
uv run playwright install chromium       # Install browser for screenshots
uv run --no-project python init_database.py  # Initialize database
```

### Daily Usage Commands
```bash
# Using the convenient run script:
./run.sh basic   # Test system components
./run.sh test    # Run pipeline with 2 test queries (~2 min)
./run.sh full    # Run full pipeline - ALL queries (~30-60 min)
./run.sh init    # Reset/reinitialize database

# Direct commands with uv:
uv run --no-project python test_basic.py     # System health check
uv run --no-project python main.py test      # Test mode (2 queries)
uv run --no-project python main.py           # Full pipeline
```

### Database Commands
```bash
# Initialize/reset database with search terms
uv run --no-project python init_database.py

# PostgreSQL direct access
psql -U postgres -d dprk                     # Connect to database
psql -U postgres -d dprk -c "SELECT COUNT(*) FROM search_queries;"
psql -U postgres -d dprk -c "SELECT COUNT(*) FROM captured_images;"

# Backup database
pg_dump -U postgres dprk > dprk_backup_$(date +%Y%m%d).sql

# Restore database
psql -U postgres -d dprk < dprk_backup_20250119.sql
```

### Ollama Commands (Local LLM)
```bash
# Start Ollama service
ollama serve

# Check Ollama status
curl http://localhost:11434/api/tags

# Pull required model (if not installed)
ollama pull llava

# List installed models
ollama list
```

### Monitoring & Maintenance
```bash
# Check system status
./run.sh basic

# View captured images
ls -la captured_data/images/$(date +%Y-%m-%d)/

# View screenshots
ls -la captured_data/screenshots/$(date +%Y-%m-%d)/

# Check logs
tail -f logs/pipeline_$(date +%Y%m%d).log

# Disk usage
du -sh captured_data/

# Clean old data (30+ days)
find captured_data/ -type f -mtime +30 -delete
```

## Project Structure

```
DPRK/
├── capture/               # Screenshot and image capture modules
│   ├── screenshot_capture.py
│   └── image_downloader.py
├── database/             # Database models and connection
│   ├── models.py         # Image analysis database models
│   ├── article_models.py # Article analysis database models (New!)
│   └── connection.py
├── search/               # Search API clients
│   ├── serp_image_client.py  # Image search client
│   └── serp_web_client.py    # Web/article search client (New!)
├── utils/                # Utility modules
│   └── ollama_analyzer.py
├── captured_data/        # Storage for captured content
│   ├── images/
│   └── screenshots/
├── dprk_images_search_terms.py    # Image search terms (pack 1)
├── dprk_images_search_terms_2.py  # Image search terms (pack 2)
├── dprk_images_search_terms_3.py  # Article search terms (pack 3) (New!)
├── process_article_searches.py    # Article search processor (New!)
├── process_article_content.py     # Article content scraper (New!)
├── process_article_analysis.py    # Article content analyzer (New!)
├── main_article_pipeline.py       # Article pipeline orchestrator (New!)
├── init_database.py      # Database initialization
├── main.py              # Main image pipeline
├── .env                 # Configuration (not in git)
├── DESIGN_DOCUMENT.md   # System design
├── README.md            # This file
└── CHANGELOG.md         # Version history
```

## Database Schema

### Image Analysis Tables
- `search_queries`: Search terms and categories
- `search_results`: URLs from image searches
- `captured_images`: Downloaded image metadata
- `screenshots`: Screenshot metadata
- `content_analysis`: LLM analysis results for images
- `search_sessions`: Session tracking

### Article Analysis Tables (New!)
- `article_searches`: Article search terms and metadata
- `article_results`: URLs from article searches
- `article_content`: Scraped article content (markdown/HTML)
- `article_analysis`: AI analysis results for articles

## API Services

- **SERP API**: Google image and web search
- **Firecrawl**: High-performance web scraping (50 concurrent scrapers)
- **Jina AI**: Backup content extraction
- **Ollama**: Local LLM for analysis (LLaVA for images, Gemma3:12b for text)

## Configuration

### Environment Variables
- `DB_NAME`: PostgreSQL database name (default: dprk)
- `OLLAMA_HOST`: Ollama server URL
- `OLLAMA_MODEL`: Model for analysis (default: llava)
- `IMAGE_STORAGE_PATH`: Path for image storage
- `SCREENSHOT_STORAGE_PATH`: Path for screenshots
- `SEARCH_RATE_LIMIT`: API rate limit
- `CONCURRENT_SCRAPERS`: Parallel download threads
- `FIRECRAWL_API_KEY`: Firecrawl API key for article scraping

## Search Categories

### Image Search Categories (Packs 1 & 2)
1. **Region**: Far East, Kursk, Vladivostok, Siberia
2. **Labour Type**: Construction, mining, industrial
3. **Military**: Soldiers, officers, supervision
4. **Community**: Students, migrants
5. **Hybrid**: Workers with guards/supervisors

### Article Search Categories (Pack 3) - New!
1. **Refugees_Communities**: Community and refugee situations
2. **Phones_Chinese_Forums**: Phone seizures and forum discussions
3. **Locating_Workers_Region**: Geographic worker location searches
4. **Abuse_Exploitation_Asylum**: Abuse and exploitation cases
5. **Groups_to_Check**: Specific organizations and groups
6. **Hiring_DPRK_Workers**: Employment and hiring practices
7. **Corporate_Warehouse_Cases**: Corporate and warehouse investigations

## Privacy & Ethics

This system is designed for:
- Human rights documentation
- Academic research
- Journalistic investigation
- NGO reporting

**NOT** for:
- Commercial exploitation
- Privacy violation
- Harmful surveillance
- Discriminatory profiling

## Troubleshooting Commands

### System Diagnostics
```bash
# Full system check
./run.sh basic

# Check Python environment
uv pip list | grep -E "sqlalchemy|playwright|ollama|PIL"

# Verify environment variables
grep -E "SERP_API|DB_NAME|OLLAMA" .env

# Test database connection
uv run --no-project python -c "from database.connection import get_session; s=get_session(); print('✓ DB OK')"
```

### Ollama Issues
```bash
# Check if running
curl -s http://localhost:11434/api/tags || echo "Ollama not running"

# Start Ollama
ollama serve &

# Restart Ollama
pkill ollama && sleep 2 && ollama serve &

# Check for llava model
ollama list | grep llava || ollama pull llava

# Test image analysis capability
echo "Testing Ollama..." | ollama run llava "What do you see?"
```

### Database Issues
```bash
# Check PostgreSQL status
pg_ctl status || brew services list | grep postgresql

# Start PostgreSQL
brew services start postgresql

# Restart PostgreSQL
brew services restart postgresql

# Reset database completely
dropdb dprk 2>/dev/null; createdb dprk
uv run --no-project python init_database.py

# Check table counts
psql -U postgres -d dprk -c "\dt"
```

### API/Network Issues
```bash
# Test SERP API
uv run --no-project python -c "from search.serp_image_client import SerpImageClient; c=SerpImageClient(); print('✓ SERP OK' if c.api_key else '✗ No API key')"

# Test network connectivity
curl -I https://google.com

# Check rate limit status
grep RATE_LIMIT .env

# Reset failed downloads
psql -U postgres -d dprk -c "UPDATE search_results SET image_download_status='pending' WHERE image_download_status='failed';"
```

### Storage Issues
```bash
# Check disk space
df -h captured_data/

# Find large files
find captured_data/ -type f -size +10M -ls

# Clean temporary files
find captured_data/ -name "*.tmp" -delete

# Archive old data
tar -czf captured_data_$(date +%Y%m%d).tar.gz captured_data/
```

### Common Error Fixes
```bash
# "Module not found" error
uv pip install -r requirements.txt

# "Playwright browser not found"
uv run playwright install chromium

# "Database does not exist"
createdb dprk
uv run --no-project python init_database.py

# "Ollama model not found"
ollama pull llava

# "Permission denied" errors
chmod +x run.sh setup.sh
```

## Performance

### Image Pipeline
- Processes ~104 image search queries
- Downloads 10-20 images per query
- Analyzes 5 images per query with LLM
- Total runtime: ~30-60 minutes for full dataset

### Article Pipeline (New!)
- Processes 58 article search queries across 7 categories
- Collects ~50 results per query (~2,900 URLs total)
- Scrapes content with 50 concurrent Firecrawl requests
- Analyzes articles with Gemma3:12b for DPRK relevance
- Optimized for high-throughput processing

## Storage

- Images: ~50-100MB per session
- Screenshots: ~20-50MB per session
- Database: ~10MB for metadata

## Contributing

This is a sensitive research project. Please ensure:
1. Respect privacy and human rights
2. Follow ethical guidelines
3. Document findings responsibly
4. Protect sensitive data

## License

For research and human rights documentation only.

## Support

For issues or questions:
- Check DESIGN_DOCUMENT.md for technical details
- Review CHANGELOG.md for recent changes
- Consult logs in the `logs/` directory

## Disclaimer

This system is for legitimate research and human rights documentation only. Users are responsible for compliance with applicable laws and ethical guidelines.