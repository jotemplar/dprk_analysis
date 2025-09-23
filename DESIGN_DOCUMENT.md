# DPRK Image Capture System Design Document

## Project Overview
A system for capturing and analyzing images related to North Korean workers and military personnel in Russia, with focus on documenting potential human rights concerns. This system is adapted from the BURUNDI codebase with modifications specific to DPRK-related content.

## Objectives
1. Search for images using multilingual search terms (English, Russian, Korean, Chinese, French)
2. Capture screenshots of search results and image URLs
3. Download and store images with metadata
4. Perform sensitive content analysis using local LLM (to avoid cloud content filtering)
5. Maintain searchable database of findings

## System Architecture

### Components

#### 1. Database Layer (PostgreSQL)
- **Database Name**: `dprk`
- **Key Tables**:
  - `search_queries`: Store search terms and execution history
  - `search_results`: Store URLs from search results
  - `captured_images`: Store image metadata and file paths
  - `screenshots`: Store screenshot metadata and paths
  - `content_analysis`: Store LLM analysis results
  - `search_sessions`: Track search sessions and progress

#### 2. Search Module
- **Primary API**: SERP API (Google Images)
- **Fallback**: Direct web scraping with Firecrawl
- **Search Categories**:
  - Regional locations (Far East, Kursk, Vladivostok, Siberia)
  - Labor types (construction, mining, industrial)
  - Military/supervision contexts
  - Community/educational contexts
  - Hybrid scenarios (workers with supervisors/guards)

#### 3. Capture Module
- **Screenshot Tool**: Playwright browser automation
- **Image Downloader**: aiohttp with retry logic
- **Storage Structure**:
  ```
  /captured_data/
    /screenshots/
      /YYYY-MM-DD/
        /{search_term_hash}/
    /images/
      /YYYY-MM-DD/
        /{category}/
  ```

#### 4. Analysis Module
- **Local LLM**: Ollama with mistral-nemo:12b
- **Analysis Categories**:
  - Scene context identification
  - Personnel identification (workers/military/supervisors)
  - Environmental conditions assessment
  - Activity type classification
  - Potential concern indicators

#### 5. Reporting Module
- HTML dashboard with React components
- Excel export functionality
- Statistical summaries
- Image galleries with metadata

## Data Flow

1. **Search Execution**
   - Load search terms from `dprk_images_search_terms.py`
   - Execute searches via SERP API
   - Store results in database

2. **Content Capture**
   - Screenshot search result pages
   - Extract image URLs
   - Download images with metadata
   - Store file paths in database

3. **Analysis Pipeline**
   - Process images through local LLM
   - Extract contextual information
   - Flag potential areas of concern
   - Store analysis results

4. **Reporting**
   - Generate daily summaries
   - Create searchable archive
   - Export findings for documentation

## Security & Privacy Considerations

1. **Local Processing**: Use Ollama for sensitive content analysis
2. **Data Storage**: Encrypted local storage for captured images
3. **Access Control**: Database credentials in .env file
4. **Content Filtering**: Avoid triggering cloud API content filters
5. **Ethical Guidelines**: Focus on documentation for human rights purposes

## Technical Stack

### Core Technologies
- Python 3.12+
- PostgreSQL with pgvector
- Ollama (local LLM)
- Playwright (browser automation)
- Flask (web interface)

### Key Libraries
- `asyncio` & `aiohttp`: Async operations
- `psycopg2` / `SQLAlchemy`: Database operations
- `Pillow`: Image processing
- `pandas`: Data manipulation
- `python-dotenv`: Configuration management

## Search Strategy

### Multilingual Approach
1. **English**: Standard terminology with quotes for exact phrases
2. **Russian**: Cyrillic terms with regional specifics
3. **Korean**: Hangul script for direct sources
4. **Chinese**: Simplified characters for regional coverage
5. **French**: For international documentation

### Search Modifiers
- Date ranges: 2021-2025
- Location specifiers: Russia, Far East, specific cities
- Context terms: workers, soldiers, construction, supervision
- Visual indicators: photo, image, фото, 사진, 图片

## Error Handling

1. **API Rate Limits**: Exponential backoff with jitter
2. **Network Failures**: Retry with fallback services
3. **Content Blocks**: Switch to alternative search terms
4. **Storage Issues**: Queue system for failed downloads
5. **Analysis Failures**: Manual review queue

## Monitoring & Logging

1. **Search Performance**: Success rates, API usage
2. **Capture Statistics**: Images/screenshots per session
3. **Analysis Metrics**: Processing time, classification accuracy
4. **Error Tracking**: Failed operations log
5. **Audit Trail**: All database operations logged

## Development Phases

### Phase 1: Infrastructure Setup
- Database creation and schema
- Environment configuration
- Directory structure

### Phase 2: Search Implementation
- SERP API integration
- Search term processing
- Result storage

### Phase 3: Capture System
- Screenshot functionality
- Image download pipeline
- Metadata extraction

### Phase 4: Analysis Integration
- Ollama setup
- Analysis pipeline
- Result classification

### Phase 5: Reporting & UI
- Dashboard creation
- Export functionality
- Search interface

## Success Metrics

1. **Coverage**: Number of unique images captured
2. **Quality**: Resolution and relevance of images
3. **Analysis Accuracy**: Correct classification rate
4. **Performance**: Processing speed per image
5. **Documentation**: Completeness of metadata

## Risk Mitigation

1. **Content Sensitivity**: Local processing only
2. **Legal Compliance**: Focus on publicly available content
3. **Data Protection**: Secure storage and access
4. **Ethical Use**: Clear documentation of purpose
5. **Technical Failures**: Comprehensive backup strategies

## Maintenance Plan

1. **Daily**: Monitor capture pipeline
2. **Weekly**: Review analysis accuracy
3. **Monthly**: Database optimization
4. **Quarterly**: Search term updates
5. **As Needed**: API/service updates

## Dependencies on BURUNDI Codebase

### Reusable Components:
- Database connection utilities
- API client wrappers
- Image processing functions
- Report generation templates
- Error handling patterns

### Modifications Required:
- Search terms and categories
- Analysis prompts for DPRK context
- Storage path configurations
- Report templates customization
- LLM prompts for sensitive content

## Compliance & Ethics

This system is designed for:
- Human rights documentation
- Academic research
- Journalistic investigation
- NGO reporting

NOT for:
- Commercial exploitation
- Privacy violation
- Harmful surveillance
- Discriminatory profiling

---

**Document Version**: 1.0.0
**Created**: 2025-01-19
**Author**: System Design Team
**Status**: Active Development