import openai
import os
import re
import json
from dotenv import load_dotenv
load_dotenv()

def get_font_families(product_url, product_name, product_description):
    """
    Recommend font families from available fonts based on product image, name, and description using OpenAI GPT-4 Vision.
    
    Args:
        product_url (str): URL of the product image
        product_name (str): Name of the product
        product_description (str): Description of the product
        
    Returns:
        list: A list of up to 4 recommended font families from the available fonts
    """
    try:
        # Load available fonts from fonts.json
        fonts_file_path = os.path.join(os.path.dirname(__file__), '../../assets/fonts.json')
        with open(fonts_file_path, 'r', encoding='utf-8') as f:
            fonts_data = json.load(f)["english"]
        fontFamilyList = list(fonts_data.keys())
       
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Create the prompt for font recommendation
        prompt = f"""
        Analyze this product image along with the product name and description to recommend the most suitable top 4 font families for creating an advertisement banner.

        Product Name: {product_name}
        Product Description: {product_description}

        Consider the following factors:
        1. The product's target audience and market positioning
        2. The visual style and aesthetics of the product
        3. The brand personality conveyed by the product
        4. Typography that would complement the product's visual elements
        5. Readability and impact for advertisement purposes

        Available font families include:
        <fontFamilyList>
        {json.dumps(fontFamilyList)}
        </fontFamilyList>

        The font family MUST be selected from the available font families list.


        Please recommend exactly 4 font families from the available options that would work best for this product's advertisement banner. Consider different types of fonts that could be used for different text elements (headlines, subheadlines, tagline, cta etc.).

        Please provide the response in the following structure:
        <fonts>
        [
        "font1",
        "font2",
        "font3",
        "font4"
        ]
        </fonts>
        <explanation>
        Explanation of the font families selected.
        </explanation>
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
        response_text = response.choices[0].message.content
        print(response_text)
        match = re.search(r'<fonts>(.*?)</fonts>', response_text, re.DOTALL)
        if match:
            recommended_fonts = match.group(1).strip()
        else:
            start_index = response_text.find("[")
            end_index = response_text.rfind("]")
            recommended_fonts = response_text[start_index:end_index+1]
            
        data = json.loads(recommended_fonts)
        return data
            
        
    except Exception as e:
        print(f"Error processing product {product_name}: {str(e)}")
        # Return default fonts in case of error
        return ["Ultra-Regular", "League Spartan-Bold", "Alata Regular", "Ultra-Regular"],
        


# if __name__ == "__main__":
#     result = get_font_families(
#         "https://s3.us-east-2.wasabisys.com/ai-image-editor-webapp/test-images/65592cc4-1937-406a-9260-9904e6aa840c_nobg_1214x1439.png",
#         "Luxury Handbag",
#         "Premium leather handbag with elegant design, perfect for professional and casual occasions"
#     )
#     print("Recommended Fonts:", result["fonts"])
#     print("Explanation:", result["explanation"])
