"""SQLAlchemy models for article/text content analysis"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, ARRAY, UniqueConstraint, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from database.models import Base

class ArticleSearch(Base):
    """Store text/article search queries"""
    __tablename__ = 'article_searches'

    id = Column(Integer, primary_key=True)
    category = Column(String(100))  # refugees, phones, workers, abuse, groups, hiring
    search_term = Column(Text, unique=True, nullable=False)
    language = Column(String(10), default='en')  # en, ru, ko, zh
    search_type = Column(String(20), default='web')  # web, news, site-specific
    site_filter = Column(String(255))  # e.g., vk.com, t.me, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    results = relationship("ArticleResult", back_populates="search", cascade="all, delete-orphan")


class ArticleResult(Base):
    """Store article search results from SERP API"""
    __tablename__ = 'article_results'

    id = Column(Integer, primary_key=True)
    search_id = Column(Integer, ForeignKey('article_searches.id'), nullable=False)
    url = Column(Text, nullable=False)
    title = Column(Text)
    snippet = Column(Text)
    position = Column(Integer)
    source_domain = Column(String(255))
    published_date = Column(DateTime)

    # Processing status
    scrape_status = Column(String(20), default='pending')  # pending, completed, failed
    analysis_status = Column(String(20), default='pending')  # pending, completed, failed

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    search = relationship("ArticleSearch", back_populates="results")
    content = relationship("ArticleContent", back_populates="result", uselist=False, cascade="all, delete-orphan")
    analysis = relationship("ArticleAnalysis", back_populates="result", uselist=False, cascade="all, delete-orphan")

    # Unique constraint
    __table_args__ = (UniqueConstraint('search_id', 'url', name='_search_url_uc'),)


class ArticleContent(Base):
    """Store scraped article content from Firecrawl"""
    __tablename__ = 'article_content'

    id = Column(Integer, primary_key=True)
    result_id = Column(Integer, ForeignKey('article_results.id'), nullable=False)

    # Content fields
    raw_html = Column(Text)
    markdown_content = Column(Text)
    cleaned_text = Column(Text)

    # Metadata
    word_count = Column(Integer)
    language = Column(String(10))
    author = Column(String(255))
    published_date = Column(DateTime)
    tags = Column(ARRAY(String))

    # Scraping metadata
    scrape_method = Column(String(50))  # firecrawl, jina, manual
    scrape_success = Column(Boolean, default=True)
    error_message = Column(Text)

    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    result = relationship("ArticleResult", back_populates="content")


class ArticleAnalysis(Base):
    """Store Gemma3:12b analysis of articles"""
    __tablename__ = 'article_analysis'

    id = Column(Integer, primary_key=True)
    result_id = Column(Integer, ForeignKey('article_results.id'), nullable=False)

    # Summary and insights
    summary = Column(Text)  # 500-word summary
    key_insights = Column(ARRAY(Text))  # List of key insights

    # Entity extraction
    entities = Column(JSON)  # {people: [], organizations: [], locations: [], dates: []}

    # Concern assessment (similar to image analysis)
    concern_level = Column(String(20))  # low, medium, high, critical
    concern_indicators = Column(ARRAY(Text))
    human_rights_issues = Column(ARRAY(Text))

    # Specific analysis fields
    worker_conditions = Column(Text)
    refugee_mentions = Column(Boolean, default=False)
    corporate_involvement = Column(ARRAY(String))  # List of companies mentioned
    government_entities = Column(ARRAY(String))

    # Timeline and events
    timeline_events = Column(JSON)  # [{date: '', event: '', significance: ''}]

    # Translation (if needed)
    original_language = Column(String(10))
    translated_summary = Column(Text)  # English translation if original is not English

    # Analysis metadata
    confidence_score = Column(Float)
    processing_time = Column(Float)
    analysis_model = Column(String(50), default='gemma3:12b')

    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    error_message = Column(Text)

    # Relationships
    result = relationship("ArticleResult", back_populates="analysis")