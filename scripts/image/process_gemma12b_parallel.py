#!/usr/bin/env python3
"""Process all images with Gemma3:12b model using parallel processing"""

import time
import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from database.connection import get_session
from database.models import ContentAnalysis, CapturedImage
from utils.ollama_analyzer import OllamaAnalyzer
from utils.image_preprocessor import ImagePreprocessor
from sqlalchemy import text
from tqdm import tqdm

class Gemma12bParallelProcessor:
    """Process images with Gemma3:12b model using parallel requests"""

    def __init__(self, max_concurrent=4, max_size=896):
        """Initialize parallel processor"""
        self.max_concurrent = max_concurrent
        self.preprocessor = ImagePreprocessor(max_size=max_size)
        self.processed_count = 0
        self.error_count = 0
        self.lock = Lock()

        print(f"✨ Initialized Gemma3:12b Parallel Processor")
        print(f"   Model: gemma3:12b")
        print(f"   Max concurrent: {max_concurrent}")
        print(f"   Image standardization: {max_size}x{max_size}")
        print(f"   🚀 Using {max_concurrent} parallel threads for 4x speed!")

    def get_all_images(self, session, limit=None):
        """Get all captured images"""
        query = session.query(CapturedImage)

        if limit:
            query = query.limit(limit)

        return query.all()

    def process_single_image(self, image_data):
        """Process a single image - thread-safe"""
        image_id, image_path, result_id = image_data
        session = get_session()

        try:
            # Check if file exists
            if not Path(image_path).exists():
                with self.lock:
                    self.error_count += 1
                    print(f"   ⚠️ File not found: {image_path}")
                return False

            # Create analyzer for this thread
            analyzer = OllamaAnalyzer(model="gemma3:12b")

            # Analyze image
            start_time = time.time()
            result = analyzer.analyze_image(image_path)
            processing_time = time.time() - start_time

            # Check if analysis exists
            analysis = session.query(ContentAnalysis).filter_by(
                result_id=result_id
            ).first()

            if not analysis:
                # Skip if no primary analysis exists
                with self.lock:
                    print(f"   ⚠️ No primary analysis for result_id={result_id}")
                return False
            else:
                # Store Gemma3:12b analysis in gemma fields
                analysis.gemma_description = result.get('scene_description', '')
                analysis.gemma_concern_level = result.get('concern_level', 'low')
                analysis.gemma_indicators = result.get('concern_indicators', [])
                analysis.gemma_processing_time = processing_time
                analysis.analyzed_at = datetime.utcnow()

            session.commit()

            with self.lock:
                self.processed_count += 1

            return True

        except Exception as e:
            session.rollback()
            with self.lock:
                self.error_count += 1
                print(f"   ❌ Error processing image {image_id}: {e}")
            return False
        finally:
            session.close()

    def run(self, limit=None, test_mode=False):
        """Run parallel batch processing"""
        session = get_session()

        try:
            # Get all images
            print("\n📊 Getting all captured images...")
            images = self.get_all_images(session, limit=limit)
            total = len(images)

            if total == 0:
                print("❌ No images found in database!")
                return

            print(f"📋 Found {total} images to process with Gemma3:12b")

            if test_mode:
                print("🧪 Test mode: Processing first 20 images only")
                images = images[:20]
                total = len(images)

            # Prepare data for parallel processing
            image_data = [
                (img.id, img.file_path, img.result_id)
                for img in images
            ]

            # Process in parallel with progress bar
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                # Submit all tasks
                futures = {
                    executor.submit(self.process_single_image, data): data
                    for data in image_data
                }

                # Process with progress bar
                with tqdm(total=total, desc="Processing images") as pbar:
                    for future in as_completed(futures):
                        result = future.result()
                        pbar.update(1)

                        # Update description with stats
                        pbar.set_description(
                            f"Gemma3:12b Parallel (✓{self.processed_count} ✗{self.error_count})"
                        )

                        # Print periodic updates
                        if self.processed_count % 50 == 0 and self.processed_count > 0:
                            elapsed = time.time() - start_time
                            rate = self.processed_count / elapsed
                            eta = (total - self.processed_count) / rate if rate > 0 else 0
                            print(f"\n   📊 Progress: {self.processed_count}/{total} "
                                  f"({rate:.1f} images/sec, ETA: {eta/60:.1f} minutes)")

            # Final stats
            total_time = time.time() - start_time
            print(f"\n📈 Gemma3:12b Processing Complete!")
            print(f"   ✓ Processed: {self.processed_count}")
            print(f"   ✗ Errors: {self.error_count}")
            print(f"   ⏱️ Total time: {total_time:.1f}s")
            print(f"   📊 Average: {total_time/max(self.processed_count,1):.1f}s per image")
            print(f"   🚀 Throughput: {self.processed_count/total_time:.2f} images/second")

        finally:
            session.close()

def main():
    parser = argparse.ArgumentParser(description="Process images with Gemma3:12b in parallel")
    parser.add_argument('--max-concurrent', type=int, default=4,
                        help='Max concurrent requests (default: 4)')
    parser.add_argument('--limit', type=int, help='Limit number of images')
    parser.add_argument('--test', action='store_true', help='Test mode (20 images)')
    args = parser.parse_args()

    processor = Gemma12bParallelProcessor(max_concurrent=args.max_concurrent)
    processor.run(limit=args.limit, test_mode=args.test)

if __name__ == "__main__":
    main()