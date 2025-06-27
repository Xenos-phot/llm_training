import sys
import os
import gspread
from google.oauth2.service_account import Credentials
import dotenv
import time
from typing import List, Dict, Optional

dotenv.load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from banner_utils.amazon_scrapper import extract_amazon_product_details


class UpdateInput:
    def __init__(self, credentials_file: str = None, spreadsheet_name: str = "TestData"):
        """
        Initialize the Google Sheets populator
        
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
            self.worksheet = self.spreadsheet.sheet1  # Use first sheet
            print(f"Successfully opened spreadsheet: {self.spreadsheet_name}")
            return True
        except Exception as e:
            print(f"Failed to open spreadsheet '{self.spreadsheet_name}': {e}")
            return False
    
    def get_amazon_urls(self) -> List[Dict]:
        """
        Get Amazon URLs from the spreadsheet
        
        Returns:
            List of dictionaries with row number and amazon_url
        """
        try:
            # Get all values from the spreadsheet
            all_values = self.worksheet.get_all_values()
            
            if not all_values:
                print("Spreadsheet is empty")
                return []
            
            # Find the header row and column indices
            headers = all_values[0]
            url_col_idx = None
            
            for i, header in enumerate(headers):
                if 'amazon_url' in header.lower():
                    url_col_idx = i
                    break
            
            if url_col_idx is None:
                print("Could not find amazon_url column")
                return []
            
            amazon_urls = []
            for row_idx, row in enumerate(all_values[1:], start=2):  # Start from row 2 (skip header)
                if len(row) > url_col_idx and row[url_col_idx].strip():
                    amazon_urls.append({
                        'row': row_idx,
                        'amazon_url': row[url_col_idx].strip()
                    })
            
            print(f"Found {len(amazon_urls)} Amazon URLs to process")
            return amazon_urls
            
        except Exception as e:
            print(f"Error getting Amazon URLs: {e}")
            return []
    
    def update_row_with_product_details(self, row_num: int, product_name: str, 
                                      product_description: str, product_price: str, 
                                      image_url: str):
        """
        Update a specific row with product details
        
        Args:
            row_num (int): Row number to update
            product_name (str): Product name
            product_description (str): Product description  
            product_price (str): Product price
            image_url (str): Product image URL
        """
        try:
            # Get header row to find column positions
            headers = self.worksheet.row_values(1)
            
            # Find column indices
            name_col = None
            desc_col = None
            price_col = None
            image_col = None
            
            for i, header in enumerate(headers, 1):
                header_lower = header.lower()
                if 'product_name' in header_lower:
                    name_col = i
                elif 'product_description' in header_lower:
                    desc_col = i
                elif 'product_price' in header_lower:
                    price_col = i
                elif 'product_image' in header_lower:
                    image_col = i
            
            # Update cells if columns were found
            updates = []
            
            if name_col:
                updates.append({
                    'range': f'{gspread.utils.rowcol_to_a1(row_num, name_col)}',
                    'values': [[product_name]]
                })
            
            if desc_col:
                updates.append({
                    'range': f'{gspread.utils.rowcol_to_a1(row_num, desc_col)}',
                    'values': [[product_description]]
                })
            
            if price_col:
                updates.append({
                    'range': f'{gspread.utils.rowcol_to_a1(row_num, price_col)}',
                    'values': [[product_price]]
                })
            
            if image_col and image_url:
                # For Google Sheets, we can use IMAGE formula to display the image
                image_formula = f'=IMAGE("{image_url}")'
                updates.append({
                    'range': f'{gspread.utils.rowcol_to_a1(row_num, image_col)}',
                    'values': [[image_formula]]
                })
            
            # Batch update all cells
            if updates:
                self.worksheet.batch_update(updates)
                print(f"Updated row {row_num} with product details")
            
        except Exception as e:
            print(f"Error updating row {row_num}: {e}")
    
    def process_all_urls(self, delay_seconds: float = 2.0):
        """
        Process all Amazon URLs in the spreadsheet
        
        Args:
            delay_seconds (float): Delay between requests to avoid rate limiting
        """
        if not self.authenticate():
            return False
            
        if not self.open_spreadsheet():
            return False
        
        amazon_urls = self.get_amazon_urls()
        
        if not amazon_urls:
            print("No Amazon URLs found to process")
            return False
        
        print(f"Processing {len(amazon_urls)} Amazon URLs...")
        
        for i, url_data in enumerate(amazon_urls, 1):
            row_num = url_data['row']
            amazon_url = url_data['amazon_url']
            
            print(f"\nProcessing {i}/{len(amazon_urls)}: Row {row_num}")
            print(f"URL: {amazon_url}")
            
            try:
                # Extract product details using the existing function
                product_name, product_description, product_price, image_url = extract_amazon_product_details(amazon_url)
                
                print(f"Product Name: {product_name[:50]}...")
                print(f"Price: {product_price}")
                print(f"Image URL: {image_url[:50]}..." if image_url else "No image")
                
                # Update the spreadsheet row
                self.update_row_with_product_details(
                    row_num, product_name, product_description, 
                    product_price, image_url
                )
                
                # Add delay to avoid rate limiting
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                    
            except Exception as e:
                print(f"Error processing URL in row {row_num}: {e}")
                continue
        
        print(f"\nCompleted processing all URLs!")
        return True


def main():
    """Main function to run the Google Sheets populator"""
    # You can specify a custom spreadsheet name here
    populator = UpdateInput(spreadsheet_name="TestData")
    
    # Process all URLs with a 2-second delay between requests
    success = populator.process_all_urls(delay_seconds=2.0)
    
    if success:
        print("Successfully populated Google Sheets with product details!")
    else:
        print("Failed to populate Google Sheets. Please check the error messages above.")


if __name__ == "__main__":
    main() 