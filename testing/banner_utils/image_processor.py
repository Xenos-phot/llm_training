import os
import requests
import json
import time
import fal_client
from PIL import Image
import uuid
from io import BytesIO
import base64
from boto3 import resource
import cv2
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

class ImageProcessor:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get Wasabi credentials from environment variables
        self.aws_access_key_id = os.getenv('WASABI_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.getenv('WASABI_SECRET_ACCESS_KEY')
        self.endpoint_url = os.getenv('WASABI_ENDPOINT_URL')
        self.bucket_name = os.getenv('WASABI_BUCKET_NAME')
        
        # Validate credentials
        if not all([self.aws_access_key_id, self.aws_secret_access_key, 
                   self.endpoint_url, self.bucket_name]):
            raise ValueError("Missing required Wasabi credentials in environment variables")


    def _on_queue_update(self, update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
               print(log["message"])



    def process_image_url(self, image_url: str, banner_width: int, banner_height: int) -> str:
        """
        Main function to process image: download, remove background, and upload to Wasabi
        Returns the new Wasabi URL
        """
        try:
            # Download image from URL
            BI_REF = False
            if BI_REF:
                result = fal_client.subscribe(
                    "fal-ai/birefnet/v2",
                    arguments={
                        "image_url": image_url
                    },
                    with_logs=True,
                    on_queue_update=self._on_queue_update,
                )
                bg_removed_url = result.get("image").get("url")
                response = requests.get(bg_removed_url)
                if response.status_code != 200:
                    raise Exception("Failed to download image")
                bg_removed_path = f"tmp/{uuid.uuid4()}.png"
                with open(bg_removed_path, 'wb') as f:
                    f.write(response.content)
                temp_path = bg_removed_path
            else:
                temp_path = self._download_image(image_url)
                
                # Convert to PNG if needed
                temp_path = self._convert_to_png(temp_path)
                
                # Remove background
                bg_removed_path = self._remove_background(temp_path)
            # # Crop to content
            cropped_image_path   = self._crop_to_content(bg_removed_path, banner_width, banner_height, BI_REF)
            # Upload to Wasabi
            wasabi_url = self._upload_to_wasabi(cropped_image_path)
            
            # Cleanup temporary files
            self._cleanup_files([temp_path, cropped_image_path, bg_removed_path])
            
            return wasabi_url
            
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            raise

    def _download_image(self, url: str, path: str = f"tmp/{uuid.uuid4()}.png") -> str:
        """Download image from URL and save temporarily"""
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("Failed to download image")
            
        with open(path, 'wb') as f:
            f.write(response.content)
        return path

    def _convert_to_png(self, image_path: str) -> str:
        """Convert image to PNG if it's not already"""
        if image_path.lower().endswith('.png'):
            return image_path
            
        try:
            img = Image.open(image_path)
            new_path = image_path[:image_path.rfind('.')] + '.png'
            img.save(new_path, 'PNG')
            img.close()
            os.remove(image_path)
            return new_path
        except Exception as e:
            raise Exception(f"Error converting to PNG: {str(e)}")

    def _remove_background(self, image_path: str) -> str:
        """Remove background from image"""
        try:
            # Open and resize image if needed
            img = Image.open(image_path)
            img.thumbnail([1440, 1440])
            
            # Get mask from API
            response = self._get_mask_from_api(img)
            
            # Retry once if failed
            if 'output_image' not in response:
                print("First attempt FAILED, retrying...")
                response = self._get_mask_from_api(img)
                
            if 'output_image' not in response:
                raise Exception("Background removal failed after retry")
            
            # Process the mask and create output image
            mask = Image.open(BytesIO(base64.b64decode(response['output_image'])))
            output_image = Image.composite(
                img, 
                Image.new("RGBA", img.size, (255, 255, 255, 0)), 
                mask.convert('L')
            )
            
            # Save the processed image
            output_path = image_path.replace('.png', '_nobg.png')
            output_image.save(output_path, 'PNG')
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Error removing background: {str(e)}")

    def _get_mask_from_api(self, img: Image) -> dict:
        """Get mask from background removal API"""
        url = 'https://static-aws-ml1.phot.ai/v1/models/transparent-bgremover-model:predict'
        headers = {"Content-Type": "application/json"}
        
        # Convert image to base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Prepare API request
        data = {
            "instances": [{
                "image": {
                    "b64": img_base64
                }
            }]
        }
        
        # Make API call
        response = requests.post(url, json=data, headers=headers)
        return json.loads(response.text)

    def _get_maskurl_from_api(self, img_url: str=None, b64_image: str= None) -> dict:
        """Get mask from background removal API"""
        url = 'https://static-aws-ml1.phot.ai/v1/models/transparent-bgremover-model:predict'
        headers = {"Content-Type": "application/json"}
        # Prepare API request
        if not b64_image:
            data = {
                "instances": [{
                    "image": {
                    "url": img_url
                }
            }]
        }
        else:
            data = {
                "instances": [{
                    "image": {
                    "b64": b64_image
                }
            }]
        }
        # Make API call
        response = requests.post(url, json=data, headers=headers)
        return json.loads(response.text)

    def _crop_to_content(self, image_path: str, banner_width: int, banner_height: int, BI_REF: bool) -> str:
        """
        Crops a background-removed image to the smallest rectangle containing the main object.
        
        Args:
            image_path: Path to the background-removed image
            banner_width: Width of the banner
            banner_height: Height of the banner
        Returns:
            Path to the cropped image
        """
        try:
            # Read the image
            if BI_REF:
                print(BI_REF)
                img = Image.open(image_path)
                img.thumbnail([1440, 1440])
                img.save(image_path)
            img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            print(img.shape)
            # Convert to grayscale if image has alpha channel
            if img.shape[-1] == 4:
                # Use alpha channel for finding content
                mask = img[:, :, 3]
            else:
                # Convert to grayscale for RGB images
                mask = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
            # Find non-zero points (content)
            coords = np.argwhere(mask > 0)
            
            # Find the bounding rectangle
            y_min, x_min = coords.min(axis=0)
            y_max, x_max = coords.max(axis=0)
            
            # Add small padding (optional)
            # padding_y = banner_height * 0.1
            # padding_x = banner_width * 0.1
            padding_y = 0
            padding_x = 0
            y_min = int(max(0, y_min - padding_y))
            y_max = int(min(img.shape[0], y_max + padding_y))
            x_min = int(max(0, x_min - padding_x))
            x_max = int(min(img.shape[1], x_max + padding_x))
            # Crop the image
            cropped = img[y_min:y_max, x_min:x_max]
            
            # Save the cropped image
            output_path = image_path.replace('.', '_cropped.')
            cv2.imwrite(output_path, cropped)
        except Exception as e:
            raise Exception(f"Error cropping image: {str(e)}")
        
        return output_path
            
    def image_to_base64(self, image: Image) -> str:
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        return img_base64
    
    def url_to_base64(self, url: str) -> str:
        response = requests.get(url)
        img_base64 = base64.b64encode(response.content).decode()
        return img_base64
    
    def path_to_base64(self, path: str) -> str:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def resize_and_compress_image(self, image_path, max_size_mb=4.5, output_path=None):
        # Open the image
        image = Image.open(image_path)

        # Check the current file size
        file_size = os.path.getsize(image_path) / (1024 * 1024)  # size in MB
        print(f"Current file size: {file_size:.2f} MB")
        # If the file size is greater than max_size_mb, reduce the image
        if file_size > max_size_mb:
            # Resize the image if necessary to reduce file size
            width, height = image.size
            aspect_ratio = width / height
            if width > 2048:  # If width is greater than 2K
                new_width = 2048
                new_height = int(new_width / aspect_ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Handle RGBA images
            has_alpha = image.mode == 'RGBA'
            print(f"Has alpha: {has_alpha}")
            if has_alpha:
                # Keep original RGBA image
                quality = 95  # Start with high quality
                if output_path is None:
                    output_path = image_path  # Overwrite original image if no output path provided
                
                # Reduce quality until the file size is under the limit
                while True:
                    image.save(output_path, "PNG", optimize=True)
                    file_size = os.path.getsize(output_path) / (1024 * 1024)  # size in MB
                    if file_size <= max_size_mb or quality <= 10:
                        break
                    quality -= 5  # Decrease quality incrementally
            else:
                # Convert to RGB if no alpha
                if image.format != 'JPEG':
                    image = image.convert('RGB')
                
                # Save the image with reduced quality to reduce size
                quality = 95  # Start with high quality
                if output_path is None:
                    output_path = image_path  # Overwrite original image if no output path provided
                
                # Reduce quality until the file size is under the limit
                while True:
                    image.save(output_path, "JPEG", quality=quality, optimize=True)
                    file_size = os.path.getsize(output_path) / (1024 * 1024)  # size in MB
                    if file_size <= max_size_mb or quality <= 10:
                        break
                    quality -= 5  # Decrease quality incrementally
                
            print(f"Image saved at {output_path} with size: {file_size:.2f} MB")
        else:
            print(f"Image is already under {max_size_mb} MB, no resizing needed.")
            return image  # Return original image if no resizing is needed

        return image  # Return the resized/compressed image



    def _upload_to_wasabi(self, image_path: str) -> str:
        """Upload image to Wasabi and return URL"""
        try:
            if isinstance(image_path, Image.Image):
                temp_path = f"tmp/{uuid.uuid4()}.png"
                image_path.save(temp_path)
                image_path = temp_path
            
            elif image_path.startswith('http'):
                image_path = self._download_image(image_path)
            
            # Get image dimensions
            image = self.resize_and_compress_image(image_path)
            width, height = image.size

            # Initialize Wasabi client
            s3_client = resource(
                service_name="s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key
            )

            # Generate unique filename with dimensions and nobg indicator
            file_name = f"{uuid.uuid4()}_nobg_{width}x{height}.png"
            
            # Upload file
            bucket = s3_client.Bucket(self.bucket_name)
            bucket.upload_file(image_path, f"test-images/{file_name}")
            
            # Return public URL
            return f"{self.endpoint_url}{self.bucket_name}/test-images/{file_name}"
            
        except Exception as e:
            raise Exception(f"Error uploading to Wasabi: {str(e)}")

    def _cleanup_files(self, file_paths: list):
        """Clean up temporary files"""
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Error cleaning up {path}: {str(e)}")

    def resize_image(self, image_path: str,min_dimension: int =1024, width: int = None, height: int = None) -> str:
        """Resize image to given width and height maintaining aspect ratio"""
        image = Image.open(image_path)
        if min_dimension == image.size[0] or min_dimension == image.size[1]:
            return image_path

        if width and height:
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        else:
            original_width, original_height = image.size
            aspect_ratio = original_width / original_height
            if original_width > original_height:
                new_height = min_dimension
                new_width = int(new_height * aspect_ratio)
            else:
                new_width = min_dimension
                new_height = int(new_width / aspect_ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        print(image.size)
        image.save(image_path)
        return image_path

    def enhance_prompt(self, prompt: str, image_url: str) -> str:
        """Enhance prompt using OpenAI"""
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        openai_time = time.time()
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                {"role": "developer", "content": """You are an expert prompt engineer with deep expertise in generating background for product photography advertisement banners. You are given a product image and a basic background description. You need to give a detailed description of the real-life background scene focussing on the foreground product(creating focus on the foreground product using blur etc.), giving a perfect background for product photography ad banner.
                 
                 
                <Guidelines>
                - Understand the product image and its natural placement while generating the background.
                - Mention clearly a description of the natural placement of the foreground product in the image.
                - Make sure the foreground product is in focus and the background is coherent to the product.
                - Understand the basic prompt given by the user and enhance it to make it more detailed description of the background scene.
                - Add blur, bokeh, depth of field, etc to the highlight the foreground product.
                - Each generated prompt MUST follow a structured format:
                    1. First sentence: Describe the overall background, with very detailed description about the placement of the foreground product.
                    2. Next sentences: Provide detailed descriptions of background features, lighting, textures, and special effects around the foreground product.
                    3. Final sentences: Emphasize blurring, depth, and other important details.
                  </Guidelines>"""},
                
                {"role": "user", "content": [
                    {"type": "text", "text": "**Product image:** "},
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": "Clearly understand the product image and its natural placement while generating the background"},
                    {"type": "text", "text": """**General rules**
                    - NEVER mention the product in the background description, only describe the background details that enhance the product.
                    - NEVER leave the foreground product hanging in the air, ALWAYS mention in detail the placement of the foreground product, in the image.
                    """},
                    {"type": "text", "text": "**Basic background description:** "},
                    {"type": "text", "text": prompt},
                ]}
                ]
            )
            print(f"OpenAI Prompt Enhancement time: {time.time() - openai_time} seconds")
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error enhancing prompt: {str(e)}")