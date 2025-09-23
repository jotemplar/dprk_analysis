#!/usr/bin/env python3
"""Update dashboard data with both image and article analysis"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from database.connection import get_session
from sqlalchemy import text

def generate_dashboard_data():
    """Generate comprehensive dashboard data"""

    session = get_session()

    print("Generating dashboard data...")

    # Get image statistics
    total_images = session.execute(text("SELECT COUNT(*) FROM dprk_images")).scalar()

    llava_count = session.execute(text("""
        SELECT COUNT(DISTINCT image_id) FROM image_analysis WHERE model = 'llava'
    """)).scalar()

    gemma_count = session.execute(text("""
        SELECT COUNT(DISTINCT image_id) FROM image_analysis WHERE model = 'gemma2:vision'
    """)).scalar()

    total_analyses = session.execute(text("""
        SELECT COUNT(DISTINCT image_id) FROM image_analysis
    """)).scalar()

    # Get detailed image data
    image_query = session.execute(text("""
        WITH latest_analyses AS (
            SELECT
                image_id,
                model,
                concern_level,
                environment_type,
                activity_type,
                personnel_count,
                scene_description,
                concern_indicators,
                analyzed_at,
                ROW_NUMBER() OVER (PARTITION BY image_id, model ORDER BY analyzed_at DESC) as rn
            FROM image_analysis
        )
        SELECT
            i.id,
            i.file_name,
            i.file_path,
            i.thumbnail,
            MAX(CASE WHEN la.model = 'llava' THEN la.concern_level END) as llava_concern,
            MAX(CASE WHEN la.model = 'gemma2:vision' THEN la.concern_level END) as gemma_concern,
            MAX(CASE WHEN la.model = 'llava' THEN la.scene_description END) as llava_description,
            MAX(CASE WHEN la.model = 'gemma2:vision' THEN la.scene_description END) as gemma_description,
            MAX(CASE WHEN la.model = 'llava' THEN la.environment_type END) as environment_type,
            MAX(CASE WHEN la.model = 'llava' THEN la.activity_type END) as activity_type,
            MAX(CASE WHEN la.model = 'llava' THEN la.personnel_count END) as personnel_count,
            MAX(CASE WHEN la.model = 'llava' THEN la.concern_indicators END) as llava_indicators,
            MAX(CASE WHEN la.model = 'gemma2:vision' THEN la.concern_indicators END) as gemma_indicators,
            CASE WHEN MAX(CASE WHEN la.model = 'llava' THEN 1 ELSE 0 END) = 1 THEN true ELSE false END as has_llava,
            CASE WHEN MAX(CASE WHEN la.model = 'gemma2:vision' THEN 1 ELSE 0 END) = 1 THEN true ELSE false END as has_gemma
        FROM dprk_images i
        LEFT JOIN latest_analyses la ON i.id = la.image_id AND la.rn = 1
        GROUP BY i.id, i.file_name, i.file_path, i.thumbnail
        ORDER BY i.id DESC
        LIMIT 500
    """))

    image_data = []
    for row in image_query:
        # Use the highest concern level from either model
        concern_level = row.llava_concern or row.gemma_concern or 'unknown'
        if row.llava_concern and row.gemma_concern:
            # If both exist, use the more severe one
            concern_priority = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'unknown': 0}
            if concern_priority.get(row.gemma_concern, 0) > concern_priority.get(row.llava_concern, 0):
                concern_level = row.gemma_concern
            else:
                concern_level = row.llava_concern

        image_data.append({
            'id': row.id,
            'file_name': row.file_name,
            'thumbnail': row.thumbnail,
            'concern_level': concern_level,
            'llava_concern_level': row.llava_concern,
            'gemma_concern_level': row.gemma_concern,
            'scene_description': row.llava_description,
            'gemma_description': row.gemma_description,
            'environment_type': row.environment_type or 'unknown',
            'activity_type': row.activity_type or 'unknown',
            'personnel_count': row.personnel_count or 0,
            'concern_indicators': row.llava_indicators or [],
            'gemma_indicators': row.gemma_indicators or [],
            'has_llava': row.has_llava,
            'has_gemma': row.has_gemma
        })

    dashboard_data = {
        'stats': {
            'total_images': total_images,
            'total_analyses': total_analyses,
            'llava_count': llava_count,
            'gemma_count': gemma_count
        },
        'data': image_data,
        'generated_at': datetime.now().isoformat()
    }

    # Save to file
    with open('dashboard_data.json', 'w') as f:
        json.dump(dashboard_data, f, indent=2)

    print(f"Dashboard data generated:")
    print(f"  Total images: {total_images}")
    print(f"  Total analyses: {total_analyses}")
    print(f"  LLaVA analyses: {llava_count}")
    print(f"  Gemma analyses: {gemma_count}")
    print(f"  Data entries: {len(image_data)}")

    session.close()

    return dashboard_data

if __name__ == "__main__":
    generate_dashboard_data()