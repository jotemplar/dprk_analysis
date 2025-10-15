"""SQLAlchemy models for Russian OSINT search queries (Yandex and Google Russia)"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, ARRAY, UniqueConstraint, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from database.models import Base


class RussianSearch(Base):
    """Store Russian OSINT search queries (Yandex and Google Russia)"""
    __tablename__ = 'russian_searches'

    id = Column(Integer, primary_key=True)
    query_id = Column(String(100), unique=True, nullable=False)  # From CSV: ru_construction_00001
    language = Column(String(10), default='ru')  # Language code from CSV
    engine = Column(String(20), nullable=False)  # 'yandex' or 'google'
    location = Column(String(50), default='russia')  # Search location

    # Query metadata from CSV
    theme = Column(String(100))  # portal_slice, etc.
    sector = Column(String(100))  # стройка, etc.
    region = Column(String(100))  # Приморский край, etc.
    time_filter = Column(String(50))  # 2023..2025
    site = Column(String(255))  # hh.ru, superjob.ru, etc.
    query_text = Column(Text, nullable=False)  # The actual search query

    # Processing status
    search_status = Column(String(20), default='pending')  # pending, completed, failed
    results_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    searched_at = Column(DateTime(timezone=True))

    # Relationships
    results = relationship("RussianSearchResult", back_populates="search", cascade="all, delete-orphan")


class RussianSearchResult(Base):
    """Store search results from Yandex or Google Russia"""
    __tablename__ = 'russian_search_results'

    id = Column(Integer, primary_key=True)
    search_id = Column(Integer, ForeignKey('russian_searches.id'), nullable=False)

    # Result data
    position = Column(Integer)
    url = Column(Text, nullable=False)
    title = Column(Text)
    snippet = Column(Text)
    source_domain = Column(String(255))
    published_date = Column(DateTime)

    # Processing status
    scrape_status = Column(String(20), default='pending')  # pending, completed, failed
    analysis_status = Column(String(20), default='pending')  # pending, completed, failed

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    search = relationship("RussianSearch", back_populates="results")
    content = relationship("RussianSearchContent", back_populates="result", uselist=False, cascade="all, delete-orphan")

    # Unique constraint
    __table_args__ = (UniqueConstraint('search_id', 'url', name='_russian_search_url_uc'),)


class RussianSearchContent(Base):
    """Store scraped content from Russian search results"""
    __tablename__ = 'russian_search_content'

    id = Column(Integer, primary_key=True)
    result_id = Column(Integer, ForeignKey('russian_search_results.id'), nullable=False)

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
    result = relationship("RussianSearchResult", back_populates="content")
