#!/usr/bin/env python3
"""Process all images with Gemma3:12b using structured outputs"""

import time
import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from database.connection import get_session
from database.models import ContentAnalysis, CapturedImage
from utils.ollama_structured import StructuredOllamaAnalyzer
from utils.image_preprocessor import ImagePreprocessor
from tqdm import tqdm


class GemmaStructuredProcessor:
    """Process images with Gemma3:12b using structured JSON outputs"""

    def __init__(self, max_concurrent=4, max_size=896):
        """Initialize parallel processor with structured outputs"""
        self.max_concurrent = max_concurrent
        self.preprocessor = ImagePreprocessor(max_size=max_size)
        self.processed_count = 0
        self.error_count = 0
        self.lock = Lock()
        self.start_time = None

        print(f"✨ Initialized Gemma3:12b Structured Processor")
        print(f"   Model: gemma3:12b")
        print(f"   Max concurrent: {max_concurrent}")
        print(f"   Image standardization: {max_size}x{max_size}")
        print(f"   🎯 Using structured JSON outputs with Pydantic validation")
        print(f"   🚀 Parallel processing with {max_concurrent} threads")

    def get_images_to_process(self, session, reprocess=False):
        """Get images that need Gemma3:12b processing"""
        if reprocess:
            # Get all images
            return session.query(CapturedImage).all()
        else:
            # Get images without Gemma analysis
            return session.query(CapturedImage).outerjoin(
                ContentAnalysis, CapturedImage.result_id == ContentAnalysis.result_id
            ).filter(
                (ContentAnalysis.gemma_description == None) |
                (ContentAnalysis.gemma_description == '')
            ).all()

    def process_single_image(self, image_data):
        """Process a single image with structured outputs"""
        image_id, image_path, result_id = image_data
        session = get_session()

        try:
            # Check if file exists
            if not Path(image_path).exists():
                with self.lock:
                    self.error_count += 1
                return {'success': False, 'error': 'File not found'}

            # Create analyzer for this thread
            analyzer = StructuredOllamaAnalyzer(model="gemma3:12b")

            # Analyze image with structured output
            start_time = time.time()
            result = analyzer.analyze_image(image_path)
            processing_time = time.time() - start_time

            if not result:
                with self.lock:
                    self.error_count += 1
                return {'success': False, 'error': 'Analysis failed'}

            # Get or create analysis record
            analysis = session.query(ContentAnalysis).filter_by(
                result_id=result_id
            ).first()

            if not analysis:
                # Create new analysis with Gemma results
                analysis = ContentAnalysis(
                    result_id=result_id,
                    # Store in primary fields since this is structured
                    scene_description=result.get('scene_description', ''),
                    location_assessment=result.get('location_assessment', ''),
                    environment_type=result.get('environment_type', 'unknown'),
                    personnel_count=result.get('personnel_count', 0),
                    personnel_types=result.get('personnel_types', []),
                    uniform_identification=result.get('uniform_identification', ''),
                    activity_type=result.get('activity_type', 'unknown'),
                    activity_description=result.get('activity_description', ''),
                    concern_level=result.get('concern_level', 'low'),
                    concern_indicators=result.get('concern_indicators', []),
                    supervision_present=result.get('supervision_present', False),
                    restriction_indicators=result.get('restriction_indicators', []),
                    confidence_score=result.get('confidence_score', 0.5),
                    # Also store in Gemma fields
                    gemma_description=result.get('scene_description', ''),
                    gemma_concern_level=result.get('concern_level', 'low'),
                    gemma_indicators=result.get('concern_indicators', []),
                    gemma_processing_time=processing_time,
                    analysis_model='gemma3:12b',
                    processing_time=processing_time,
                    analyzed_at=datetime.utcnow()
                )
                session.add(analysis)
            else:
                # Update with Gemma structured results
                analysis.gemma_description = result.get('scene_description', '')
                analysis.gemma_concern_level = result.get('concern_level', 'low')
                analysis.gemma_indicators = result.get('concern_indicators', [])
                analysis.gemma_processing_time = processing_time

                # If no LLaVA analysis, update primary fields too
                if not analysis.scene_description:
                    analysis.scene_description = result.get('scene_description', '')
                    analysis.location_assessment = result.get('location_assessment', '')
                    analysis.environment_type = result.get('environment_type', 'unknown')
                    analysis.personnel_count = result.get('personnel_count', 0)
                    analysis.personnel_types = result.get('personnel_types', [])
                    analysis.uniform_identification = result.get('uniform_identification', '')
                    analysis.activity_type = result.get('activity_type', 'unknown')
                    analysis.activity_description = result.get('activity_description', '')
                    analysis.concern_level = result.get('concern_level', 'low')
                    analysis.concern_indicators = result.get('concern_indicators', [])
                    analysis.supervision_present = result.get('supervision_present', False)
                    analysis.restriction_indicators = result.get('restriction_indicators', [])
                    analysis.confidence_score = result.get('confidence_score', 0.5)

                analysis.analyzed_at = datetime.utcnow()

            session.commit()

            with self.lock:
                self.processed_count += 1

            return {
                'success': True,
                'time': processing_time,
                'has_description': bool(result.get('scene_description'))
            }

        except Exception as e:
            session.rollback()
            with self.lock:
                self.error_count += 1
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def run(self, limit=None, test_mode=False, reprocess=False):
        """Run parallel processing with structured outputs"""
        session = get_session()

        try:
            # Get images to process
            print("\n📊 Checking for images to process...")
            images = self.get_images_to_process(session, reprocess=reprocess)

            if limit:
                images = images[:limit]

            total = len(images)

            if total == 0:
                print("✅ All images already have Gemma3:12b analysis!")
                return

            print(f"📋 Found {total} images to process")

            if test_mode:
                print("🧪 Test mode: Processing first 10 images only")
                images = images[:10]
                total = len(images)

            # Prepare data for parallel processing
            image_data = [
                (img.id, img.file_path, img.result_id)
                for img in images
            ]

            # Track statistics
            self.start_time = time.time()
            success_with_desc = 0
            success_no_desc = 0

            # Process in parallel
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                # Submit all tasks
                futures = {
                    executor.submit(self.process_single_image, data): data
                    for data in image_data
                }

                # Process with progress bar
                with tqdm(total=total, desc="Processing") as pbar:
                    for future in as_completed(futures):
                        result = future.result()

                        if result['success']:
                            if result.get('has_description'):
                                success_with_desc += 1
                            else:
                                success_no_desc += 1

                        pbar.update(1)

                        # Update description with detailed stats
                        pbar.set_description(
                            f"Gemma3:12b (✓{self.processed_count} [📝{success_with_desc}] ✗{self.error_count})"
                        )

                        # Print periodic updates
                        if self.processed_count % 25 == 0 and self.processed_count > 0:
                            elapsed = time.time() - self.start_time
                            rate = self.processed_count / elapsed
                            eta = (total - self.processed_count - self.error_count) / rate if rate > 0 else 0
                            print(f"\n📊 Progress Report:")
                            print(f"   Processed: {self.processed_count}/{total}")
                            print(f"   With descriptions: {success_with_desc}")
                            print(f"   Empty descriptions: {success_no_desc}")
                            print(f"   Errors: {self.error_count}")
                            print(f"   Rate: {rate:.2f} images/sec")
                            print(f"   ETA: {eta/60:.1f} minutes\n")

            # Final statistics
            total_time = time.time() - self.start_time
            success_rate = (self.processed_count / total * 100) if total > 0 else 0
            desc_rate = (success_with_desc / self.processed_count * 100) if self.processed_count > 0 else 0

            print("\n" + "=" * 60)
            print("📈 Gemma3:12b Structured Processing Complete!")
            print("=" * 60)
            print(f"✅ Successfully processed: {self.processed_count}/{total} ({success_rate:.1f}%)")
            print(f"📝 With descriptions: {success_with_desc} ({desc_rate:.1f}% of successes)")
            print(f"📄 Empty descriptions: {success_no_desc}")
            print(f"❌ Errors: {self.error_count}")
            print(f"⏱️  Total time: {total_time/60:.1f} minutes")
            print(f"⚡ Average: {total_time/max(self.processed_count,1):.1f}s per image")
            print(f"🚀 Throughput: {self.processed_count/max(total_time,1):.2f} images/second")

        finally:
            session.close()


def main():
    parser = argparse.ArgumentParser(description="Process images with Gemma3:12b structured outputs")
    parser.add_argument('--max-concurrent', type=int, default=4,
                        help='Max concurrent requests (default: 4)')
    parser.add_argument('--limit', type=int, help='Limit number of images')
    parser.add_argument('--test', action='store_true', help='Test mode (10 images)')
    parser.add_argument('--reprocess', action='store_true',
                        help='Reprocess all images (including those with existing Gemma analysis)')
    args = parser.parse_args()

    processor = GemmaStructuredProcessor(max_concurrent=args.max_concurrent)
    processor.run(limit=args.limit, test_mode=args.test, reprocess=args.reprocess)


if __name__ == "__main__":
    main()