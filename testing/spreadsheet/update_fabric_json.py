import sys
import os
import gspread
from google.oauth2.service_account import Credentials
import dotenv
import time
import json
from typing import List, Dict, Optional

dotenv.load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_scripts.test_qwen import test_model, load_model


class UpdateFabricJson:
    def __init__(self, credentials_file: str = None, spreadsheet_name: str = "TestData", sheet_number: int = 1, checkpoint_path: str = "/root/llm_training/model/checkpoint-850"):
        """
        Initialize the Google Sheets FabricJS JSON updater
        
        Args:
            credentials_file (str): Path to Google Service Account credentials JSON file
            spreadsheet_name (str): Name of the Google Spreadsheet
        """
        self.spreadsheet_name = spreadsheet_name
        self.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE')
        
        # Scopes required for Google Sheets API
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        self.gc = None
        self.spreadsheet = None
        self.worksheet = None
        
        # Layout types to process
        self.layouts = [
            'centered_hero',
            'minimalist_center', 
            'circular_focus',
            'split_vertical',
            'grid_four',
            "z_pattern",
            "frame_layout",
            "diagonal_split"
        ]

        self.model = None
        self.tokenizer = None
        self.checkpoint_path = checkpoint_path
        self.sheet_number = sheet_number
        self.model, self.tokenizer = load_model(self.checkpoint_path)
        
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
            self.worksheet = self.spreadsheet.get_worksheet(self.sheet_number)  # Use second sheet (0-indexed)
            print(f"Successfully opened spreadsheet: {self.spreadsheet_name}")
            return True
        except Exception as e:
            print(f"Failed to open spreadsheet '{self.spreadsheet_name}': {e}")
            return False
    
    def extract_url_from_image_formula(self, formula: str) -> str:
        """
        Extract URL from IMAGE formula like =IMAGE("https://example.com/image.jpg")
        
        Args:
            formula (str): The formula string
            
        Returns:
            str: The extracted URL or empty string if not found
        """
        import re
        
        if not formula or not formula.startswith('=IMAGE('):
            return formula.strip() if formula else ""  # Return as-is if not an IMAGE formula
        
        # Extract URL from =IMAGE("url") formula
        match = re.search(r'=IMAGE\(["\']([^"\']+)["\']', formula)
        if match:
            return match.group(1)
        
        # Try without quotes in case formula doesn't have them
        match = re.search(r'=IMAGE\(([^)]+)\)', formula)
        if match:
            return match.group(1).strip()
        
        return ""
    
    def get_product_data(self) -> List[Dict]:
        """
        Get product data from the spreadsheet
        
        Returns:
            List of dictionaries with row number and product details
        """
        try:
            # Get all values from the spreadsheet (rendered values)
            all_values = self.worksheet.get_all_values()
            # Get formulas to extract IMAGE() URLs
            all_formulas = self.worksheet.get_all_values(value_render_option='FORMULA')
            
            if not all_values:
                print("Spreadsheet is empty")
                return []
            
            # Find the header row and column indices
            headers = all_values[0]
            name_col_idx = None
            desc_col_idx = None
            price_col_idx = None
            image_url_col_idx = None
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if 'product_name' in header_lower:
                    name_col_idx = i
                elif 'product_description' in header_lower:
                    desc_col_idx = i
                elif 'product_price' in header_lower:
                    price_col_idx = i
                elif 'product_image' in header_lower:
                    image_url_col_idx = i
            
            if any(col is None for col in [name_col_idx, desc_col_idx, price_col_idx]):
                print("Could not find all required product columns (product_name, product_description, product_price)")
                return []
            
            product_data = []
            for row_idx, row in enumerate(all_values[1:], start=2):  # Start from row 2 (skip header)
                # Check if we have product data in this row
                if (len(row) > max(name_col_idx, desc_col_idx, price_col_idx) and 
                    any(row[col].strip() for col in [name_col_idx, desc_col_idx, price_col_idx])):
                    
                    # Extract image URL from IMAGE formula if present
                    image_url = ""
                    if image_url_col_idx is not None and len(all_formulas) > row_idx - 1:
                        formula_row = all_formulas[row_idx - 1]  # -1 because all_formulas includes header
                        if len(formula_row) > image_url_col_idx:
                            formula = formula_row[image_url_col_idx]
                            image_url = self.extract_url_from_image_formula(formula)
                    
                    product_data.append({
                        'row': row_idx,
                        'product_name': row[name_col_idx].strip() if len(row) > name_col_idx else "",
                        'product_description': row[desc_col_idx].strip() if len(row) > desc_col_idx else "",
                        'product_price': row[price_col_idx].strip() if len(row) > price_col_idx else "",
                        'product_image': image_url
                    })
            
            print(f"Found {len(product_data)} rows with product data to process")
            return product_data
            
        except Exception as e:
            print(f"Error getting product data: {e}")
            return []
    
    def find_layout_columns(self) -> Dict[str, int]:
        """
        Find the column indices for each layout's Fabric Json column
        
        Returns:
            Dictionary mapping layout names to column indices
        """
        try:
            headers = self.worksheet.row_values(1)
            layout_columns = {}
            
            for i, header in enumerate(headers, 1):
                header_lower = header.lower()
                
                # Check if this is a Fabric Json column for any layout
                for layout in self.layouts:
                    # Look for patterns like "centered_hero Fabric Json" or just layout name in fabric json context
                    if (layout.lower() in header_lower and 
                        ('fabric' in header_lower and 'json' in header_lower)):
                        layout_columns[layout] = i
                        break
                    # Also check for exact layout name in a fabric json context
                    elif layout.lower() == header_lower.replace('_', '').replace(' ', ''):
                        # This might be a layout column, check if next column is fabric json
                        if i < len(headers):
                            next_header = headers[i].lower() if i < len(headers) else ""
                            if 'fabric' in next_header and 'json' in next_header:
                                layout_columns[layout] = i + 1
            
            # If we can't find specific fabric json columns, look for layout columns and assume fabric json is next
            if not layout_columns:
                for i, header in enumerate(headers, 1):
                    for layout in self.layouts:
                        if layout.lower() in header.lower():
                            # Assume the fabric json column is either this column or nearby
                            layout_columns[layout] = i
                            
            print(f"Found layout columns: {layout_columns}")
            return layout_columns
            
        except Exception as e:
            print(f"Error finding layout columns: {e}")
            return {}
    
    def update_fabric_json(self, row_num: int, layout: str, fabric_json: dict, layout_columns: Dict[str, int]):
        """
        Update a specific cell with FabricJS JSON
        
        Args:
            row_num (int): Row number to update
            layout (str): Layout type
            fabric_json (dict): FabricJS JSON object
            layout_columns (Dict[str, int]): Mapping of layout names to column indices
        """
        try:
            if layout not in layout_columns:
                print(f"No column found for layout: {layout}")
                return
                
            col_num = layout_columns[layout]
            
            # Convert JSON to string
            json_str = json.dumps(fabric_json, separators=(',', ':'))  # Compact JSON
            
            # Update the cell
            cell_range = gspread.utils.rowcol_to_a1(row_num, col_num)
            self.worksheet.update(cell_range, [[json_str]])
            
            print(f"Updated row {row_num}, {layout} with FabricJS JSON")
            
        except Exception as e:
            print(f"Error updating fabric JSON for row {row_num}, layout {layout}: {e}")
    
    def process_all_products(self, delay_seconds: float = 3.0, specific_layout: str = None):
        """
        Process all products and generate FabricJS JSON for each layout
        
        Args:
            delay_seconds (float): Delay between model calls to avoid overwhelming the GPU
            specific_layout (str): If specified, only process this layout
        """
        if not self.authenticate():
            return False
            
        if not self.open_spreadsheet():
            return False
        
        product_data = self.get_product_data()
        
        if not product_data:
            print("No product data found to process")
            return False
        
        layout_columns = self.find_layout_columns()
        
        if not layout_columns:
            print("No layout columns found in spreadsheet")
            return False
        
        # Filter layouts if specific layout is requested
        layouts_to_process = [specific_layout] if specific_layout else self.layouts
        layouts_to_process = [l for l in layouts_to_process if l in layout_columns]
        
        if not layouts_to_process:
            print("No valid layouts to process")
            return False
        
        print(f"Processing {len(product_data)} products for layouts: {layouts_to_process}")
        
        total_operations = len(product_data) * len(layouts_to_process)
        current_operation = 0
        
        for i, product in enumerate(product_data, 1):
            row_num = product['row']
            product_name = product['product_name']
            product_description = product['product_description']
            product_price = product['product_price']
            image_url = product['product_image']
            print(f"\nProcessing Product {i}/{len(product_data)}: Row {row_num}")
            print(f"Product: {product_name[:50]}...")
            
            for layout in layouts_to_process:
                current_operation += 1
                print(f"\n  Generating {layout} layout ({current_operation}/{total_operations})...")
                
                try:
                    # Generate FabricJS JSON using the test_model function
                    start_time = time.time()
                    fabric_json = test_model(product_name, product_description, product_price, layout, image_url, self.model, self.tokenizer)
                    generation_time = time.time() - start_time
                    
                    if fabric_json and fabric_json != "failed to extract json":
                        # Update the spreadsheet
                        self.update_fabric_json(row_num, layout, fabric_json, layout_columns)
                        print(f"    ✅ Generated and saved {layout} (took {generation_time:.1f}s)")
                    else:
                        print(f"    ❌ Failed to generate valid JSON for {layout}")
                        
                    # Add delay between model calls
                    if delay_seconds > 0:
                        time.sleep(delay_seconds)
                        
                except Exception as e:
                    print(f"    ❌ Error generating {layout}: {e}")
                    continue
        
        print(f"\n🎉 Completed processing all products and layouts!")
        return True
    
    def process_single_product(self, row_num: int, layout: str = None, delay_seconds: float = 3.0):
        """
        Process a single product row
        
        Args:
            row_num (int): Row number to process
            layout (str): Specific layout to generate (if None, generates all layouts)
            delay_seconds (float): Delay between model calls
        """
        if not self.authenticate():
            return False
            
        if not self.open_spreadsheet():
            return False
        
        # Get the specific row data
        try:
            row_values = self.worksheet.row_values(row_num)
            row_formulas = self.worksheet.row_values(row_num, value_render_option='FORMULA')
            headers = self.worksheet.row_values(1)
            
            # Find product data columns
            product_data = {}
            image_col_idx = None
            
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if 'product_name' in header_lower and i < len(row_values):
                    product_data['product_name'] = row_values[i]
                elif 'product_description' in header_lower and i < len(row_values):
                    product_data['product_description'] = row_values[i]
                elif 'product_price' in header_lower and i < len(row_values):
                    product_data['product_price'] = row_values[i]
                elif 'product_image' in header_lower:
                    image_col_idx = i
            
            # Extract image URL from formula if present
            if image_col_idx is not None and image_col_idx < len(row_formulas):
                formula = row_formulas[image_col_idx]
                product_data['product_image'] = self.extract_url_from_image_formula(formula)
            else:
                product_data['product_image'] = ""
            
            print(f"Extracted image URL: {product_data['product_image']}")
            
            if not all(key in product_data for key in ['product_name', 'product_description', 'product_price', 'product_image']):
                print("Could not find all required product data in the specified row")
                return False
            
            layout_columns = self.find_layout_columns()
            layouts_to_process = [layout] if layout else self.layouts
            layouts_to_process = [l for l in layouts_to_process if l in layout_columns]
            
            print(f"Processing row {row_num}: {product_data['product_name']}")
            
            for layout_type in layouts_to_process:
                print(f"  Generating {layout_type}...")
                fabric_json = test_model(
                    product_data['product_name'], 
                    product_data['product_description'], 
                    product_data['product_price'], 
                    layout_type, 
                    product_data['product_image'],
                    self.model,
                    self.tokenizer
                )
                
                if fabric_json and fabric_json != "failed to extract json":
                    self.update_fabric_json(row_num, layout_type, fabric_json, layout_columns)
                    print(f"    ✅ Generated and saved {layout_type}")
                else:
                    print(f"    ❌ Failed to generate {layout_type}")
                
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
            
            return True
            
        except Exception as e:
            print(f"Error processing single product: {e}")
            return False


def main():
    """Main function to run the FabricJS JSON updater"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update Google Sheets with FabricJS JSON')
    parser.add_argument('--spreadsheet', default='TestData', help='Name of the Google Spreadsheet')
    parser.add_argument('--layout', help='Specific layout to process (default: all layouts)')
    parser.add_argument('--row', type=int, help='Specific row to process (default: all rows)')
    parser.add_argument('--delay', type=float, default=3.0, help='Delay between model calls in seconds')
    
    args = parser.parse_args()
    
    updater = UpdateFabricJson(spreadsheet_name=args.spreadsheet)
    
    if args.row:
        # Process single row
        success = updater.process_single_product(args.row, args.layout, args.delay)
    else:
        # Process all rows
        success = updater.process_all_products(args.delay, args.layout)
    
    if success:
        print("Successfully updated Google Sheets with FabricJS JSON!")
    else:
        print("Failed to update Google Sheets. Please check the error messages above.")


if __name__ == "__main__":
    main()
