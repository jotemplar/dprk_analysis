#!/usr/bin/env python3
"""Generate improved dashboard data with URLs and proper structure"""

import json
import base64
from PIL import Image
import io
from pathlib import Path
from database.connection import get_session
from database.models import CapturedImage, ContentAnalysis, SearchResult
from sqlalchemy import func

def create_thumbnail(image_path, max_size=(200, 200)):
    """Create a base64 encoded thumbnail"""
    try:
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background

            img.thumbnail(max_size)
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        print(f"Error creating thumbnail for {image_path}: {e}")
        return None

def main():
    session = get_session()

    try:
        # Get statistics
        total_images = session.query(CapturedImage).count()
        total_analyses = session.query(ContentAnalysis).count()

        # Count analyses by model
        llava_count = session.query(ContentAnalysis).filter(
            ContentAnalysis.scene_description != None,
            ContentAnalysis.scene_description != ''
        ).count()

        gemma_count = session.query(ContentAnalysis).filter(
            ContentAnalysis.gemma_description != None,
            ContentAnalysis.gemma_description != ''
        ).count()

        print(f"📊 Statistics:")
        print(f"   Total images: {total_images}")
        print(f"   Total analyses: {total_analyses}")
        print(f"   LLaVA processed: {llava_count}")
        print(f"   Gemma processed: {gemma_count}")

        # Get distinct images with analysis (avoiding duplicates)
        # First get unique result_ids
        unique_result_ids = session.query(
            CapturedImage.result_id
        ).join(
            ContentAnalysis, CapturedImage.result_id == ContentAnalysis.result_id
        ).distinct().limit(100).subquery()

        # Then get full data for those result_ids
        images_query = session.query(
            CapturedImage,
            ContentAnalysis,
            SearchResult
        ).join(
            ContentAnalysis, CapturedImage.result_id == ContentAnalysis.result_id
        ).join(
            SearchResult, CapturedImage.result_id == SearchResult.id
        ).filter(
            CapturedImage.result_id.in_(session.query(unique_result_ids))
        ).distinct(CapturedImage.result_id)

        images_data = []

        for img, analysis, result in images_query:
            # Check if file exists
            if not Path(img.file_path).exists():
                continue

            # Create thumbnail
            thumbnail = create_thumbnail(img.file_path)

            # Prepare image data
            img_data = {
                "id": img.id,
                "file_name": img.file_name,
                "thumbnail": thumbnail,
                "source_url": result.url,
                "page_url": result.page_url,
                "source_domain": result.source_domain,
                # Analysis data
                "scene_description": analysis.scene_description,
                "concern_level": analysis.concern_level,
                "gemma_description": analysis.gemma_description,
                "gemma_concern_level": analysis.gemma_concern_level,
                "personnel_count": analysis.personnel_count or 0,
                "has_llava": bool(analysis.scene_description),
                "has_gemma": bool(analysis.gemma_description)
            }

            images_data.append(img_data)

        print(f"📸 Collected {len(images_data)} unique images with analysis")

        # Create dashboard data
        dashboard_data = {
            "stats": {
                "total_images": total_images,
                "total_analyses": total_analyses,
                "llava_count": llava_count,
                "gemma_count": gemma_count
            },
            "data": images_data
        }

        # Save to JSON
        with open('dashboard_data.json', 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved dashboard data to dashboard_data.json")
        print(f"   Images with thumbnails: {len([d for d in images_data if d['thumbnail']])}")
        print(f"   Images with URLs: {len([d for d in images_data if d['source_url']])}")

    finally:
        session.close()

if __name__ == "__main__":
    main()