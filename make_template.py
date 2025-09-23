from openpyxl import Workbook

def create_template(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Image Evidence Metadata"

    # List of all column headings
    headers = [
        "Image_URL",
        "Source_Page_URL",
        "Thumbnail_URL",
        "Image_Filename",
        "Image_Format",
        "Image_Width",
        "Image_Height",
        "File_Size_Bytes",
        "Date_Published",
        "Date_Captured",
        "Date_Downloaded",
        "Country",
        "Region",
        "City_or_Locality",
        "GPS_Latitude",
        "GPS_Longitude",
        "Place_Description",
        "Subject_Type",
        "Subject_Group",
        "Person_Names",
        "Person_Roles",
        "Number_of_Subjects",
        "Gender",
        "Nationality_Claimed",
        "Handler_Present",
        "Handler_Role",
        "Interaction_Description",
        "Labour_Type",
        "Uniforms_Equipment",
        "Activity_Description",
        "EXIF_Camera_Make",
        "EXIF_Camera_Model",
        "EXIF_DateTime_Original",
        "EXIF_Software",
        "EXIF_GPS_Altitude",
        "GPS_Accuracy",
        "Reverse_Image_Search_Matches",
        "Duplicate_Of",
        "Publisher",
        "Author_Photographer",
        "License_Usage_Rights",
        "Caption_Alt_Text",
        "Language_Of_Source",
        "Source_Type",
        "Search_Term_Used",
        "Relevance_Score",
        "Verification_Notes",
        "Date_Added_To_DB",
        "Row_ID"
    ]

    # Write headers into the first row
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.value = header

    # Optionally: freeze the header row so it's always visible
    ws.freeze_panes = "A2"

    # Save the workbook
    wb.save(path)
    print(f"Template saved to {path}")

if __name__ == "__main__":
    create_template("north_koreans_in_russia_template.xlsx")
