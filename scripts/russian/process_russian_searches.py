"""Process Russian OSINT search queries from CSV (Yandex and Google Russia)"""

import os
import csv
import sys
import time
from datetime import datetime, timezone
from typing import List, Dict
from sqlalchemy.orm import Session
from database.connection import get_session
from database.russian_search_models import RussianSearch, RussianSearchResult
from search.serp_russia_client import SerpRussiaClient


def load_queries_from_csv(csv_path: str) -> List[Dict]:
    """
    Load search queries from CSV file

    Args:
        csv_path: Path to CSV file

    Returns:
        List of query dictionaries
    """
    queries = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
        reader = csv.DictReader(f)
        for row in reader:
            queries.append({
                'query_id': row['id'],
                'language': row['language'],
                'engine_hint': row['engine_hint'],
                'theme': row['theme'],
                'sector': row['sector'],
                'region': row['region'],
                'time_filter': row['time_filter'],
                'site': row['site'],
                'query_text': row['query']
            })

    print(f"Loaded {len(queries)} queries from CSV")
    return queries


def store_query_in_db(session: Session, query_data: Dict) -> RussianSearch:
    """
    Store or retrieve search query in database

    Args:
        session: Database session
        query_data: Query data dictionary

    Returns:
        RussianSearch object
    """
    # Check if already exists
    existing = session.query(RussianSearch).filter_by(
        query_id=query_data['query_id']
    ).first()

    if existing:
        print(f"  Query {query_data['query_id']} already exists in database")
        return existing

    # Determine engine
    engine = 'yandex' if query_data['engine_hint'].lower() == 'yandex' else 'google'

    # Create new search record
    search = RussianSearch(
        query_id=query_data['query_id'],
        language=query_data['language'],
        engine=engine,
        location='russia',
        theme=query_data['theme'],
        sector=query_data['sector'],
        region=query_data['region'],
        time_filter=query_data['time_filter'],
        site=query_data['site'],
        query_text=query_data['query_text'],
        search_status='pending'
    )

    session.add(search)
    session.commit()
    session.refresh(search)

    print(f"  Stored query {query_data['query_id']} in database")
    return search


def execute_search(client: SerpRussiaClient, search: RussianSearch,
                  session: Session, num_results: int = 10) -> int:
    """
    Execute search and store results

    Args:
        client: SERP Russia client
        search: RussianSearch object
        session: Database session
        num_results: Number of results to retrieve (default 10)

    Returns:
        Number of results found
    """
    try:
        print(f"\n[{search.query_id}] Executing {search.engine.upper()} search...")
        print(f"  Query: {search.query_text[:100]}...")

        # Execute search
        results = client.search(
            query=search.query_text,
            engine=search.engine,
            num_results=num_results
        )

        # Store results
        results_stored = 0
        for result in results:
            # Check if result already exists
            existing = session.query(RussianSearchResult).filter_by(
                search_id=search.id,
                url=result['url']
            ).first()

            if existing:
                continue

            # Create new result record
            search_result = RussianSearchResult(
                search_id=search.id,
                position=result.get('position', 0),
                url=result['url'],
                title=result.get('title', ''),
                snippet=result.get('snippet', ''),
                source_domain=result.get('source_domain', ''),
                published_date=None  # Parse if needed
            )

            session.add(search_result)
            results_stored += 1

        # Update search record
        search.search_status = 'completed'
        search.results_count = results_stored
        search.searched_at = datetime.now(timezone.utc)

        session.commit()

        print(f"  Stored {results_stored} new results (total: {len(results)})")
        return results_stored

    except Exception as e:
        print(f"  Error executing search: {e}")
        search.search_status = 'failed'
        session.commit()
        return 0


def process_all_queries(csv_path: str, num_results: int = 10,
                       delay_seconds: float = 2.0, resume: bool = True):
    """
    Process all queries from CSV file

    Args:
        csv_path: Path to CSV file
        num_results: Number of results per query (default 10)
        delay_seconds: Delay between queries (default 2.0)
        resume: Skip already completed queries (default True)
    """
    # Load queries
    queries = load_queries_from_csv(csv_path)

    if not queries:
        print("No queries to process")
        return

    # Initialize client
    client = SerpRussiaClient()
    session = get_session()

    # Process queries
    total = len(queries)
    completed = 0
    skipped = 0
    failed = 0

    print(f"\nProcessing {total} Russian OSINT queries")
    print("=" * 80)

    try:
        for i, query_data in enumerate(queries, 1):
            print(f"\n[{i}/{total}] Processing {query_data['query_id']}...")

            # Store query in database
            search = store_query_in_db(session, query_data)

            # Check if already completed (resume mode)
            if resume and search.search_status == 'completed':
                print(f"  Skipping (already completed with {search.results_count} results)")
                skipped += 1
                continue

            # Execute search
            results_count = execute_search(client, search, session, num_results)

            if results_count > 0 or search.search_status == 'completed':
                completed += 1
            else:
                failed += 1

            # Rate limiting delay
            if i < total:
                print(f"  Waiting {delay_seconds}s before next query...")
                time.sleep(delay_seconds)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        session.close()

    # Print summary
    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)
    print(f"Total queries: {total}")
    print(f"Completed: {completed}")
    print(f"Skipped (already done): {skipped}")
    print(f"Failed: {failed}")
    print(f"Remaining: {total - completed - skipped - failed}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Process Russian OSINT search queries')
    parser.add_argument('--csv', type=str,
                       default='dprk_osint_queries_with_social_and_portals_v1_3.csv',
                       help='Path to CSV file')
    parser.add_argument('--num-results', type=int, default=10,
                       help='Number of results per query (default: 10)')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay between queries in seconds (default: 2.0)')
    parser.add_argument('--no-resume', action='store_true',
                       help='Process all queries (don\'t skip completed ones)')

    args = parser.parse_args()

    # Check if CSV exists
    if not os.path.exists(args.csv):
        print(f"Error: CSV file not found: {args.csv}")
        sys.exit(1)

    # Process queries
    process_all_queries(
        csv_path=args.csv,
        num_results=args.num_results,
        delay_seconds=args.delay,
        resume=not args.no_resume
    )


if __name__ == '__main__':
    main()
