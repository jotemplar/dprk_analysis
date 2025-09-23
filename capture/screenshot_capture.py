"""Screenshot capture module using Playwright"""

import os
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from playwright.async_api import async_playwright, Browser, Page
from dotenv import load_dotenv

load_dotenv()

class ScreenshotCapture:
    """Capture screenshots of web pages and search results"""

    def __init__(self):
        self.screenshot_path = Path(os.getenv("SCREENSHOT_STORAGE_PATH",
                                              "/Volumes/X5/_CODE_PROJECTS/DPRK/captured_data/screenshots"))
        self.screenshot_path.mkdir(parents=True, exist_ok=True)
        self.browser: Optional[Browser] = None
        self.timeout = int(os.getenv("SCREENSHOT_TIMEOUT", 60)) * 1000  # Convert to ms

    async def initialize(self):
        """Initialize Playwright browser"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )

    async def close(self):
        """Close browser instance"""
        if self.browser:
            await self.browser.close()
            self.browser = None

    async def capture_page_screenshot(self, url: str, full_page: bool = True) -> Optional[str]:
        """
        Capture screenshot of a web page

        Args:
            url: URL to capture
            full_page: Whether to capture full page or just viewport

        Returns:
            Path to saved screenshot or None if failed
        """
        await self.initialize()

        try:
            # Create new page
            page = await self.browser.new_page(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            # Navigate to URL
            await page.goto(url, wait_until="networkidle", timeout=self.timeout)

            # Wait for images to load
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)  # Additional wait for dynamic content

            # Generate filename
            date_str = datetime.now().strftime("%Y-%m-%d")
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{date_str}_{url_hash}_{timestamp}.png"

            # Create date-based subdirectory
            date_dir = self.screenshot_path / date_str
            date_dir.mkdir(exist_ok=True)
            filepath = date_dir / filename

            # Take screenshot
            await page.screenshot(
                path=str(filepath),
                full_page=full_page,
                type="png"
            )

            await page.close()

            print(f"   ✓ Screenshot saved: {filename}")
            return str(filepath)

        except Exception as e:
            print(f"   ✗ Failed to capture screenshot of {url}: {e}")
            if 'page' in locals():
                await page.close()
            return None

    async def capture_search_results(self, query: str, results_html: str) -> Optional[str]:
        """
        Capture screenshot of search results by rendering HTML

        Args:
            query: Search query for filename
            results_html: HTML content of search results

        Returns:
            Path to saved screenshot or None if failed
        """
        await self.initialize()

        try:
            page = await self.browser.new_page(
                viewport={"width": 1920, "height": 1080}
            )

            # Set HTML content
            await page.set_content(results_html)
            await page.wait_for_load_state("domcontentloaded")

            # Generate filename
            date_str = datetime.now().strftime("%Y-%m-%d")
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"search_{date_str}_{query_hash}_{timestamp}.png"

            # Create subdirectory
            date_dir = self.screenshot_path / date_str / "search_results"
            date_dir.mkdir(parents=True, exist_ok=True)
            filepath = date_dir / filename

            # Take screenshot
            await page.screenshot(
                path=str(filepath),
                full_page=True,
                type="png"
            )

            await page.close()

            print(f"   ✓ Search results screenshot saved: {filename}")
            return str(filepath)

        except Exception as e:
            print(f"   ✗ Failed to capture search results: {e}")
            if 'page' in locals():
                await page.close()
            return None

    async def capture_image_gallery(self, image_urls: List[str], query: str) -> Optional[str]:
        """
        Create and capture a gallery view of multiple images

        Args:
            image_urls: List of image URLs to display
            query: Search query for context

        Returns:
            Path to gallery screenshot
        """
        await self.initialize()

        try:
            # Create HTML gallery
            gallery_html = self._create_gallery_html(image_urls, query)

            page = await self.browser.new_page(
                viewport={"width": 1920, "height": 1080}
            )

            await page.set_content(gallery_html)
            await page.wait_for_load_state("networkidle")

            # Wait for images to load
            await asyncio.sleep(3)

            # Generate filename
            date_str = datetime.now().strftime("%Y-%m-%d")
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"gallery_{date_str}_{query_hash}_{timestamp}.png"

            # Create subdirectory
            date_dir = self.screenshot_path / date_str / "galleries"
            date_dir.mkdir(parents=True, exist_ok=True)
            filepath = date_dir / filename

            # Take screenshot
            await page.screenshot(
                path=str(filepath),
                full_page=True,
                type="png"
            )

            await page.close()

            print(f"   ✓ Gallery screenshot saved: {filename}")
            return str(filepath)

        except Exception as e:
            print(f"   ✗ Failed to capture gallery: {e}")
            if 'page' in locals():
                await page.close()
            return None

    def _create_gallery_html(self, image_urls: List[str], query: str) -> str:
        """Create HTML for image gallery"""
        images_html = ""
        for i, url in enumerate(image_urls[:20]):  # Limit to 20 images
            images_html += f'''
            <div class="image-item">
                <img src="{url}" alt="Image {i+1}" onerror="this.style.display='none'">
                <div class="image-number">{i+1}</div>
            </div>
            '''

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Image Gallery: {query}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f5f5f5;
                    padding: 20px;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 20px;
                }}
                .gallery {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 20px;
                    margin-top: 20px;
                }}
                .image-item {{
                    position: relative;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .image-item img {{
                    width: 100%;
                    height: 250px;
                    object-fit: cover;
                }}
                .image-number {{
                    position: absolute;
                    top: 10px;
                    left: 10px;
                    background: rgba(0,0,0,0.7);
                    color: white;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-size: 14px;
                }}
                .query-info {{
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="query-info">
                <h1>Search Query: {query}</h1>
                <p>Captured: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Total Images: {len(image_urls)}</p>
            </div>
            <div class="gallery">
                {images_html}
            </div>
        </body>
        </html>
        """

    async def batch_capture_screenshots(self, urls: List[str], max_concurrent: int = 3) -> Dict[str, str]:
        """
        Capture multiple screenshots concurrently

        Args:
            urls: List of URLs to capture
            max_concurrent: Maximum concurrent captures

        Returns:
            Dictionary mapping URLs to screenshot paths
        """
        await self.initialize()

        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def capture_with_semaphore(url):
            async with semaphore:
                path = await self.capture_page_screenshot(url)
                return url, path

        tasks = [capture_with_semaphore(url) for url in urls]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, tuple):
                url, path = result
                if path:
                    results[url] = path
            else:
                print(f"   ✗ Error in batch capture: {result}")

        return results