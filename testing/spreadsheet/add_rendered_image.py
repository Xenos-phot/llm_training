import sys
import os
import gspread
from google.oauth2.service_account import Credentials
import dotenv
import time
import json
from typing import List, Dict, Optional
import uuid

dotenv.load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from banner_utils.render_banner import render_banner
from banner_utils.image_processor import ImageProcessor


class AddRenderedImage:
    def __init__(self, credentials_file: str = None, spreadsheet_name: str = "TestData"):
        """
        Initialize the Google Sheets rendered image updater
        
        Args:
            credentials_file (str): Path to Google Service Account credentials JSON file
            spreadsheet_name (str): Name of the Google Spreadsheet
        """
        self.spreadsheet_name = spreadsheet_name
        self.credentials_file = credentials_file or os.getenv('GOOGLE_CREDENTIALS_FILE')
        
        # Scopes required for Google Sheets API
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        self.gc = None
        self.spreadsheet = None
        self.worksheet = None
        
        # Initialize image processor for Wasabi uploads
        self.image_processor = ImageProcessor()
        
        # Layout types to process
        self.layouts = [
            'centered_hero',
            'minimalist_center', 
            'circular_focus',
            'split_vertical',
            'grid_four',
            'z_pattern',
            'frame_layout',
            'diagonal_split'
        ]
        
        # Create temp directory for rendering
        os.makedirs('tmp', exist_ok=True)
        
    def authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            if self.credentials_file and os.path.exists(self.credentials_file):
                creds = Credentials.from_service_account_file(
                    self.credentials_file, scopes=self.scopes
                )
                self.gc = gspread.authorize(creds)
            else:
                # Alternative: try to use default credentials or OAuth
                print("Using default authentication method...")
                self.gc = gspread.service_account()
                
            print("Successfully authenticated with Google Sheets API")
            return True
            
        except Exception as e:
            print(f"Authentication failed: {e}")
            print("Please ensure you have:")
            print("1. Google Service Account credentials file")
            print("2. Set GOOGLE_CREDENTIALS_FILE environment variable")
            print("3. Or use 'gcloud auth application-default login'")
            return False
    
    def open_spreadsheet(self):
        """Open the Google Spreadsheet"""
        try:
            self.spreadsheet = self.gc.open(self.spreadsheet_name)
            self.worksheet = self.spreadsheet.get_worksheet(2)  # Use first sheet
            print(f"Successfully opened spreadsheet: {self.spreadsheet_name}")
            return True
        except Exception as e:
            print(f"Failed to open spreadsheet '{self.spreadsheet_name}': {e}")
            return False
    
    def find_layout_columns(self) -> Dict[str, Dict[str, int]]:
        """
        Find the column indices for each layout's Fabric Json and Image columns
        
        Returns:
            Dictionary mapping layout names to their JSON and Image column indices
        """
        try:
            headers = self.worksheet.row_values(1)
            layout_columns = {}
            
            for layout in self.layouts:
                layout_info = {'json_col': None, 'image_col': None}
                print(layout)
                for i, header in enumerate(headers, 1):
                    header_lower = header.lower()
                    
                    # Find FabricJS JSON column
                    if (layout.lower() in header_lower):
                        layout_info['json_col'] = i
                        layout_info['image_col'] = i+1
                    
                   
                print(layout_info)
                # Only add if we found at least the JSON column
                if layout_info['json_col'] is not None:
                    layout_columns[layout] = layout_info
                    
            print(f"Found layout columns: {layout_columns}")
            return layout_columns
            
        except Exception as e:
            print(f"Error finding layout columns: {e}")
            return {}
    
    def get_fabricjs_data(self, layout_columns: Dict[str, Dict[str, int]]) -> List[Dict]:
        """
        Get FabricJS JSON data from the spreadsheet
        
        Returns:
            List of dictionaries with row number, layout, and JSON data
        """
        try:
            # Get all values from the spreadsheet
            all_values = self.worksheet.get_all_values()
            
            if not all_values:
                print("Spreadsheet is empty")
                return []
            
            fabricjs_data = []
            for row_idx, row in enumerate(all_values[1:], start=2):  # Start from row 2 (skip header)
                for layout, cols in layout_columns.items():
                    json_col = cols['json_col']
                    
                    # Check if we have JSON data in this row for this layout
                    if (len(row) > json_col - 1 and 
                        row[json_col - 1].strip()):  # -1 because columns are 1-indexed
                        
                        try:
                            # Parse the JSON to validate it
                            json_data = json.loads(row[json_col - 1].strip())
                            
                            fabricjs_data.append({
                                'row': row_idx,
                                'layout': layout,
                                'json_data': json_data,
                                'image_col': cols.get('image_col')
                            })
                        except json.JSONDecodeError as e:
                            print(f"Invalid JSON in row {row_idx}, layout {layout}: {e}")
                            continue
            
            print(f"Found {len(fabricjs_data)} FabricJS JSON entries to render")
            return fabricjs_data
            
        except Exception as e:
            print(f"Error getting FabricJS data: {e}")
            return []
    
    def render_and_upload_image(self, json_data: dict, layout: str, row_num: int) -> str:
        """
        Render FabricJS JSON to image and upload to Wasabi
        
        Args:
            json_data (dict): FabricJS JSON configuration
            layout (str): Layout name
            row_num (int): Row number for unique naming
            
        Returns:
            str: Wasabi URL of the uploaded image
        """
        try:
            # Generate unique filenames
            unique_id = str(uuid.uuid4())[:8]
            input_file = f'tmp/input_{layout}_{row_num}_{unique_id}.json'
            output_file = f'tmp/output_{layout}_{row_num}_{unique_id}.json'
            
            print(f"    Rendering {layout} for row {row_num}...")
            
            # Render the banner with PNG output
            start_time = time.time()
            render_banner(json_data, input_file, output_file, create_png=True)
            render_time = time.time() - start_time
            
            # The PNG file will be created with the same name as output_file but with .png extension
            png_file = output_file.replace('.json', '.png')
            
            if not os.path.exists(png_file):
                raise Exception(f"PNG file not created: {png_file}")
            
            print(f"    Rendered successfully (took {render_time:.1f}s)")
            
            # Upload to Wasabi
            upload_start = time.time()
            wasabi_url = self.image_processor._upload_to_wasabi(png_file)
            upload_time = time.time() - upload_start
            
            print(f"    Uploaded to Wasabi (took {upload_time:.1f}s)")
            
            # Cleanup temporary files
            self._cleanup_files([input_file, output_file, png_file])
            
            return wasabi_url
            
        except Exception as e:
            print(f"    ❌ Error rendering/uploading {layout}: {e}")
            # Cleanup on error
            self._cleanup_files([input_file, output_file, png_file])
            raise
    
    def update_image_column(self, row_num: int, layout: str, wasabi_url: str, image_col: int):
        """
        Update the image column with IMAGE formula
        
        Args:
            row_num (int): Row number to update
            layout (str): Layout name
            wasabi_url (str): Wasabi URL of the rendered image
            image_col (int): Column index for the image
        """
        try:
            if image_col is None:
                print(f"    No image column found for {layout}")
                return
                
            # Create IMAGE formula for Google Sheets
            image_formula = "=IMAGE(\"" + wasabi_url + "\")"
            
            # Update the cell with raw=False to allow formula interpretation
            cell_range = gspread.utils.rowcol_to_a1(row_num, image_col)
            self.worksheet.update(cell_range, [[image_formula]], raw=False)
            
            print(f"    Updated {layout} image column with rendered banner")
            
        except Exception as e:
            print(f"    Error updating image column for {layout}: {e}")
    
    def process_all_layouts(self, delay_seconds: float = 2.0, specific_layout: str = None, specific_row: int = None):
        """
        Process all FabricJS JSON entries and generate rendered images
        
        Args:
            delay_seconds (float): Delay between rendering operations
            specific_layout (str): If specified, only process this layout
            specific_row (int): If specified, only process this row
        """
        if not self.authenticate():
            return False
            
        if not self.open_spreadsheet():
            return False
        
        layout_columns = self.find_layout_columns()
        
        if not layout_columns:
            print("No layout columns found in spreadsheet")
            return False
        
        fabricjs_data = self.get_fabricjs_data(layout_columns)
        
        if not fabricjs_data:
            print("No FabricJS data found to process")
            return False
        
        # Filter data if specific layout or row is requested
        if specific_layout:
            fabricjs_data = [item for item in fabricjs_data if item['layout'] == specific_layout]
        
        if specific_row:
            fabricjs_data = [item for item in fabricjs_data if item['row'] == specific_row]
        
        if not fabricjs_data:
            print("No matching FabricJS data found after filtering")
            return False
        
        print(f"Processing {len(fabricjs_data)} FabricJS entries...")
        
        for i, item in enumerate(fabricjs_data, 1):
            row_num = item['row']
            layout = item['layout']
            json_data = item['json_data']
            image_col = item['image_col']
            
            print(f"\nProcessing {i}/{len(fabricjs_data)}: Row {row_num}, Layout {layout}")
            
            try:
                # Render and upload the image
                wasabi_url = self.render_and_upload_image(json_data, layout, row_num)
                
                # Update the spreadsheet with the image
                self.update_image_column(row_num, layout, wasabi_url, image_col)
                
                print(f"  ✅ Successfully processed {layout} for row {row_num}")
                
                # Add delay between operations
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                    
            except Exception as e:
                print(f"  ❌ Error processing {layout} for row {row_num}: {e}")
                continue
        
        print(f"\n🎉 Completed processing all FabricJS entries!")
        return True
    
    def _cleanup_files(self, file_paths: list):
        """Clean up temporary files"""
        for path in file_paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Error cleaning up {path}: {str(e)}")


def main():
    """Main function to run the rendered image updater"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Render FabricJS JSON and update Google Sheets with images')
    parser.add_argument('--spreadsheet', default='TestData', help='Name of the Google Spreadsheet')
    parser.add_argument('--layout', help='Specific layout to process (default: all layouts)')
    parser.add_argument('--row', type=int, help='Specific row to process (default: all rows)')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between operations in seconds')
    
    args = parser.parse_args()
    
    updater = AddRenderedImage(spreadsheet_name=args.spreadsheet)
    
    success = updater.process_all_layouts(
        delay_seconds=args.delay,
        specific_layout=args.layout,
        specific_row=args.row
    )
    
    if success:
        print("Successfully updated Google Sheets with rendered images!")
    else:
        print("Failed to update Google Sheets. Please check the error messages above.")


if __name__ == "__main__":
    main()
