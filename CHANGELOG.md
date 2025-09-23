# CHANGELOG

All notable changes to the DPRK Image Capture and Analysis System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-19

### Added

#### Core Infrastructure
- Created comprehensive design document outlining system architecture
- Set up PostgreSQL database 'dprk' with complete schema
- Configured environment variables and API credentials
- Established directory structure for organized data storage

#### Database Schema
- `search_queries` table for multilingual search terms
- `search_results` table for search result URLs
- `captured_images` table for downloaded image metadata
- `screenshots` table for screenshot metadata
- `content_analysis` table for LLM analysis results
- `search_sessions` table for session tracking
- `image_metadata` table for additional image information

#### Search Functionality
- Implemented `SerpImageClient` for Google Image searches
- Support for 100+ multilingual search terms (English, Russian, Korean, Chinese, French)
- Category-based search organization (region, labour, military, community, hybrid)
- Rate limiting and retry logic for API calls
- Both image and web search capabilities

#### Capture Modules
- `ScreenshotCapture` class using Playwright for web screenshots
- Gallery view generation for multiple images
- Batch screenshot capability with concurrency control
- Full page and viewport screenshot options

#### Image Download System
- `ImageDownloader` class for async image downloads
- EXIF data extraction including GPS coordinates
- Image format conversion (WebP to PNG)
- Batch download with concurrent processing
- File size and format validation

#### Analysis System
- `OllamaAnalyzer` class for local LLM integration
- Support for llava model for image analysis
- Structured analysis output with categories:
  - Scene description
  - Personnel identification
  - Activity analysis
  - Concern level assessment
  - Supervision indicators
- Confidence scoring for analysis results

#### Main Pipeline
- Complete end-to-end pipeline implementation
- Search → Capture → Download → Analyze → Store workflow
- Session management and progress tracking
- Test mode for limited query processing
- Comprehensive error handling and logging

#### Documentation
- Detailed README with installation and usage instructions
- Design document with architecture and strategy
- Changelog for version tracking

### Configuration
- API keys for SERP, Jina, Firecrawl services
- Ollama configuration for local LLM
- Database connection settings
- Storage paths for images and screenshots
- Rate limiting and timeout settings

### Security
- Local LLM processing for sensitive content
- No cloud-based analysis for privacy
- Secure credential storage in .env file

## [2.0.0] - 2025-01-21

### Added

#### Humanitarian Research Framework
- Created PROJECT_OBJECTIVES.md defining humanitarian research goals
- Focus on documenting evidence of poor conditions and potential exploitation
- Specialized AI prompts for detecting humanitarian concerns

#### Enhanced Search Capabilities
- Integrated 57 additional themed search terms from dprk_images_search_terms_2.py
- Total of 104 search terms organized by exploitation themes:
  - Construction workers and sites
  - Dormitory and living conditions
  - Handlers and supervision
  - Community and social aspects
  - Financial and economic indicators
- Implemented deduplication to preserve existing images while adding new ones

#### Multi-Model Ensemble Analysis
- Added Gemma3n:e4b model support for humanitarian perspective analysis
- Upgraded to Gemma3:12b for improved accuracy
- Created ensemble analysis combining LLaVA + Gemma outputs
- Confidence scoring based on model agreement
- Priority scoring for human review of concerning cases

#### Database Enhancements
- Added Gemma analysis fields (gemma_description, gemma_concern_level, gemma_indicators)
- Added Gemma3:12b comparison fields for model evaluation
- Added ensemble fields (ensemble_concern_level, ensemble_confidence, ensemble_indicators)
- Extended ContentAnalysis model with humanitarian-focused fields

#### Parallel Processing Infrastructure
- Created ParallelLLaVAProcessor for 4 concurrent analysis threads
- Created ParallelGemma12bProcessor for efficient batch processing
- Implemented asyncio with semaphore for controlled concurrency
- Progress tracking with ETA calculations

#### Image Preprocessing
- Created ImagePreprocessor utility for standardization
- Automatic resizing to 896x896 pixels (optimal for both models)
- Aspect ratio preservation using LANCZOS resampling
- Caching system for preprocessed images
- Support for various image formats (JPEG, PNG, WebP conversion)

#### New Processing Scripts
- process_missing_llava_parallel.py - Process images missing primary analysis
- process_all_gemma12b_parallel.py - Process all images with Gemma3:12b
- apply_ensemble_analysis.py - Combine analyses from multiple models
- generate_model_comparison.py - Create detailed model comparison reports
- process_missing_gemma.py - Sequential processing for Gemma3n:e4b

#### Export and Reporting
- Enhanced export_to_spreadsheet.py with multiple analysis sheets:
  - Summary statistics
  - Full analysis results
  - High concern cases
  - Search performance metrics
  - Theme analysis breakdown
- Model comparison report generator with:
  - Agreement matrices
  - Performance metrics
  - Disagreement case analysis
  - Model tendency analysis

### Changed
- Modified OllamaAnalyzer to accept model parameter for flexibility
- Updated prompts to align with humanitarian objectives
- Fixed database field references (search_query→search_term, source_type→search_type)
- Optimized image processing pipeline for parallel execution

### Fixed
- Resolved missing field errors (color_mode, capture_method, capture_status)
- Fixed OllamaAnalyzer model parameter handling
- Corrected SQL query field references in export scripts
- Fixed CapturedImage model field mismatches

## [3.0.0] - 2025-01-22

### Added

#### Complete Text Article Processing Pipeline
- **New Database Schema**: Created comprehensive article processing tables
  - `article_searches`: Search terms and metadata storage
  - `article_results`: Search result URLs with source domain tracking
  - `article_content`: Scraped content in markdown and HTML formats
  - `article_analysis`: AI analysis results with DPRK relevance scoring

#### Search Terms Pack 3 Implementation
- **58 specialized search queries** across 7 thematic categories:
  - Refugees_Communities (8 queries)
  - Phones_Chinese_Forums (10 queries)
  - Locating_Workers_Region (8 queries)
  - Abuse_Exploitation_Asylum (10 queries)
  - Groups_to_Check (8 queries)
  - Hiring_DPRK_Workers (8 queries)
  - Corporate_Warehouse_Cases (8 queries)
- **Multilingual support**: English, Russian, Korean, and Chinese queries
- **Site-specific targeting**: VK, Telegram, forums, government sites
- **Language detection and categorization** for search terms

#### High-Performance Content Scraping
- **Firecrawl Integration**: Optimized for 50 concurrent scrapers
- **Connection pooling**: TCPConnector with 60 total/50 per-host limits
- **Async processing**: Eliminated rate limiting delays for maximum throughput
- **Content extraction**: Markdown and HTML with metadata preservation
- **Progress tracking**: Real-time ETA calculations for large batches
- **Error handling**: Comprehensive failure tracking and retry logic

#### AI-Powered Article Analysis
- **Gemma3:12b integration**: Structured text analysis for DPRK content
- **Concern level assessment**: Low/Medium/High/Critical classification
- **DPRK relevance scoring**: None/Low/Medium/High relevance detection
- **Entity extraction**: Key entities, themes, and geographic references
- **Violation detection**: Potential sanctions violations identification
- **Credibility assessment**: Source reliability evaluation
- **Action indicators**: Actionable intelligence flagging

#### Pipeline Orchestration
- **main_article_pipeline.py**: Complete workflow automation
- **Phase-based execution**: Search → Scrape → Analyze workflow
- **Individual phase control**: Run specific phases independently
- **Comprehensive monitoring**: Real-time status tracking and reporting
- **Flexible configuration**: Customizable limits and batch sizes
- **Performance metrics**: Throughput and success rate monitoring

#### Article Processing Scripts
- **process_article_searches.py**: Execute search terms with SERP API
- **process_article_content.py**: High-performance content scraping
- **process_article_analysis.py**: AI-powered content analysis
- **Database initialization**: Automatic table creation and setup

### Enhanced

#### Performance Optimizations
- **50x concurrent scraping**: Leveraging Firecrawl's full capacity
- **Eliminated artificial delays**: Removed unnecessary rate limiting
- **Connection reuse**: Optimized HTTP session management
- **Progress visualization**: Enhanced progress tracking for large datasets
- **Batch processing**: Efficient handling of ~2,900 article URLs

#### Documentation Updates
- **README.md**: Comprehensive article pipeline documentation
- **Command examples**: Updated with article processing commands
- **Architecture diagrams**: Expanded project structure documentation
- **Performance metrics**: Added article pipeline performance data
- **Search categories**: Documented all 7 article search categories

### Configuration
- **FIRECRAWL_API_KEY**: New environment variable for content scraping
- **Optimized defaults**: 50 concurrent scrapers, efficient batch sizes
- **Database integration**: Seamless PostgreSQL integration for all pipelines

## [3.1.0] - 2025-01-22

### Added

#### Comprehensive Reporting and Analytics
- **Enhanced Excel Export System**: Complete redesign with search term tracking
  - Search category and term columns in all sheets
  - URLs included for direct article verification
  - Search performance analysis sheet showing term effectiveness
  - Entity consolidation for cleaner government/corporate tracking

- **Interactive Dashboards**: Multi-source analysis visualization
  - `dprk_comprehensive_dashboard.html`: Combined article and image analysis
  - Tabbed interface for Articles and Images
  - Real-time filtering and search capabilities
  - Concern level distribution charts
  - Entity frequency tracking with search source attribution

- **Report Generation**: Comprehensive HTML and JSON reports
  - `generate_article_report.py`: Full article analysis reporting
  - Entity extraction with deduplication
  - Confidence score normalization (0-1 range)
  - Government entity consolidation (183 variations → clean categories)
  - Human rights issues tracking

#### Data Quality Improvements
- **Entity Consolidation**: Advanced SQL-based entity normalization
  - Russian Government variations (183 mentions consolidated)
  - North Korean Government variations (168 mentions)
  - Chinese Government, UN, and US Government standardization
  - Removal of AI placeholder text ("No specific companies mentioned")

- **Confidence Score Fixes**: Normalized outlier scores
  - Fixed scores >1.0 (75→0.75, 65→0.65, 2→0.02, 1→0.01)
  - Consistent probability scale across all analyses

- **Search Term Attribution**: Complete traceability
  - Every article linked to originating search term
  - Search category performance metrics
  - Identification of most effective search strategies

#### Dashboard Infrastructure
- **Web Server**: Local HTTP server for dashboard access
  - `serve_dashboard.py`: CORS-enabled local server
  - Automatic browser launch on startup
  - JSON data loading for dynamic content

### Enhanced

#### Excel Export Capabilities
- **8 Comprehensive Sheets**:
  1. Summary: Overall statistics with concern distribution
  2. Main Analysis: 376 articles with search terms and URLs
  3. High Priority: 68 critical/high concern articles with sources
  4. Entities: Corporations and governments with article URLs
  5. Key Insights: Recurring themes across articles
  6. Human Rights: Identified issues with frequencies
  7. Concern Indicators: Distribution across severity levels
  8. Search Performance: Search term effectiveness analysis

#### Article Processing Pipeline
- **Complete Analysis Coverage**: 381/381 articles processed
  - 376 successfully analyzed with Gemma3:12b
  - 68 high-priority articles identified (critical + high concern)
  - 3 critical, 65 high, 167 medium, 141 low concern levels

### Fixed
- **SQL Query Issues**: Resolved aggregation and timezone errors
  - Fixed string_agg with DISTINCT and ORDER BY
  - Removed timezone from datetime columns for Excel compatibility
  - Corrected HAVING clause usage in CTEs

- **Dashboard Loading**: Fixed CORS issues for local file access
  - Implemented proper HTTP server for JSON loading
  - Fixed image thumbnail display in grid view

## [Unreleased]

### Planned Features
- **Unified dashboard**: Combined image and article analysis visualization
- **Cross-pipeline correlation**: Link related images and articles
- **Advanced export**: Combined Excel reports with both pipelines
- **Web interface**: Browsing both images and articles
- **Enhanced search**: Cross-dataset filtering and correlation
- **Automated scheduling**: Periodic pipeline execution
- **Alert system**: High-priority content notifications
- **Data visualization**: Interactive charts and graphs
- **Duplicate detection**: Cross-pipeline duplicate identification

### Known Issues
- Ollama must be running before pipeline execution
- Some images may fail to download due to access restrictions
- Large images (>50MB) are skipped
- GPS extraction limited to images with EXIF data

## Development Notes

### Dependencies
- Python 3.12+
- PostgreSQL 14+
- Ollama with llava model
- Playwright with Chromium
- Key Python packages:
  - SQLAlchemy 2.0+
  - aiohttp
  - Pillow
  - playwright
  - ollama-python
  - python-dotenv
  - serpapi

### Testing
Run test mode with limited queries:
```bash
python main.py test
```

### Database Reset
To reset and reinitialize:
```bash
python init_database.py
```

---

For questions or issues, refer to the README.md and DESIGN_DOCUMENT.md files.