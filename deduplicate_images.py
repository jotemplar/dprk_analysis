#!/usr/bin/env python3
"""Deduplicate images by keeping only the latest capture for each unique URL"""

import argparse
from datetime import datetime
from collections import defaultdict
from database.connection import get_session
from database.models import CapturedImage, SearchResult, ContentAnalysis
from sqlalchemy import func
from tqdm import tqdm


class ImageDeduplicator:
    """Handle deduplication of images with same result_id"""

    def __init__(self, dry_run=True):
        """Initialize deduplicator"""
        self.dry_run = dry_run
        self.session = get_session()
        self.duplicates_found = 0
        self.images_removed = 0
        self.analyses_preserved = 0

    def find_duplicate_groups(self):
        """Find groups of duplicate images by result_id"""
        print("\n📊 Analyzing for duplicates...")

        # Query for result_ids that have multiple images
        duplicate_query = self.session.query(
            CapturedImage.result_id,
            func.count(CapturedImage.id).label('count')
        ).group_by(CapturedImage.result_id).having(func.count(CapturedImage.id) > 1)

        duplicate_groups = duplicate_query.all()

        if not duplicate_groups:
            print("✅ No duplicates found!")
            return []

        print(f"⚠️  Found {len(duplicate_groups)} result_ids with duplicate images")

        # Get detailed information for each group
        groups = []
        for result_id, count in duplicate_groups:
            # Get all images for this result_id
            images = self.session.query(CapturedImage).filter_by(
                result_id=result_id
            ).order_by(CapturedImage.captured_at.desc()).all()

            # Get the search result URL for context
            search_result = self.session.query(SearchResult).filter_by(
                id=result_id
            ).first()

            groups.append({
                'result_id': result_id,
                'url': search_result.url if search_result else 'Unknown',
                'images': images,
                'count': count
            })

        return groups

    def merge_analyses(self, keep_image, remove_images):
        """Merge analyses from images to be removed into the keeper"""
        # Get analysis for the keeper
        keep_analysis = self.session.query(ContentAnalysis).filter_by(
            result_id=keep_image.result_id
        ).first()

        if not keep_analysis:
            # Check if any of the remove images have an analysis
            for img in remove_images:
                analysis = self.session.query(ContentAnalysis).filter_by(
                    result_id=img.result_id
                ).first()
                if analysis:
                    # This shouldn't happen since they share result_id
                    # but keep as keeper's analysis if found
                    keep_analysis = analysis
                    self.analyses_preserved += 1
                    break

        return keep_analysis is not None

    def deduplicate(self):
        """Perform deduplication"""
        groups = self.find_duplicate_groups()

        if not groups:
            return

        # Calculate total duplicates
        total_duplicates = sum(g['count'] - 1 for g in groups)
        print(f"\n🔍 Will remove {total_duplicates} duplicate images")

        if self.dry_run:
            print("\n🧪 DRY RUN MODE - No changes will be made")
        else:
            print("\n⚠️  LIVE MODE - Changes will be committed")
            response = input("\nProceed with deduplication? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Deduplication cancelled")
                return

        # Process each group
        with tqdm(total=len(groups), desc="Processing groups") as pbar:
            for group in groups:
                # Keep the most recent image (first in our sorted list)
                keep = group['images'][0]
                remove = group['images'][1:]

                # Ensure the keeper has any analysis
                has_analysis = self.merge_analyses(keep, remove)

                if not self.dry_run:
                    # Remove duplicate images
                    for img in remove:
                        try:
                            self.session.delete(img)
                            self.images_removed += 1
                        except Exception as e:
                            print(f"\n❌ Error removing image {img.id}: {e}")
                            self.session.rollback()
                            continue
                else:
                    # In dry run, just count
                    self.images_removed += len(remove)

                self.duplicates_found += len(remove)
                pbar.update(1)

        # Commit changes if not dry run
        if not self.dry_run:
            try:
                self.session.commit()
                print("\n✅ Changes committed successfully")
            except Exception as e:
                print(f"\n❌ Error committing changes: {e}")
                self.session.rollback()
                return

        # Print summary
        print("\n" + "="*60)
        print("📈 Deduplication Summary")
        print("="*60)
        print(f"Result IDs with duplicates: {len(groups)}")
        print(f"Duplicate images found: {self.duplicates_found}")
        print(f"Images removed: {self.images_removed}")
        print(f"Analyses preserved: {self.analyses_preserved}")

        if self.dry_run:
            print("\n💡 This was a dry run. Use --execute to perform actual deduplication")

    def verify_integrity(self):
        """Verify database integrity after deduplication"""
        print("\n🔍 Verifying database integrity...")

        # Check for orphaned analyses
        orphaned = self.session.query(ContentAnalysis).outerjoin(
            SearchResult, ContentAnalysis.result_id == SearchResult.id
        ).filter(SearchResult.id == None).count()

        if orphaned > 0:
            print(f"⚠️  Found {orphaned} orphaned analyses")
        else:
            print("✅ No orphaned analyses found")

        # Check for result_ids with no images
        results_without_images = self.session.query(SearchResult).outerjoin(
            CapturedImage, SearchResult.id == CapturedImage.result_id
        ).filter(CapturedImage.id == None).count()

        print(f"📊 Search results without images: {results_without_images}")

        # Final duplicate check
        remaining_dups = self.session.query(
            CapturedImage.result_id,
            func.count(CapturedImage.id).label('count')
        ).group_by(CapturedImage.result_id).having(func.count(CapturedImage.id) > 1).count()

        if remaining_dups > 0:
            print(f"⚠️  Still have {remaining_dups} result_ids with duplicates")
        else:
            print("✅ No duplicates remain")

    def close(self):
        """Close database session"""
        self.session.close()


def main():
    parser = argparse.ArgumentParser(description="Deduplicate captured images")
    parser.add_argument('--execute', action='store_true',
                        help='Execute deduplication (default is dry run)')
    parser.add_argument('--verify', action='store_true',
                        help='Only verify integrity without deduplication')
    args = parser.parse_args()

    deduplicator = ImageDeduplicator(dry_run=not args.execute)

    try:
        if args.verify:
            deduplicator.verify_integrity()
        else:
            deduplicator.deduplicate()
            deduplicator.verify_integrity()
    finally:
        deduplicator.close()


if __name__ == "__main__":
    main()