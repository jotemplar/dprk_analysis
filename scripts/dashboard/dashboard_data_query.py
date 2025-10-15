#!/usr/bin/env python3
"""Query database for dashboard data"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import get_session
from database.models import CapturedImage, ContentAnalysis, SearchResult, SearchQuery
from sqlalchemy.orm import joinedload
import json
import base64
from PIL import Image
import io

def get_dashboard_data():
    """Get data for dashboard"""
    session = get_session()

    try:
        # Get total images analyzed
        total_images = session.query(CapturedImage).count()
        print(f"Total images: {total_images}")

        # Get images with analysis
        images_with_analysis = session.query(CapturedImage)\
            .join(SearchResult)\
            .join(ContentAnalysis)\
            .options(
                joinedload(CapturedImage.search_result).joinedload(SearchResult.content_analysis),
                joinedload(CapturedImage.search_result).joinedload(SearchResult.query)
            )\
            .limit(50)\
            .all()

        print(f"Images with analysis: {len(images_with_analysis)}")

        # Get analysis statistics
        analysis_counts = session.query(ContentAnalysis.concern_level,
                                      session.query(ContentAnalysis).filter_by(concern_level=ContentAnalysis.concern_level).count())\
                               .group_by(ContentAnalysis.concern_level)\
                               .all()

        print("Analysis counts by concern level:")
        for level, count in analysis_counts:
            print(f"  {level}: {count}")

        # Get sample data structure
        if images_with_analysis:
            sample = images_with_analysis[0]
            print(f"\nSample image: {sample.file_name}")
            print(f"File path: {sample.file_path}")
            if sample.search_result.content_analysis:
                analysis = sample.search_result.content_analysis
                print(f"Scene description: {analysis.scene_description[:100] if analysis.scene_description else 'None'}...")
                print(f"Concern level: {analysis.concern_level}")
                print(f"Gemma description: {analysis.gemma_description[:100] if analysis.gemma_description else 'None'}...")
                print(f"Gemma concern level: {analysis.gemma_concern_level}")
                print(f"Ensemble concern level: {analysis.ensemble_concern_level}")

        # Generate JSON data for dashboard
        dashboard_data = {
            "stats": {
                "total_images": total_images,
                "analyzed_images": len(images_with_analysis),
                "concern_levels": dict(analysis_counts)
            },
            "images": []
        }

        for img in images_with_analysis[:20]:  # Limit to 20 for now
            analysis = img.search_result.content_analysis

            # Try to create thumbnail
            thumbnail_base64 = None
            try:
                if os.path.exists(img.file_path):
                    with Image.open(img.file_path) as pil_img:
                        # Create thumbnail
                        pil_img.thumbnail((200, 200))
                        img_buffer = io.BytesIO()
                        pil_img.save(img_buffer, format='JPEG')
                        img_buffer.seek(0)
                        thumbnail_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            except Exception as e:
                print(f"Error creating thumbnail for {img.file_path}: {e}")

            image_data = {
                "id": img.id,
                "file_name": img.file_name,
                "file_path": img.file_path,
                "thumbnail": thumbnail_base64,
                "search_term": img.search_result.query.search_term if img.search_result.query else None,
                "category": img.search_result.query.category if img.search_result.query else None,
                "source_url": img.search_result.url if img.search_result else None,
                "page_url": img.search_result.page_url if img.search_result else None,
                "source_domain": img.search_result.source_domain if img.search_result else None,
                "analysis": {
                    "scene_description": analysis.scene_description,
                    "concern_level": analysis.concern_level,
                    "concern_indicators": analysis.concern_indicators or [],
                    "gemma_description": analysis.gemma_description,
                    "gemma_concern_level": analysis.gemma_concern_level,
                    "gemma_indicators": analysis.gemma_indicators or [],
                    "ensemble_concern_level": analysis.ensemble_concern_level,
                    "ensemble_confidence": analysis.ensemble_confidence,
                    "personnel_count": analysis.personnel_count,
                    "activity_type": analysis.activity_type,
                    "environment_type": analysis.environment_type
                } if analysis else None
            }
            dashboard_data["images"].append(image_data)

        # Save to JSON file
        with open("dashboard_data.json", "w") as f:
            json.dump(dashboard_data, f, indent=2, default=str)

        print(f"\nSaved dashboard data with {len(dashboard_data['images'])} images to dashboard_data.json")
        return dashboard_data

    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        session.close()

if __name__ == "__main__":
    get_dashboard_data()