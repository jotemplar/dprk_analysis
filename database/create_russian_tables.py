"""Create database tables for Russian OSINT searches"""

import sys
from sqlalchemy import create_engine
from database.connection import get_engine
from database.models import Base
from database.russian_search_models import RussianSearch, RussianSearchResult, RussianSearchContent


def create_tables():
    """Create all Russian search tables"""
    try:
        engine = get_engine()

        print("Creating Russian OSINT search tables...")
        print("=" * 60)

        # Create tables
        Base.metadata.create_all(
            engine,
            tables=[
                RussianSearch.__table__,
                RussianSearchResult.__table__,
                RussianSearchContent.__table__
            ]
        )

        print("\nTables created successfully:")
        print("  - russian_searches")
        print("  - russian_search_results")
        print("  - russian_search_content")
        print("\n✓ Database schema updated")

    except Exception as e:
        print(f"\n✗ Error creating tables: {e}")
        sys.exit(1)


def verify_tables():
    """Verify tables were created"""
    from sqlalchemy import inspect

    try:
        engine = get_engine()
        inspector = inspect(engine)

        required_tables = [
            'russian_searches',
            'russian_search_results',
            'russian_search_content'
        ]

        existing_tables = inspector.get_table_names()

        print("\nVerifying tables...")
        all_exist = True

        for table in required_tables:
            if table in existing_tables:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} (missing)")
                all_exist = False

        if all_exist:
            print("\n✓ All tables verified successfully")
            return True
        else:
            print("\n✗ Some tables are missing")
            return False

    except Exception as e:
        print(f"\n✗ Error verifying tables: {e}")
        return False


def main():
    """Main entry point"""
    print("Russian OSINT Search Database Setup")
    print("=" * 60)

    # Create tables
    create_tables()

    # Verify
    if verify_tables():
        print("\nDatabase is ready for Russian OSINT searches!")
    else:
        print("\nWarning: Database verification failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
