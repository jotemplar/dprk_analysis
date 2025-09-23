#!/usr/bin/env python3
"""Initialize DPRK database schema and load search terms"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from database.models import Base, SearchQuery
from database.connection import engine, get_session
from dprk_images_search_terms import search_terms_comprehensive

load_dotenv()

def create_database():
    """Create database if it doesn't exist"""
    db_name = os.getenv("DB_NAME", "dprk")

    # Connect to postgres to create database
    admin_engine = create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/postgres"
    )

    with admin_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")

        # Check if database exists
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": db_name}
        )

        if not result.fetchone():
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            print(f"✓ Created database '{db_name}'")
        else:
            print(f"✓ Database '{db_name}' already exists")

def create_tables():
    """Create all tables from models"""
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ All tables created successfully")

def load_search_terms():
    """Load search terms into database"""
    session = get_session()

    try:
        # Clear existing search terms
        session.query(SearchQuery).delete()
        session.commit()

        loaded_count = 0

        for idx, term in enumerate(search_terms_comprehensive):
            # Determine language and category from term
            language = 'en'  # Default
            category = 'general'  # Default

            # Language detection based on script
            if any(ord(char) >= 0x0400 and ord(char) <= 0x04FF for char in term):
                language = 'ru'  # Cyrillic
            elif any(ord(char) >= 0xAC00 and ord(char) <= 0xD7AF for char in term):
                language = 'ko'  # Korean
            elif any(ord(char) >= 0x4E00 and ord(char) <= 0x9FFF for char in term):
                language = 'zh'  # Chinese
            elif 'travailleurs' in term.lower() or 'soldats' in term.lower():
                language = 'fr'  # French

            # Category detection based on keywords
            if 'construction' in term.lower() or 'строител' in term.lower() or '건설' in term:
                category = 'labour_type'
            elif 'soldier' in term.lower() or 'солдат' in term.lower() or '병사' in term:
                category = 'military'
            elif 'student' in term.lower() or 'студент' in term.lower() or '유학생' in term:
                category = 'community'
            elif 'Far East' in term or 'Kursk' in term or 'Vladivostok' in term or 'Дальнего Востока' in term:
                category = 'region'
            elif 'guard' in term.lower() or 'supervis' in term.lower() or 'надзор' in term.lower():
                category = 'hybrid'

            query = SearchQuery(
                search_term=term,
                language=language,
                category=category,
                search_type='images'
            )

            session.add(query)
            loaded_count += 1

        session.commit()
        print(f"✓ Loaded {loaded_count} search terms into database")

        # Show distribution
        result = session.execute(
            text("""
                SELECT language, category, COUNT(*) as count
                FROM search_queries
                GROUP BY language, category
                ORDER BY language, category
            """)
        )

        print("\nSearch term distribution:")
        for row in result:
            print(f"  {row.language:5} | {row.category:15} | {row.count:3} terms")

    except Exception as e:
        print(f"✗ Error loading search terms: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def create_directories():
    """Create necessary directories for image storage"""
    base_path = Path("/Volumes/X5/_CODE_PROJECTS/DPRK")

    directories = [
        base_path / "captured_data" / "images",
        base_path / "captured_data" / "screenshots",
        base_path / "reports",
        base_path / "logs"
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def main():
    """Main initialization function"""
    print("=" * 60)
    print("DPRK Image Capture System - Database Initialization")
    print("=" * 60)

    try:
        # Create database
        create_database()

        # Create tables
        create_tables()

        # Load search terms
        load_search_terms()

        # Create directories
        create_directories()

        print("\n" + "=" * 60)
        print("✓ Database initialization completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()