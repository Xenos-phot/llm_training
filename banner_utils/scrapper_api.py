import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import urllib.parse
import re

class RapidAPIClient:
    def __init__(self):
        load_dotenv()
        self.x_rapidapi_key = os.getenv('X-RAPIDAPI-KEY')
        self.api_url = "https://real-time-amazon-data.p.rapidapi.com/product-details"
        self.headers = {
            "x-rapidapi-key": self.x_rapidapi_key,
            "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com"
        }
        
        if not all([self.x_rapidapi_key]):
            raise ValueError("X-RAPIDAPI-KEY credentials not found in environment variables")

    def get_flipkart_product_details(self, pid: str) -> dict:
        print(f"PID: {pid}")
        url = "https://real-time-flipkart-api.p.rapidapi.com/product-details"
        querystring = {"pid":pid}
        headers = {
            "x-rapidapi-key": os.getenv('X-RAPIDAPI-KEY'),
            "x-rapidapi-host": "real-time-flipkart-api.p.rapidapi.com"
        }
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code != 200:
            raise Exception(f"API call failed: {response.status_code}")
        data = response.json()
        product_description = ""
        if data.get('description'):
            product_description += f"{data.get('description')} "
        if data.get("highlights"):
            product_description += f"{' '.join(data.get('highlights'))} "

        product_info = {
            'product_id': data.get("pid"),
            'url': data.get("url"),
            'product_name': data.get("title"),
            'main_image': data.get("images")[0] if data.get("images") else None,
            'price': str(data.get("price", "N/A")),
            'about_item': [product_description],
            'rating': str(data.get('rating', {}).get("overall", {}).get("average", "N/A")),
            'description': product_description
        }
        return product_info
    
    def get_shopify_product_details(self, product_url: str) -> dict:
        url = "https://shopify-fast-scraper.p.rapidapi.com/product"
        querystring = {"url":product_url}
        headers = {
            "x-rapidapi-key": os.getenv('X-RAPIDAPI-KEY'),
            "x-rapidapi-host": "shopify-fast-scraper.p.rapidapi.com"
        }
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code != 200:
            print(response.text)
            raise Exception(f"API call failed: {response.status_code}")

        data = response.json()
        results = data.get("product", {})
        product_info = {
            'product_id': str(results.get("id")),
            'url': results.get("product_url"),
            'product_name': results.get("title"),
            'main_image': results.get("image", {}).get("src", None),
            'price': f'{results.get("variants", [{}])[0].get("price", "N/A")} {results.get("variants", [{}])[0].get("price_currency")}',
            'about_item': [results.get("body_html")],
            'rating': str(results.get('product_star_rating', 'N/A')),
            'description': results.get("body_html")
        }
        return product_info

    def get_woocommerce_product_details(self, product_url: str) -> dict:
        url = "https://woocommerce-scraper2.p.rapidapi.com/api/woo/scrape-by-url/"
        payload = { "url": product_url}
        headers = {
            "x-rapidapi-key": os.getenv('X-RAPIDAPI-KEY'),
            "x-rapidapi-host": "woocommerce-scraper2.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            print(response.text)
            raise Exception(f"API call failed: {response.status_code}")
        data = response.json()
        results = data.get("data", {})
        product_info = {
            'product_id': str(results.get("id")),
            'url': results.get("product_url"),
            'product_name': results.get("name"),
            'main_image': results.get("images", "").split(",")[0],
            'price': f'{results.get("sale_price")}',
            'about_item': [results.get("description")],
            'rating': str(results.get('average_rating', 'N/A')),
            'description': results.get("description")
        }
        return product_info
    
    def get_etsy_product_details(self, listing_id):
        url = "https://etsy-api2.p.rapidapi.com/product/description"
        querystring = {"listingId": listing_id}
        headers = {
            "x-rapidapi-key": os.getenv('X-RAPIDAPI-KEY'),
            "x-rapidapi-host": "etsy-api2.p.rapidapi.com"
        }
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code != 200:
            print(response.text)
            raise Exception(f"API call failed: {response.status_code}")
        data = response.json()
        results = data.get("data", {})
        product_info = {
            'product_id': str(results.get("productId")),
            'url': results.get("url"),
            'product_name': results.get("title"),
            'main_image': results.get("images", [None])[0],
            'price': f'{results.get("price", {}).get("salePrice", "N/A")}',
            'about_item': results.get("category"),
            'rating': str(results.get('ratingSummary', {}).get("ratingValue", "N/A")),
            'description': results.get("description")
        }
        return product_info
    
    def get_walmart_product_details(self, product_url):
        url = "https://walmart-data.p.rapidapi.com/details.php"
        querystring = {"url":product_url}
        headers = {
            "x-rapidapi-key": os.getenv('X-RAPIDAPI-KEY'),
            "x-rapidapi-host": "walmart-data.p.rapidapi.com"
        }
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code != 200:
            print(response.text)
            raise Exception(f"API call failed: {response.status_code}")
        data = response.json()
        if data:
            results = data[0]
            if results["@type"] != "Product":
                results = data[1]
            product_info = {
                'product_id': str(results.get("sku")),
                'url': f'{results.get("offers", [{}])[0].get("url", "N/A")}',
                'product_name': results.get("name"),
                'main_image': results.get("image", None),
                'price': f'{results.get("offers", [{}])[0].get("price", "N/A")}',
                'about_item': [results.get("description")],
                'rating': str(results.get('aggregateRating', {}).get("ratingValue", "N/A")),
                'description': results.get("description")
            }
            print(product_info)
            return product_info
        else:
            raise Exception(f"API call failed: {response.status_code}")

    def get_product_details(self, url: str, marketplace: str) -> dict:
        if marketplace == "Flipkart":
            pattern = r'/p/(\w+).*?pid=([A-Za-z0-9]+)'
            match = re.search(pattern, url)
            if match:
                product_id = match.group(1)  # Product ID after '/p/'
                pid = match.group(2)         # pid parameter from the query string
            else:
                raise ValueError("Invalid Flipkart URL")        
            return self.get_flipkart_product_details(pid)
        if marketplace == "Walmart":
            return self.get_walmart_product_details(url)
        if marketplace == "Shopify":
            return self.get_shopify_product_details(url)
        if marketplace == "WooCommerce":
            return self.get_woocommerce_product_details(url)
        if marketplace == "Etsy":
            pattern = r'/listing/(\d+)'
            match = re.search(pattern, url)
            if match:
                listing_id = match.group(1)
            else:
                raise ValueError("Invalid Etsy URL") 
            return self.get_etsy_product_details(listing_id)    


        querystring = {"asin":OxylabsClient._extract_product_id("self", url), "country":"US"}
        response = requests.get(
                self.api_url,
                headers=self.headers,
                params=querystring
            )
        if response.status_code != 200:
            raise Exception(f"API call failed: {response.status_code}")
        data = response.json()
        results = data.get("data", None)
        if not results:
            raise Exception(f"API call failed, No result: {data}")
        product_description = ""
        if results.get('product_description'):
            product_description += f"{results.get('product_description')} "
        if results.get("about_product"):
            product_description += f"{' '.join(results.get('about_product'))} "
        if results.get("product_details"):
            product_description += " ".join([f"{k} - {results.get('product_details')[k]} **" for k in results.get('product_details')])


        product_info = {
            'product_id': results.get("asin"),
            'url': results.get("product_url"),
            'product_name': results.get("product_title"),
            'main_image': results.get("product_photo"),
            'price': str(results.get("product_price", "N/A")),
            'about_item': [product_description],
            'rating': str(results.get('product_star_rating', 'N/A')),
            'description': product_description
        }
        return product_info

class OxylabsClient:
    def __init__(self):
        load_dotenv()
        self.username = os.getenv('OXYLABS_USER')
        self.password = os.getenv('OXYLABS_PASS')
        self.api_url = "https://realtime.oxylabs.io/v1/queries"
        
        if not all([self.username, self.password]):
            raise ValueError("Oxylabs credentials not found in environment variables")
            
    def _extract_product_id(self, url: str) -> str:
        """Extract Amazon product ID from URL"""
        try:
            parsed_url = urllib.parse.urlparse(url)
            for param in parsed_url.path.split('/'):
                if param.startswith('B0') and len(param) == 10:
                    return param
            raise ValueError("Could not extract product ID from URL")
        except Exception as e:
            raise ValueError(f"Error extracting product ID: {str(e)}") 

    def get_product_details(self, url: str, marketplace: str) -> dict:
        """Fetch product details from Oxylabs API"""
        try:
            payload = {
                "url": url,
                "parse": True
            }
            if marketplace == "Amazon":
                product_id = self._extract_product_id(url)
                payload["query"] = product_id
                payload["source"] = "amazon_product"
                payload["geo_location"] = "90210"
                payload.pop("url")
            elif marketplace in ["Walmart", "BestBuy", "Target"]:
                payload["source"] = "universal_ecommerce"
                payload["geo_location"] = "United States"
            elif marketplace == "Etsy":
                payload["source"] = "universal_ecommerce"
            elif marketplace == "eBay":
                payload["source"] = "universal_ecommerce"
                payload["geo_location"] = "United States"
                # payload.pop("parse")

            response = requests.post(
                self.api_url,
                auth=(self.username, self.password),
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"API call failed: {response.status_code}")
            
            data = response.json()
            print(f"Oxylabs Data: {data}")
            if  marketplace == "Amazon":
                content = data['results'][0]['content']
                # Create dictionary with only required fields
                about_items = content.get('bullet_points', '').split('\n')
                description = ' '.join(about_items) if about_items else 'No description available'
                
                product_info = {
                        'product_id': product_id,
                        'url': url,
                        'product_name': content.get('title'),
                        'price': str(content.get('price', 'N/A')),
                        'main_image': content.get('images', [])[0] if content.get('images') else None,
                        'about_item': about_items,
                        'rating': str(content.get('rating', 'N/A')),
                        'description': description  # Now contains all bullet points combined
                    }
            elif marketplace == "Walmart":
                content = data['results'][0]['content']
                product_info = {
                    'product_id': content.get('general', {}).get('meta', {}).get('sku', 'sku'),
                    'url': url,
                    'product_name': content.get('general', {}).get('title'),
                    'main_image': content.get('general', {}).get('main_image') if content.get('general', {}).get('main_image') else None,
                    'price': str(content.get('price', {}).get('price', 'N/A')),
                    'about_item': [f"{s['key']} - {s['value']}" for s in content.get('specifications', {})],
                    'rating': str(content.get('rating', {}).get('rating', 'N/A')),
                    'description': content.get('general', {}).get('description', 'No description available')
                }
            elif marketplace == "BestBuy":
                content = data['results'][0]['content']
                product_info = {
                    'product_id': content.get('product_id', "product_id"),
                    'url': url,
                    'product_name': content.get('title'),
                    'main_image': content.get('general', {}).get('main_image') if content.get('general', {}).get('main_image') else None,
                    'price': str(content.get('price', {}).get('price', 'N/A')),
                    'about_item': content.get('bullet_points', '').split('\n'),
                    'rating': str(content.get('rating', {}).get('score', 'N/A')),
                    'description': content.get('general', {}).get('description', 'No description available')
                }
            elif marketplace == "Etsy":
                content = data['results'][0]['content']
                product_info = {
                    'product_id': content.get('product_id', "product_id"),
                    'url': url,
                    'product_name': content.get('title'),
                    'main_image': content.get('images')[0] if content.get('images') else None,
                    'price': str(content.get('price', 'N/A')),
                    'about_item': [a['title'] for a in content.get('categories')] if content.get('categories') else content.get('categories', '').split('\n'),
                    'rating': str(content.get('rating', {}).get('score', 'N/A')),
                    'description': content.get('general', {}).get('description', 'No description available')
                }
            elif marketplace == "Target":
                content = data['results'][0]['content']
                product_info = {
                    'product_id': content.get('product_id', "product_id"),
                    'url': url,
                    'product_name': content.get('title'),
                    'main_image': content.get('images')[0] if content.get('images') else None,
                    'price': str(content.get('price')),
                    'about_item': content.get('bullet_points', '').split('\n'),
                    'rating': str(content.get('rating_score', "N/A")),
                    'description': content.get('description', 'No description available')
                }
            elif marketplace == "eBay":
                content = data['results'][0]['content']
                product_info = {
                    'product_id': content.get('product_id', "product_id"),
                    'url': url,
                    'product_name': content.get('title'),
                    'main_image': content.get('image') if content.get('image') else None,
                    'price': str(content.get('price')),
                    'about_item': content.get('description', 'No description available').split('\n'),
                    'rating': str(content.get('rating_score', "N/A")),
                    'description': content.get('description', 'No description available')
                }
            
            # Print only the required fields
            print("\n=== Product Details ===")
            for key, value in product_info.items():
                if key != 'about_item':  # Skip printing the full about_item array
                    print(f"{key}: {value}")
            print("===================\n")
            
            return product_info
            
        except Exception as e:
            print(f"Error: {str(e)}")
            raise 