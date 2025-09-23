#!/usr/bin/env python3
"""Create article analysis tables in the database"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine
from database.article_models import Base

def create_article_tables():
    """Create all article-related tables"""
    print("Creating article analysis tables...")

    # Create all tables defined in article_models
    Base.metadata.create_all(engine, checkfirst=True)

    print("✅ Article tables created successfully:")
    print("   - article_searches")
    print("   - article_results")
    print("   - article_content")
    print("   - article_analysis")

if __name__ == "__main__":
    create_article_tables()