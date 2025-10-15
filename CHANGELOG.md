# Changelog

All notable changes to the DPRK Research and Analysis System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2025-01-15

### Changed - Major Codebase Reorganization
- **Restructured entire codebase** for better organization and maintainability
- Consolidated root directory from **132 files to 15 core files**
- Moved 100+ files to logical directories:
  - 36 reports → `reports/`
  - 7 search term files → `search_terms/`
  - 8 test files → `tests/`
  - 30+ scripts → `scripts/` (organized by pipeline type)
  - 7 log files → `logs/`
  - 12 documentation files → `docs/`

### Added
- New folder structure with clear separation of concerns:
  - `reports/` - All generated reports (HTML, XLSX, JSON)
  - `search_terms/` - All search term definitions and CSV files
  - `tests/` - All test scripts
  - `scripts/image/` - Image pipeline processing scripts
  - `scripts/article/` - Article pipeline processing scripts
  - `scripts/russian/` - Russian OSINT processing scripts
  - `scripts/reporting/` - Export and reporting scripts
  - `scripts/dashboard/` - Dashboard generation scripts
  - `logs/` - All log files
  - `docs/` - Documentation files

### Fixed
- Updated all import statements to reflect new folder structure
- Updated shell scripts (`run.sh`, `run_russian_pipeline.sh`) with correct paths
- Updated default output paths in export scripts to write to `reports/` folder
- Updated `search_terms/dprk_images_search_terms_combined.py` to use new import paths

### Updated
- README.md with new project structure and updated command examples
- All Python scripts with correct import paths
- Database connection paths remain unchanged (no breaking changes)

## [3.1.0] - 2025-01-10

### Added - Russian OSINT Pipeline
- New Russian search pipeline using Yandex and Google Russia engines
- CSV-based query processing (755 queries from `dprk_osint_queries_with_social_and_portals_v1_3.csv`)
- Dual search engine support with engine hint column
- Full attribution export with all CSV metadata columns
- Interactive HTML dashboard for Russian search results
- Database schema for Russian searches with engine and location tracking

### Enhanced
- Excel exports now include complete search term attribution
- HTML reports with engine breakdown (Yandex vs Google Russia)
- Theme-based result organization
- Comprehensive summary statistics per search

## [3.0.0] - 2025-01-05

### Added - Article Analysis Pipeline
- Complete text article processing pipeline (Pack 3)
- 58 specialized article search queries across 7 categories
- High-performance content scraping with Firecrawl (50 concurrent scrapers)
- AI-powered article analysis using Gemma3:12b
- Multilingual article support (English, Russian, Korean, Chinese)
- Article analysis database schema (`article_searches`, `article_results`, `article_content`, `article_analysis`)
- Comprehensive Excel exports with search term attribution
- Interactive HTML dashboards combining article and image analysis
- Entity extraction and consolidation (corporations and government entities)

### Enhanced
- Advanced entity deduplication for government names
- Concern level distribution analysis
- Human rights violation tracking
- Geographic distribution analysis by source domain
- Category-based performance metrics
- Processing time and confidence score tracking

## [2.5.0] - 2024-12-20

### Added - Ensemble Analysis
- Dual-model ensemble analysis combining LLaVA and Gemma3:12b
- Parallel processing with 4 concurrent AI analysis threads
- Image standardization to 896x896 for optimal model performance
- Ensemble confidence scoring
- Comprehensive Excel export with multiple analysis sheets

### Enhanced
- Theme-based search organization
- Deduplication system for images
- Batch processing improvements
- Storage optimization

## [2.0.0] - 2024-12-01

### Added - Themed Search Terms
- Pack 2 themed exploitation search terms
- 5 specialized themes: construction_exploitation, dorms_living, handlers_oversight, community_mistreatment, financial_exploitation
- Combined search terms file merging Pack 1 and Pack 2
- Theme tracking in database

### Enhanced
- Search query metadata with theme information
- Improved deduplication logic
- Enhanced reporting with theme breakdowns

## [1.5.0] - 2024-11-15

### Added
- Screenshot capture functionality using Playwright
- Gallery view screenshots for search results
- Screenshot database tracking
- Automated browser management

### Enhanced
- Image download error handling
- Storage organization by date
- Metadata extraction improvements

## [1.0.0] - 2024-11-01

### Added - Initial Release
- Core image search and capture system
- PostgreSQL database integration
- Ollama local LLM integration (LLaVA model)
- SERP API integration for Google Image Search
- Multilingual search support (English, Russian, Korean, Chinese, French)
- 104 comprehensive search terms (Pack 1)
- Image metadata extraction (EXIF, GPS)
- Basic AI analysis for humanitarian concerns
- Command-line interface with convenience scripts

### Database Schema
- `search_queries` - Search term storage
- `search_results` - URL collection
- `captured_images` - Image metadata
- `screenshots` - Screenshot tracking
- `content_analysis` - AI analysis results
- `search_sessions` - Session tracking

### Features
- Batch image download with concurrency control
- Rate limiting for API calls
- Error handling and retry logic
- Storage management
- Basic reporting

---

## Version History Summary

- **v3.2.0**: Major codebase reorganization (Current)
- **v3.1.0**: Russian OSINT pipeline with Yandex/Google Russia
- **v3.0.0**: Article analysis pipeline (Pack 3)
- **v2.5.0**: Ensemble analysis with dual models
- **v2.0.0**: Themed search terms (Pack 2)
- **v1.5.0**: Screenshot capture functionality
- **v1.0.0**: Initial release with image search and analysis

## Upgrade Notes

### Upgrading to 3.2.0
No database changes required. All file reorganization is backward compatible.

**Action Required:**
1. Update any external scripts that reference old file paths
2. Use new command examples from README.md
3. All reports will now be saved to `reports/` folder by default

**Import Path Changes:**
- `from dprk_images_search_terms import` → `from search_terms.dprk_images_search_terms import`
- Scripts moved to `scripts/` subdirectories must be called with new paths

### Upgrading to 3.1.0
Requires new database tables for Russian searches.

**Action Required:**
1. Run `python database/create_russian_tables.py` to create new tables
2. Place CSV file in project root
3. Update `.env` with SERP API key if needed

### Upgrading to 3.0.0
Requires new database tables for article analysis.

**Action Required:**
1. Run database migration to add article tables
2. Install Firecrawl: `uv pip install firecrawl-py`
3. Add `FIRECRAWL_API_KEY` to `.env`
4. Pull Gemma3:12b model: `ollama pull gemma3:12b`

## Future Roadmap

- [ ] Advanced timeline visualization for worker tracking
- [ ] Network analysis of corporate entities
- [ ] Multi-language translation pipeline
- [ ] Enhanced geolocation extraction
- [ ] API endpoint for external integrations
- [ ] Docker containerization
- [ ] Automated testing suite expansion
