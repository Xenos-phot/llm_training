import json
import traceback
from pathlib import Path
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(sys.path)
from banner_utils.scrapper_api import RapidAPIClient
from banner_utils.image_processor import ImageProcessor

class AmazonScraper:
    def __init__(self):
        self.rapidapi_client = RapidAPIClient()
        self.image_processor = ImageProcessor()
        self.output_base_dir = Path('output')
        self.output_base_dir.mkdir(exist_ok=True)

    def extract_product_details(self, url, marketplace, banner_width, banner_height):
        """Extract product details using Oxylabs API and process images"""
        try:
            # Get product details from Oxylabs
            product_details = self.rapidapi_client.get_product_details(url, marketplace)
            # Create output directory for this product
            output_dir = self.output_base_dir / product_details['product_id']
            output_dir.mkdir(exist_ok=True)
            
            # Process image if available
            if product_details.get('main_image'):
                try:
                    # Process image to remove background
                    processed_image_url = self.image_processor.process_image_url(product_details['main_image'], banner_width, banner_height)
                    product_details['main_image'] = processed_image_url
                except Exception as e:
                    print(f"Error processing image: {str(e)}")
                    traceback_msg = traceback.format_exc()
                    print(traceback_msg)
                    # Keep original image URL if processing fails
            
            # Save data to JSON file
            self._save_product_details(output_dir, product_details)
            
            return product_details

        except Exception as e:
            print(f"Error during extraction: {str(e)}")
            traceback.print_exc()
            raise

    def _save_product_details(self, output_dir, product_details):
        """Save product details to JSON file"""
        try:
            output_file = output_dir / f"product_{product_details['product_id']}.json"
            with open(output_file, 'w') as f:
                json.dump(product_details, f, indent=2)
            
        except Exception as e:
            print(f"Error saving product details: {str(e)}")
            # Don't raise the error since this is not critical
            pass



def extract_amazon_product_details(amazon_url):
    """
    Extract product details from an Amazon URL
    
    Args:
        amazon_url (str): Amazon product URL
        
    Returns:
        tuple: (product_name, product_description, product_price, image_url)
    """
    scraper = AmazonScraper()
    # Default values for banner dimensions and marketplace
    banner_width = 1080
    banner_height = 1080
    marketplace = "US"  # Default to US marketplace
    
    product_details = scraper.extract_product_details(amazon_url, marketplace, banner_width, banner_height)
    product_name = product_details.get('product_name', '')
    product_description = product_details.get('description', '')
    product_price = product_details.get('price', '')
    image_url = product_details.get('main_image', '')
    
    if isinstance(product_price, dict) and 'value' in product_price:
        product_price = str(product_price['value'])
    elif isinstance(product_price, (int, float)):
        product_price = str(product_price)
    
    return product_name, product_description, product_price, image_url


def extract_amazon_product_details(amazon_url):
    """
    Extract product details from an Amazon URL
    
    Args:
        amazon_url (str): Amazon product URL
        
    Returns:
        tuple: (product_name, product_description, product_price, image_url)
    """
    scraper = AmazonScraper()
    # Default values for banner dimensions and marketplace
    banner_width = 1080
    banner_height = 1080
    marketplace = "US"  # Default to US marketplace
    
    product_details = scraper.extract_product_details(amazon_url, marketplace, banner_width, banner_height)
    product_name = product_details.get('product_name', '')
    product_description = product_details.get('description', '')
    product_price = product_details.get('price', '')
    image_url = product_details.get('main_image', '')
    
    if isinstance(product_price, dict) and 'value' in product_price:
        product_price = str(product_price['value'])
    elif isinstance(product_price, (int, float)):
        product_price = str(product_price)
    
    return product_name, product_description, product_price, image_url
