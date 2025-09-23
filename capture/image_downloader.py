"""Image download and storage module"""

import os
import hashlib
import aiohttp
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse, unquote
from PIL import Image, ExifTags
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

class ImageDownloader:
    """Download and store images with metadata extraction"""

    def __init__(self):
        self.image_path = Path(os.getenv("IMAGE_STORAGE_PATH",
                                         "/Volumes/X5/_CODE_PROJECTS/DPRK/captured_data/images"))
        self.image_path.mkdir(parents=True, exist_ok=True)
        self.timeout = int(os.getenv("IMAGE_DOWNLOAD_TIMEOUT", 30))
        self.max_file_size = 50 * 1024 * 1024  # 50MB max
        self.valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    async def download_image(self, image_url: str, category: str = "general") -> Optional[Dict]:
        """
        Download a single image and extract metadata

        Args:
            image_url: URL of the image to download
            category: Category for organizing images

        Returns:
            Dictionary with image info and file path, or None if failed
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    image_url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                ) as response:

                    # Check response status
                    if response.status != 200:
                        print(f"   ✗ HTTP {response.status} for {image_url[:50]}...")
                        return None

                    # Check content type
                    content_type = response.headers.get('Content-Type', '')
                    if not content_type.startswith('image/'):
                        print(f"   ✗ Not an image: {content_type}")
                        return None

                    # Check file size
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > self.max_file_size:
                        print(f"   ✗ Image too large: {int(content_length) / 1024 / 1024:.1f}MB")
                        return None

                    # Download image data
                    image_data = await response.read()

                    # Process and save image
                    return await self._process_and_save_image(image_data, image_url, category)

        except asyncio.TimeoutError:
            print(f"   ✗ Timeout downloading image from {image_url[:50]}...")
        except Exception as e:
            print(f"   ✗ Error downloading image: {e}")

        return None

    async def _process_and_save_image(self, image_data: bytes, url: str, category: str) -> Optional[Dict]:
        """
        Process image data and save to disk

        Args:
            image_data: Raw image bytes
            url: Original URL for filename generation
            category: Category for organization

        Returns:
            Dictionary with image metadata
        """
        try:
            # Open image with PIL
            img = Image.open(BytesIO(image_data))

            # Extract basic metadata
            width, height = img.size
            format_name = img.format or 'UNKNOWN'

            # Extract EXIF data if available
            exif_data = self._extract_exif(img)

            # Generate filename
            date_str = datetime.now().strftime("%Y-%m-%d")
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            timestamp = datetime.now().strftime("%H%M%S")

            # Determine extension
            ext = self._get_extension_from_format(format_name)
            filename = f"{date_str}_{category}_{url_hash}_{timestamp}{ext}"

            # Create category subdirectory
            category_dir = self.image_path / date_str / category
            category_dir.mkdir(parents=True, exist_ok=True)
            filepath = category_dir / filename

            # Save image
            if format_name == 'WEBP':
                # Convert WebP to PNG for better compatibility
                img.save(str(filepath), 'PNG')
                format_name = 'PNG'
                ext = '.png'
            else:
                img.save(str(filepath), format_name)

            # Calculate file size
            file_size = filepath.stat().st_size

            print(f"   ✓ Image saved: {filename} ({width}x{height}, {file_size/1024:.1f}KB)")

            return {
                'file_path': str(filepath),
                'file_name': filename,
                'file_size': file_size,
                'image_width': width,
                'image_height': height,
                'image_format': format_name.lower(),
                'download_url': url,
                'exif_data': exif_data,
                'capture_date': exif_data.get('DateTimeOriginal') if exif_data else None,
                'location_data': self._extract_gps(exif_data) if exif_data else None
            }

        except Exception as e:
            print(f"   ✗ Error processing image: {e}")
            return None

    def _extract_exif(self, img: Image.Image) -> Optional[Dict]:
        """Extract EXIF data from image"""
        try:
            exifdata = img.getexif()
            if not exifdata:
                return None

            exif = {}
            for tag_id, value in exifdata.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                # Convert values to JSON-serializable types
                exif[tag] = self._make_json_serializable(value)

            return exif if exif else None
        except:
            return None

    def _make_json_serializable(self, value):
        """Convert non-JSON-serializable types to serializable equivalents"""
        from PIL.ExifTags import IFD
        
        # Handle IFDRational objects
        if hasattr(value, 'numerator') and hasattr(value, 'denominator'):
            # This is likely an IFDRational - convert to float
            try:
                return float(value)
            except (ValueError, TypeError, ZeroDivisionError):
                return str(value)
        
        # Handle lists/tuples that might contain IFDRational objects
        elif isinstance(value, (list, tuple)):
            return [self._make_json_serializable(item) for item in value]
        
        # Handle dictionaries
        elif isinstance(value, dict):
            return {k: self._make_json_serializable(v) for k, v in value.items()}
        
        # Handle bytes objects
        elif isinstance(value, bytes):
            try:
                return value.decode('utf-8', errors='ignore')
            except:
                return str(value)
        
        # Handle other non-serializable types
        elif not isinstance(value, (str, int, float, bool, type(None))):
            try:
                # Try to convert to string as fallback
                return str(value)
            except:
                return None
        
        # Value is already JSON-serializable
        return value

    def _extract_gps(self, exif_data: Dict) -> Optional[Dict]:
        """Extract GPS coordinates from EXIF data"""
        if not exif_data:
            return None

        gps_info = exif_data.get('GPSInfo')
        if not gps_info:
            return None

        try:
            # Extract GPS coordinates
            def convert_to_degrees(value):
                # Handle potential IFDRational objects in GPS coordinates
                if isinstance(value, (list, tuple)) and len(value) >= 3:
                    d, m, s = value[:3]
                    # Convert each component to float if it's not already
                    d = float(d) if hasattr(d, 'numerator') else d
                    m = float(m) if hasattr(m, 'numerator') else m
                    s = float(s) if hasattr(s, 'numerator') else s
                    return d + (m / 60.0) + (s / 3600.0)
                return 0.0

            lat = gps_info.get(2)  # GPSLatitude
            lat_ref = gps_info.get(1)  # GPSLatitudeRef
            lon = gps_info.get(4)  # GPSLongitude
            lon_ref = gps_info.get(3)  # GPSLongitudeRef

            if lat and lon:
                lat_degrees = convert_to_degrees(lat)
                if lat_ref == 'S':
                    lat_degrees = -lat_degrees

                lon_degrees = convert_to_degrees(lon)
                if lon_ref == 'W':
                    lon_degrees = -lon_degrees

                return {
                    'latitude': lat_degrees,
                    'longitude': lon_degrees
                }
        except:
            pass

        return None

    def _get_extension_from_format(self, format_name: str) -> str:
        """Get file extension from PIL format name"""
        format_extensions = {
            'JPEG': '.jpg',
            'PNG': '.png',
            'GIF': '.gif',
            'WEBP': '.webp',
            'BMP': '.bmp'
        }
        return format_extensions.get(format_name, '.jpg')

    async def download_images_batch(self, image_urls: List[Tuple[str, str]], max_concurrent: int = 5) -> List[Dict]:
        """
        Download multiple images concurrently

        Args:
            image_urls: List of (url, category) tuples
            max_concurrent: Maximum concurrent downloads

        Returns:
            List of successfully downloaded image metadata
        """
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_with_semaphore(url, category):
            async with semaphore:
                return await self.download_image(url, category)

        tasks = [download_with_semaphore(url, cat) for url, cat in image_urls]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, dict) and result:
                results.append(result)
            elif isinstance(result, Exception):
                print(f"   ✗ Error in batch download: {result}")

        return results

    async def download_from_webpage(self, page_url: str, category: str = "general") -> List[Dict]:
        """
        Extract and download images from a webpage

        Args:
            page_url: URL of the webpage
            category: Category for organizing images

        Returns:
            List of downloaded image metadata
        """
        try:
            # This would typically use BeautifulSoup or similar to extract image URLs
            # For now, returning empty list as placeholder
            # In production, would scrape the page for img tags and download them
            print(f"   ⚠ Webpage image extraction not yet implemented")
            return []

        except Exception as e:
            print(f"   ✗ Error extracting images from webpage: {e}")
            return []

    def cleanup_old_images(self, days_to_keep: int = 30):
        """
        Remove images older than specified days

        Args:
            days_to_keep: Number of days to keep images
        """
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)

        for root, dirs, files in os.walk(self.image_path):
            for file in files:
                filepath = Path(root) / file
                if filepath.stat().st_mtime < cutoff_date:
                    filepath.unlink()
                    print(f"   Deleted old image: {file}")

    def get_storage_statistics(self) -> Dict:
        """Get statistics about stored images"""
        total_size = 0
        total_count = 0
        format_counts = {}

        for root, dirs, files in os.walk(self.image_path):
            for file in files:
                filepath = Path(root) / file
                total_size += filepath.stat().st_size
                total_count += 1

                ext = filepath.suffix.lower()
                format_counts[ext] = format_counts.get(ext, 0) + 1

        return {
            'total_images': total_count,
            'total_size_mb': total_size / 1024 / 1024,
            'format_distribution': format_counts
        }