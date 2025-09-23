"""SQLAlchemy models for DPRK image capture system"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, ARRAY, UniqueConstraint, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class SearchQuery(Base):
    """Store image search terms and their categories"""
    __tablename__ = 'search_queries'

    id = Column(Integer, primary_key=True)
    category = Column(String(100))  # region, labour_type, military, community, hybrid
    theme = Column(String(100), default='general')  # general, construction_exploitation, dorms_living, etc.
    search_term = Column(Text, unique=True, nullable=False)
    language = Column(String(10), default='en')  # en, ru, ko, zh, fr
    search_type = Column(String(20), default='images')  # images, web
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    results = relationship("SearchResult", back_populates="query", cascade="all, delete-orphan")
    sessions = relationship("SearchSession", back_populates="query")

class SearchResult(Base):
    """Store search results with image URLs"""
    __tablename__ = 'search_results'

    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey('search_queries.id'), nullable=False)
    url = Column(Text, nullable=False)
    image_url = Column(Text)  # Direct image URL if available
    page_url = Column(Text)  # Page containing the image
    title = Column(Text)
    snippet = Column(Text)
    position = Column(Integer)
    source_domain = Column(String(255))

    # Processing status
    screenshot_status = Column(String(20), default='pending')  # pending, completed, failed
    image_download_status = Column(String(20), default='pending')  # pending, completed, failed
    analysis_status = Column(String(20), default='pending')  # pending, completed, failed

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    query = relationship("SearchQuery", back_populates="results")
    captured_images = relationship("CapturedImage", back_populates="search_result", cascade="all, delete-orphan")
    screenshots = relationship("Screenshot", back_populates="search_result", cascade="all, delete-orphan")
    content_analysis = relationship("ContentAnalysis", back_populates="search_result", uselist=False, cascade="all, delete-orphan")

    # Unique constraint
    __table_args__ = (UniqueConstraint('query_id', 'url', name='_query_url_uc'),)

class CapturedImage(Base):
    """Store captured/downloaded images"""
    __tablename__ = 'captured_images'

    id = Column(Integer, primary_key=True)
    result_id = Column(Integer, ForeignKey('search_results.id'), nullable=False)
    file_path = Column(Text, nullable=False)
    file_name = Column(String(255))
    file_size = Column(Integer)  # bytes
    image_width = Column(Integer)
    image_height = Column(Integer)
    image_format = Column(String(10))  # jpg, png, gif, etc.
    download_url = Column(Text)

    # Metadata
    exif_data = Column(JSON)
    capture_date = Column(DateTime)
    location_data = Column(JSON)  # If available in EXIF

    captured_at = Column(DateTime(timezone=True), server_default=func.now())
    error_message = Column(Text)

    # Relationships
    search_result = relationship("SearchResult", back_populates="captured_images")

class Screenshot(Base):
    """Store screenshots of search results or web pages"""
    __tablename__ = 'screenshots'

    id = Column(Integer, primary_key=True)
    result_id = Column(Integer, ForeignKey('search_results.id'), nullable=False)
    file_path = Column(Text, nullable=False)
    file_name = Column(String(255))
    screenshot_type = Column(String(50))  # 'search_results', 'full_page', 'element'
    page_url = Column(Text)
    viewport_width = Column(Integer)
    viewport_height = Column(Integer)

    captured_at = Column(DateTime(timezone=True), server_default=func.now())
    error_message = Column(Text)

    # Relationships
    search_result = relationship("SearchResult", back_populates="screenshots")

class ContentAnalysis(Base):
    """Store AI analysis of images using local LLM"""
    __tablename__ = 'content_analysis'

    id = Column(Integer, primary_key=True)
    result_id = Column(Integer, ForeignKey('search_results.id'), nullable=False, unique=True)

    # Scene analysis
    scene_description = Column(Text)
    location_assessment = Column(Text)
    environment_type = Column(String(100))  # indoor, outdoor, industrial, residential, etc.

    # Personnel identification
    personnel_count = Column(Integer)
    personnel_types = Column(ARRAY(Text))  # workers, soldiers, supervisors, civilians
    uniform_identification = Column(Text)

    # Activity analysis
    activity_type = Column(String(100))  # construction, military, educational, etc.
    activity_description = Column(Text)

    # Concern indicators
    concern_level = Column(String(20))  # low, medium, high, critical
    concern_indicators = Column(ARRAY(Text))
    supervision_present = Column(Boolean)
    restriction_indicators = Column(ARRAY(Text))

    # Gemma analysis fields (second pass)
    gemma_description = Column(Text)
    gemma_concern_level = Column(String(20))  # minimal, moderate, severe, extreme
    gemma_indicators = Column(ARRAY(Text))
    gemma_processing_time = Column(Float)

    # Ensemble analysis fields (combined results)
    ensemble_concern_level = Column(String(20))  # low, medium, high, critical
    ensemble_confidence = Column(Float)  # 0-1 confidence in ensemble result

    # Metadata
    analysis_model = Column(String(50))  # ollama model used
    confidence_score = Column(Float)
    processing_time = Column(Float)  # seconds

    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    error_message = Column(Text)

    # Relationships
    search_result = relationship("SearchResult", back_populates="content_analysis")

class SearchSession(Base):
    """Track search and capture sessions"""
    __tablename__ = 'search_sessions'

    id = Column(Integer, primary_key=True)
    session_name = Column(String(255))
    query_id = Column(Integer, ForeignKey('search_queries.id'))

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Statistics
    total_results = Column(Integer, default=0)
    images_captured = Column(Integer, default=0)
    screenshots_taken = Column(Integer, default=0)
    analyses_completed = Column(Integer, default=0)

    # Status
    current_status = Column(String(50))
    last_error = Column(Text)

    # Relationships
    query = relationship("SearchQuery", back_populates="sessions")

class ImageMetadata(Base):
    """Additional metadata for images"""
    __tablename__ = 'image_metadata'

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey('captured_images.id'), nullable=False, unique=True)

    # Source metadata
    source_title = Column(Text)
    source_description = Column(Text)
    source_keywords = Column(ARRAY(Text))
    source_publication_date = Column(DateTime)

    # Technical metadata
    color_profile = Column(String(50))
    compression_ratio = Column(Float)
    bit_depth = Column(Integer)

    # Content flags
    faces_detected = Column(Integer)
    text_detected = Column(Boolean)

    created_at = Column(DateTime(timezone=True), server_default=func.now())