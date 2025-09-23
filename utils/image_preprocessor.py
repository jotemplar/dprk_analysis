#!/usr/bin/env python3
"""Image preprocessing utility for standardizing images before model analysis"""

import os
import io
import base64
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import numpy as np

class ImagePreprocessor:
    """Standardize images for optimal model performance"""

    def __init__(self, max_size: int = 896, cache_dir: Optional[str] = None):
        """
        Initialize the preprocessor

        Args:
            max_size: Maximum dimension for images (896 optimal for Gemma)
            cache_dir: Directory to cache preprocessed images
        """
        self.max_size = max_size
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cached_data/standardized_images")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, image_path: str) -> Path:
        """Generate cache path for preprocessed image"""
        # Create hash of original path + max_size
        hash_input = f"{image_path}_{self.max_size}"
        file_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        return self.cache_dir / f"{file_hash}_{self.max_size}.jpg"

    def standardize_image(self, image_path: str, use_cache: bool = True) -> str:
        """
        Standardize image to max_size preserving aspect ratio

        Args:
            image_path: Path to the image file
            use_cache: Whether to use cached version if available

        Returns:
            Base64 encoded standardized image
        """
        # Check cache first
        if use_cache:
            cache_path = self.get_cache_path(image_path)
            if cache_path.exists():
                with open(cache_path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')

        try:
            # Open and process image
            img = Image.open(image_path)

            # Convert to RGB if needed (removes alpha channel, converts grayscale)
            if img.mode not in ('RGB', 'L'):
                if img.mode == 'RGBA':
                    # Create white background for transparent images
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
                    img = background
                else:
                    img = img.convert('RGB')

            # Get original dimensions
            orig_width, orig_height = img.size

            # Resize only if larger than max_size
            if orig_width > self.max_size or orig_height > self.max_size:
                # Calculate new size preserving aspect ratio
                img.thumbnail((self.max_size, self.max_size), Image.Resampling.LANCZOS)

            # Save to bytes
            buffer = io.BytesIO()

            # Use JPEG for RGB, PNG for grayscale to preserve quality
            if img.mode == 'L':
                img.save(buffer, format='PNG', optimize=True)
            else:
                img.save(buffer, format='JPEG', quality=95, optimize=True)

            image_bytes = buffer.getvalue()

            # Save to cache
            if use_cache:
                cache_path = self.get_cache_path(image_path)
                with open(cache_path, 'wb') as f:
                    f.write(image_bytes)

            return base64.b64encode(image_bytes).decode('utf-8')

        except Exception as e:
            print(f"Error preprocessing {image_path}: {e}")
            # Fall back to reading original
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')

    def get_image_info(self, image_path: str) -> dict:
        """Get information about an image"""
        try:
            img = Image.open(image_path)
            orig_size = img.size

            # Calculate standardized size
            if orig_size[0] > self.max_size or orig_size[1] > self.max_size:
                img.thumbnail((self.max_size, self.max_size), Image.Resampling.LANCZOS)

            new_size = img.size

            return {
                'original_size': orig_size,
                'standardized_size': new_size,
                'mode': img.mode,
                'format': img.format,
                'reduction_factor': round(orig_size[0] / new_size[0], 2) if new_size[0] > 0 else 1.0,
                'file_size_kb': os.path.getsize(image_path) / 1024
            }
        except Exception as e:
            return {'error': str(e)}

    def batch_preprocess(self, image_paths: list, progress_callback=None) -> list:
        """
        Preprocess multiple images

        Args:
            image_paths: List of image paths
            progress_callback: Optional callback function for progress updates

        Returns:
            List of base64 encoded images
        """
        results = []
        total = len(image_paths)

        for i, path in enumerate(image_paths):
            if progress_callback:
                progress_callback(i + 1, total)

            try:
                encoded = self.standardize_image(path)
                results.append({
                    'path': path,
                    'encoded': encoded,
                    'success': True
                })
            except Exception as e:
                results.append({
                    'path': path,
                    'error': str(e),
                    'success': False
                })

        return results

    def clear_cache(self):
        """Clear the cache directory"""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            print(f"Cache cleared: {self.cache_dir}")

    def get_cache_stats(self) -> dict:
        """Get statistics about cached images"""
        if not self.cache_dir.exists():
            return {'cached_images': 0, 'cache_size_mb': 0}

        files = list(self.cache_dir.glob('*.jpg')) + list(self.cache_dir.glob('*.png'))
        total_size = sum(f.stat().st_size for f in files)

        return {
            'cached_images': len(files),
            'cache_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_dir': str(self.cache_dir)
        }


def test_preprocessor():
    """Test the image preprocessor"""
    from database.connection import get_session
    from database.models import CapturedImage

    session = get_session()

    # Get a sample of images
    images = session.query(CapturedImage).filter(
        CapturedImage.file_path.isnot(None)
    ).limit(5).all()

    if not images:
        print("No images found for testing")
        return

    preprocessor = ImagePreprocessor(max_size=896)

    print("="*60)
    print("IMAGE PREPROCESSOR TEST")
    print("="*60)

    for img in images:
        print(f"\nProcessing: {img.file_path}")
        info_before = preprocessor.get_image_info(img.file_path)
        print(f"  Original: {info_before['original_size']} ({info_before['file_size_kb']:.1f} KB)")

        # Standardize
        encoded = preprocessor.standardize_image(img.file_path)
        print(f"  Encoded length: {len(encoded)} chars")

        info_after = preprocessor.get_image_info(img.file_path)
        print(f"  Standardized: {info_after['standardized_size']}")
        print(f"  Reduction factor: {info_after['reduction_factor']}x")

    # Show cache stats
    stats = preprocessor.get_cache_stats()
    print(f"\nCache stats: {stats}")

    session.close()


if __name__ == "__main__":
    test_preprocessor()