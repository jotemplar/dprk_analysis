#!/usr/bin/env python3
"""Process all images with Gemma3:12b model"""

import time
import argparse
from datetime import datetime
from pathlib import Path
from database.connection import get_session
from database.models import ContentAnalysis, CapturedImage
from utils.ollama_analyzer import OllamaAnalyzer
from utils.image_preprocessor import ImagePreprocessor
from sqlalchemy import text
from tqdm import tqdm

class Gemma12bBatchProcessor:
    """Process images with Gemma3:12b model in batches"""

    def __init__(self, batch_size=10, max_size=896):
        """Initialize batch processor"""
        self.batch_size = batch_size
        self.preprocessor = ImagePreprocessor(max_size=max_size)
        self.analyzer = OllamaAnalyzer(model="gemma3:12b")
        self.processed_count = 0
        self.error_count = 0

        print(f"✨ Initialized Gemma3:12b Batch Processor")
        print(f"   Model: gemma3:12b")
        print(f"   Batch size: {batch_size}")
        print(f"   Image standardization: {max_size}x{max_size}")

    def get_all_images(self, session, limit=None):
        """Get all captured images"""
        query = session.query(CapturedImage)

        if limit:
            query = query.limit(limit)

        return query.all()

    def process_image(self, session, image):
        """Process a single image with Gemma3:12b"""
        try:
            # Check if file exists
            if not Path(image.file_path).exists():
                print(f"   ⚠️ File not found: {image.file_path}")
                self.error_count += 1
                return False

            # Analyze image with Gemma3:12b
            start_time = time.time()
            result = self.analyzer.analyze_image(image.file_path)
            processing_time = time.time() - start_time

            # Check if analysis exists
            analysis = session.query(ContentAnalysis).filter_by(
                result_id=image.result_id
            ).first()

            if not analysis:
                # Skip if no primary analysis exists
                print(f"   ⚠️ No primary analysis for result_id={image.result_id}")
                return False
            else:
                # Store Gemma3:12b analysis in gemma fields (temporary using gemma fields)
                analysis.gemma_description = result.get('scene_description', '')
                analysis.gemma_concern_level = result.get('concern_level', 'low')
                analysis.gemma_indicators = result.get('concern_indicators', [])
                analysis.gemma_processing_time = processing_time
                analysis.analyzed_at = datetime.utcnow()

            session.commit()
            self.processed_count += 1
            return True

        except Exception as e:
            print(f"   ❌ Error processing {image.file_path}: {e}")
            session.rollback()
            self.error_count += 1
            return False

    def run(self, limit=None, test_mode=False):
        """Run batch processing"""
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
                print("🧪 Test mode: Processing first 5 images only")
                images = images[:5]
                total = len(images)

            # Process in batches
            start_time = time.time()

            with tqdm(total=total, desc="Processing images") as pbar:
                for i in range(0, total, self.batch_size):
                    batch = images[i:i+self.batch_size]
                    batch_start = time.time()

                    for image in batch:
                        success = self.process_image(session, image)
                        pbar.update(1)

                        # Update description with stats
                        pbar.set_description(
                            f"Gemma3:12b Processing (✓{self.processed_count} ✗{self.error_count})"
                        )

                    # Commit batch
                    session.commit()

                    # Show batch stats
                    batch_time = time.time() - batch_start
                    avg_time = batch_time / len(batch)
                    if i % 100 == 0:  # Print less frequently
                        print(f"\n   Batch {i//self.batch_size + 1}: {len(batch)} images in {batch_time:.1f}s ({avg_time:.1f}s/image)")

            # Final stats
            total_time = time.time() - start_time
            print(f"\n📈 Gemma3:12b Processing Complete!")
            print(f"   ✓ Processed: {self.processed_count}")
            print(f"   ✗ Errors: {self.error_count}")
            print(f"   ⏱️ Total time: {total_time:.1f}s")
            print(f"   📊 Average: {total_time/max(self.processed_count,1):.1f}s per image")

        finally:
            session.close()

def main():
    parser = argparse.ArgumentParser(description="Process images with Gemma3:12b")
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size')
    parser.add_argument('--limit', type=int, help='Limit number of images')
    parser.add_argument('--test', action='store_true', help='Test mode (5 images)')
    args = parser.parse_args()

    processor = Gemma12bBatchProcessor(batch_size=args.batch_size)
    processor.run(limit=args.limit, test_mode=args.test)

if __name__ == "__main__":
    main()