#!/usr/bin/env python3
"""Process images missing LLaVA analysis in batches"""

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

class LLaVABatchProcessor:
    """Process images with LLaVA model in batches"""

    def __init__(self, batch_size=10, max_size=896):
        """Initialize batch processor"""
        self.batch_size = batch_size
        self.preprocessor = ImagePreprocessor(max_size=max_size)
        self.analyzer = OllamaAnalyzer(model="llava")
        self.processed_count = 0
        self.error_count = 0

        print(f"✨ Initialized LLaVA Batch Processor")
        print(f"   Model: llava")
        print(f"   Batch size: {batch_size}")
        print(f"   Image standardization: {max_size}x{max_size}")

    def get_missing_images(self, session, limit=None):
        """Get images missing LLaVA analysis"""
        query = session.query(CapturedImage).outerjoin(
            ContentAnalysis, CapturedImage.result_id == ContentAnalysis.result_id
        ).filter(
            (ContentAnalysis.scene_description == None) |
            (ContentAnalysis.scene_description == '')
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def process_image(self, session, image):
        """Process a single image"""
        try:
            # Check if file exists
            if not Path(image.file_path).exists():
                print(f"   ⚠️ File not found: {image.file_path}")
                self.error_count += 1
                return False

            # Analyze image
            start_time = time.time()
            result = self.analyzer.analyze_image(image.file_path)
            processing_time = time.time() - start_time

            # Check if analysis exists
            analysis = session.query(ContentAnalysis).filter_by(
                result_id=image.result_id
            ).first()

            if not analysis:
                # Create new analysis
                analysis = ContentAnalysis(
                    result_id=image.result_id,
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
                    confidence_score=result.get('confidence_score', 0.0),
                    processing_time=processing_time,
                    analysis_model='llava',
                    analyzed_at=datetime.utcnow()
                )
                session.add(analysis)
            else:
                # Update existing analysis
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
                analysis.confidence_score = result.get('confidence_score', 0.0)
                analysis.processing_time = processing_time
                analysis.analysis_model = 'llava'
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
            # Get missing images
            print("\n📊 Checking for images missing LLaVA analysis...")
            images = self.get_missing_images(session, limit=limit)
            total = len(images)

            if total == 0:
                print("✅ All images already have LLaVA analysis!")
                return

            print(f"📋 Found {total} images to process")

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
                            f"Processing (✓{self.processed_count} ✗{self.error_count})"
                        )

                    # Commit batch
                    session.commit()

                    # Show batch stats
                    batch_time = time.time() - batch_start
                    avg_time = batch_time / len(batch)
                    print(f"\n   Batch {i//self.batch_size + 1}: {len(batch)} images in {batch_time:.1f}s ({avg_time:.1f}s/image)")

            # Final stats
            total_time = time.time() - start_time
            print(f"\n📈 Processing Complete!")
            print(f"   ✓ Processed: {self.processed_count}")
            print(f"   ✗ Errors: {self.error_count}")
            print(f"   ⏱️ Total time: {total_time:.1f}s")
            print(f"   📊 Average: {total_time/max(self.processed_count,1):.1f}s per image")

        finally:
            session.close()

def main():
    parser = argparse.ArgumentParser(description="Process images with LLaVA")
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size')
    parser.add_argument('--limit', type=int, help='Limit number of images')
    parser.add_argument('--test', action='store_true', help='Test mode (5 images)')
    args = parser.parse_args()

    processor = LLaVABatchProcessor(batch_size=args.batch_size)
    processor.run(limit=args.limit, test_mode=args.test)

if __name__ == "__main__":
    main()