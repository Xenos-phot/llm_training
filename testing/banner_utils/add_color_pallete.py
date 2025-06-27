import openai
import os
import re
from dotenv import load_dotenv
load_dotenv()

def get_color_pallete(product_url):
    """
    Extract color palette from a product image URL using OpenAI GPT-4 Vision.
    
    Args:
        product_url (str): URL of the product image
        
    Returns:
        list: A list of dominant colors in the product image
    """
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Create the prompt for color palette extraction
        prompt = """
        Analyze this product image and tell me the color palette that can  be used to create a advertisement banner for this product.
        Tell how colors are used in the product image, how the colors are blended together, at the same time being highlighted.Also provide hex codes for the important colors. Please provide desription in 100 words.
        Please provide the response in the following structure:
        <description>
        ...
        </description>
        
        """
        
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": product_url,
                            }
                        }
                    ]
                }
            ],
            max_tokens=2560,
            
        )
        
        # Parse the response
        color_palette_text = response.choices[0].message.content
        match = re.search(r'<description>(.*?)</description>', color_palette_text, re.DOTALL)
        if match:
            color_palette_text = match.group(1)
        else:
            print(f"No description found in the response")
        return color_palette_text
        
    except Exception as e:
        print(f"Error processing image {product_url}: {str(e)}")
        return "This product features a neutral color palette with earthy tones including warm browns, beiges, and cream colors. The design incorporates subtle variations of tan and taupe shades that create a sophisticated and timeless appearance."\



# if __name__ == "__main__":
#     print(get_color_pallete("https://s3.us-east-2.wasabisys.com/ai-image-editor-webapp/test-images/65592cc4-1937-406a-9260-9904e6aa840c_nobg_1214x1439.png"))