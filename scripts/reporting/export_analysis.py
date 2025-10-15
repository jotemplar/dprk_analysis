#!/usr/bin/env python3
"""Export analyzed images and data to spreadsheet"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from database.connection import get_session
from database.models import (
    SearchQuery, SearchResult, CapturedImage,
    Screenshot, ContentAnalysis
)
from sqlalchemy.orm import joinedload

def export_to_excel():
    """Export all analysis data to Excel spreadsheet"""
    session = get_session()

    print("=" * 60)
    print("EXPORTING DPRK IMAGE ANALYSIS TO SPREADSHEET")
    print("=" * 60)

    try:
        # Query all analyzed images with their relationships
        print("\n📊 Gathering analysis data...")

        # Get all content analyses with related data
        analyses = session.query(ContentAnalysis).join(
            SearchResult
        ).join(
            CapturedImage
        ).join(
            SearchQuery
        ).all()

        print(f"   Found {len(analyses)} analyzed images")

        # Build data for export
        data = []
        for analysis in analyses:
            # Get related objects
            result = session.query(SearchResult).filter_by(id=analysis.result_id).first()
            captured = session.query(CapturedImage).filter_by(result_id=analysis.result_id).first()
            query = session.query(SearchQuery).filter_by(id=result.query_id).first() if result else None

            if result and captured and query:
                row = {
                    # Search Information
                    'Search Query': query.search_term[:100],
                    'Query Language': query.language,
                    'Query Category': query.category,

                    # Source Information
                    'Source URL': result.url,
                    'Source Title': result.title,
                    'Source Domain': result.source_domain,

                    # Image Information
                    'Image URL': result.image_url,
                    'Image File': Path(captured.file_path).name if captured.file_path else '',
                    'Image Path': captured.file_path,
                    'Image Size (KB)': round(captured.file_size / 1024, 1) if captured.file_size else 0,
                    'Image Dimensions': f"{captured.image_width}x{captured.image_height}" if captured.image_width else '',
                    'Image Format': captured.image_format,
                    'Capture Date': captured.captured_at.replace(tzinfo=None) if captured.captured_at else None,

                    # Analysis Results
                    'Scene Description': analysis.scene_description[:500] if analysis.scene_description else '',
                    'Location Assessment': analysis.location_assessment[:200] if analysis.location_assessment else '',
                    'Environment Type': analysis.environment_type,
                    'Personnel Count': analysis.personnel_count,
                    'Personnel Types': ', '.join(analysis.personnel_types) if analysis.personnel_types else '',
                    'Uniform Identification': analysis.uniform_identification[:200] if analysis.uniform_identification else '',
                    'Activity Type': analysis.activity_type,
                    'Activity Description': analysis.activity_description[:500] if analysis.activity_description else '',
                    'Concern Level': analysis.concern_level,
                    'Concern Indicators': ' | '.join(analysis.concern_indicators[:3]) if analysis.concern_indicators else '',
                    'Supervision Present': 'Yes' if analysis.supervision_present else 'No',
                    'Restriction Indicators': ' | '.join(analysis.restriction_indicators[:3]) if analysis.restriction_indicators else '',
                    'Confidence Score': round(analysis.confidence_score, 2) if analysis.confidence_score else 0,
                    'Analysis Model': analysis.analysis_model,
                    'Processing Time (s)': round(analysis.processing_time, 1) if analysis.processing_time else 0,
                    'Analysis Date': analysis.analyzed_at.replace(tzinfo=None) if analysis.analyzed_at else None,

                    # GPS/Location from EXIF
                    'GPS Coordinates': '',
                    'EXIF Location': ''
                }

                # Extract GPS if available
                if captured.location_data:
                    lat = captured.location_data.get('latitude')
                    lon = captured.location_data.get('longitude')
                    if lat and lon:
                        row['GPS Coordinates'] = f"{lat:.6f}, {lon:.6f}"
                        row['EXIF Location'] = f"Lat: {lat:.6f}, Lon: {lon:.6f}"

                data.append(row)

        # Create DataFrame
        df = pd.DataFrame(data)

        # Sort by concern level (critical -> high -> medium -> low)
        concern_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'unknown': 4}
        df['concern_sort'] = df['Concern Level'].map(concern_order).fillna(5)
        df = df.sort_values(['concern_sort', 'Personnel Count'], ascending=[True, False])
        df = df.drop('concern_sort', axis=1)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"dprk_image_analysis_{timestamp}.xlsx"
        filepath = Path(f"/Volumes/X5/_CODE_PROJECTS/DPRK/{filename}")

        # Create Excel writer with multiple sheets
        print(f"\n📝 Writing to {filename}...")
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Main analysis sheet
            df.to_excel(writer, sheet_name='Image Analysis', index=False)

            # Summary statistics sheet
            summary_data = {
                'Metric': [
                    'Total Images Analyzed',
                    'High/Critical Concern',
                    'Medium Concern',
                    'Low Concern',
                    'Images with Personnel',
                    'Images with Supervision',
                    'Average Personnel Count',
                    'Most Common Environment',
                    'Most Common Activity'
                ],
                'Value': [
                    len(df),
                    len(df[df['Concern Level'].isin(['high', 'critical'])]),
                    len(df[df['Concern Level'] == 'medium']),
                    len(df[df['Concern Level'] == 'low']),
                    len(df[df['Personnel Count'] > 0]),
                    len(df[df['Supervision Present'] == 'Yes']),
                    round(df['Personnel Count'].mean(), 1),
                    df['Environment Type'].mode()[0] if not df['Environment Type'].empty else 'N/A',
                    df['Activity Type'].mode()[0] if not df['Activity Type'].empty else 'N/A'
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # High concern items sheet
            high_concern = df[df['Concern Level'].isin(['high', 'critical'])].copy()
            if not high_concern.empty:
                high_concern_cols = [
                    'Search Query', 'Image File', 'Scene Description',
                    'Personnel Count', 'Personnel Types', 'Activity Type',
                    'Concern Level', 'Concern Indicators', 'Supervision Present'
                ]
                high_concern[high_concern_cols].to_excel(
                    writer, sheet_name='High Concern Items', index=False
                )

            # Category breakdown sheet
            category_stats = df.groupby('Query Category').agg({
                'Image File': 'count',
                'Personnel Count': 'mean',
                'Concern Level': lambda x: (x.isin(['high', 'critical'])).sum()
            }).round(1)
            category_stats.columns = ['Total Images', 'Avg Personnel', 'High/Critical Count']
            category_stats.to_excel(writer, sheet_name='Category Analysis')

            # Format the Excel file
            workbook = writer.book
            for sheet_name in workbook.sheetnames:
                worksheet = workbook[sheet_name]

                # Adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter

                    for cell in column:
                        try:
                            if cell.value:
                                max_length = max(max_length, len(str(cell.value)))
                        except:
                            pass

                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

        print(f"\n✅ Export completed successfully!")
        print(f"📁 File saved as: {filepath}")

        # Print summary
        print("\n" + "=" * 60)
        print("EXPORT SUMMARY")
        print("=" * 60)
        print(f"Total images analyzed: {len(df)}")
        print(f"High/Critical concern: {len(df[df['Concern Level'].isin(['high', 'critical'])])}")
        print(f"Medium concern: {len(df[df['Concern Level'] == 'medium'])}")
        print(f"Low concern: {len(df[df['Concern Level'] == 'low'])}")
        print(f"Images with personnel: {len(df[df['Personnel Count'] > 0])}")
        print(f"Images with supervision: {len(df[df['Supervision Present'] == 'Yes'])}")

        # Get database totals for comparison
        total_captured = session.query(CapturedImage).count()
        total_analyzed = session.query(ContentAnalysis).count()

        print(f"\nDatabase totals:")
        print(f"  Captured images: {total_captured}")
        print(f"  Analyzed images: {total_analyzed}")
        print(f"  Export coverage: {(len(df)/total_captured*100):.1f}%" if total_captured > 0 else "N/A")

        return filepath

    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        session.close()

if __name__ == "__main__":
    export_to_excel()