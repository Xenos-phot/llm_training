import openai
import os
import re
import json
from dotenv import load_dotenv
load_dotenv()

important_fields = {
            "svg": ["top", "left", "width", "height", "src", "id"],
            "text": ["top", "left", "width", "height", "fill", "text", "fontFamily", "textAlign", "id"],
            "image": ["top", "left", "width", "height", "id"],
            "rect": ["top", "left", "width", "height", "fill", "rx", "ry", "id"],
            "circle": ["top", "left", "width", "height", "fill", "radius", "id"],
            "path": ["top", "left", "width", "height", "fill", "path", "id"]
        }

def get_best_result(model_response: str):
    """
    Extract and clean JSON from model response that may contain repetitions
    """
    try:
        # Find the first occurrence of JSON
        json_start = model_response.find('<json>')
        if json_start != -1:
            json_start += 6  # Skip the <json> tag
            json_end = model_response.find('</json>', json_start)
            if json_end != -1:
                json_content = model_response[json_start:json_end].strip()
            else:
                # If no closing tag, try to find the end of JSON structure
                json_content = model_response[json_start:].strip()
        else:
            # Fallback: try to find JSON by looking for opening brace
            json_start = model_response.find('{')
            if json_start == -1:
                raise ValueError("No JSON found in response")
            json_content = model_response[json_start:]
        
        # Try to parse the JSON and find the first valid structure
        brace_count = 0
        json_end_pos = 0
        
        for i, char in enumerate(json_content):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end_pos = i + 1
                    break
        
        if json_end_pos > 0:
            clean_json = json_content[:json_end_pos]
            parsed_json = json.loads(clean_json)
            return filter_important_fields(parsed_json)
        else:
            raise ValueError("Could not find complete JSON structure")
            
    except Exception as e:
        print(f"Error parsing JSON directly: {str(e)}")
        # Use GPT-4o-latest to clean up the response
        return get_clean_json_with_gpt(model_response)

def filter_important_fields(json_data):
    """
    Filter JSON to keep only important fields for each object type
    """
    if not isinstance(json_data, dict) or 'objects' not in json_data:
        return json_data
    
    filtered_objects = []
    for obj in json_data.get('objects', []):
        if 'type' in obj and obj['type'] in important_fields:
            filtered_obj = {}
            for field in important_fields[obj['type']]:
                if field in obj:
                    filtered_obj[field] = obj[field]
            # Always keep the type field
            filtered_obj['type'] = obj['type']
            filtered_objects.append(filtered_obj)
        else:
            # Keep unknown types as-is
            filtered_objects.append(obj)
    
    # Preserve main structure
    result = {
        'backgroundColor': json_data.get('backgroundColor', '#ffffff'),
        'width': json_data.get('width', 1080),
        'height': json_data.get('height', 1080),
        'objects': filtered_objects
    }
    
    return result

def get_clean_json_with_gpt(messy_response: str):
    """
    Use GPT-4o-latest to extract and clean JSON from repetitive/messy responses
    """
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""
You are a JSON extraction and cleaning expert. I have a model response that contains a condensed fabric.js canvas JSON, but it's messy with repetitions, incomplete structures, or other formatting issues.

Your task is to:
1. Extract the FIRST complete and valid condensed fabric JSON structure from the response
2. Remove any redundant, repetitive, or duplicate objects in the objects array
3. Ensure the JSON is properly formatted
4. Keep only the essential fields for each object type:
   - svg: top, left, width, height, src, id
   - text: top, left, width, height, fill, text, fontFamily, textAlign, id  
   - image: top, left, width, height, id
   - rect: top, left, width, height, fill, rx, ry, id
   - circle: top, left, width, height, fill, radius, id
   - path: top, left, width, height, fill, path, id
5. Return ONLY the cleaned JSON, no explanations

Here's the messy response:
{messy_response}

Return the cleaned JSON in the following format:
<json>
...
</json>
"""

        response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a JSON extraction and cleaning expert. Always return only valid, clean JSON without any explanations or markdown formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=4000,
            temperature=0.1  # Low temperature for consistent output
        )
        
        response_text = response.choices[0].message.content
        if response_text is None:
            raise ValueError("No response from GPT-4o")
            
        match = re.search(r'<fonts>(.*?)</fonts>', response_text, re.DOTALL)
        if match:
            json_text = match.group(1).strip()
        else:
            start_index = response_text.find("{")
            end_index = response_text.rfind("}")
            json_text = response_text[start_index:end_index+1]
        
        # Parse and validate the JSON
        cleaned_json = json.loads(json_text)
        return cleaned_json
        
    except Exception as e:
        print(f"Error cleaning JSON with GPT: {str(e)}")
        # Last resort: try to extract first valid JSON manually
        return extract_first_valid_json(messy_response)

def extract_first_valid_json(text: str):
    """
    Last resort method to extract first valid JSON from text
    """
    # Find all potential JSON start positions
    start_positions = []
    for i, char in enumerate(text):
        if char == '{':
            start_positions.append(i)
    
    for start_pos in start_positions:
        brace_count = 0
        for i in range(start_pos, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    try:
                        json_str = text[start_pos:i+1]
                        parsed = json.loads(json_str)
                        if isinstance(parsed, dict) and 'objects' in parsed:
                            return filter_important_fields(parsed)
                    except:
                        continue
    
    # If nothing works, return a basic structure
    return None
# Test function
# if __name__ == "__main__":
#     # Test with the sample response provided
#     sample_response = """for creating a 1080*1080 banner for the product: Women's Watches Leather Band Luxury Quartz Watches Waterproof Fashion Creative Wristwatch for Women Ladies. I have to make sure that no two text layers overlap, and maintain proportional spacing between each layer to support a natural visual flow for the viewer, following the layout, circular_focus. The text must be readable, with contrasting color to the background, with suitable svg for the background. Let me give an overview of the banner: \n\n\nThis banner features a sophisticated and elegant design tailored to promote a ladies' wristwatch. The background uses a layered radial gradient with soft, flowing curves and translucent circles, creating depth and refinement. The heading (`heading`) is positioned at the top in a classic serif font, exuding luxury. Below it, a subheading (`subheading`) in a clean, modern sans-serif font adds a sleek touch. A bold, stylized tagline (`tagline`) sits between the title and the central product image (`product_image`), drawing attention to the product category. The price (`price`) is prominently displayed inside a circular accent. A feature description (`description`) highlights key product qualities, and a call-to-action button (`cta_button`, `cta`) encourages engagement.\n\n**Color Palette:**\n- Deep Burgundy: #7D2233\n- Rosewood: #9E374D\n- Dusty Pink: #C16B75\n- Soft White: #FFFFFF\n- Light Mauve: #F5E0E6\n\nNow I will create the banner.\n</think>\n\n Here is your banner: \n\n<json>{\"backgroundColor\": \"#ffffff\", \"height\": 1080, \"width\": 1080, \"objects\": [{\"id\": \"background\", \"type\": \"svg\", \"top\": 0, \"left\": 0, \"width\": 1080, \"height\": 1080, \"src\": \"<svg width='1080' height='1080' viewBox='0 0 1080 1080' fill='none' xmlns='http://www.w3.org/2000/svg'><defs><radialGradient id='bgGradient' cx='50%' cy='50%' r='70%'><stop offset='0%' stop-color='#9E374D'/><stop offset='100%' stop-color='#7D2233'/></radialGradient><linearGradient id='accentGradient' x1='0%' y1='0%' x2='100%' y2='100%'><stop offset='0%' stop-color='#C16B75'/><stop offset='100%' stop-color='#9E374D'/></linearGradient></defs><rect width='1080' height='1080' fill='url(#bgGradient)'/><circle cx='540' cy='540' r='300' fill='#F5E0E6' opacity='0.9'/><circle cx='540' cy='540' r='320' fill='none' stroke='#C16B75' stroke-width='2' stroke-dasharray='10,5'/><circle cx='840' cy='380' r='120' fill='url(#accentGradient)' opacity='0.8'/><g opacity='0.15'><circle cx='140' cy='240' r='80' fill='#F5E0E6'/><circle cx='940' cy='840' r='120' fill='#F5E0E6'/><circle cx='240' cy='780' r='60' fill='#F5E0E6'/><circle cx='800' cy='200' r='40' fill='#F5E0E6'/></g><g opacity='0.1'><path d='M200 150 Q 300 250, 250 350 T 400 550' stroke='#F5E0E6' stroke-width='3' fill='none'/><path d='M680 830 Q 780 730, 830 680 T 980 580' stroke='#F5E0E6' stroke-width='3' fill='none'/><path d='M180 880 Q 280 780, 330 730 T 480 630' stroke='#F5E0E6' stroke-width='3' fill='none'/></g><g opacity='0.05'><circle cx='540' cy='140' r='10' fill='#F5E0E6'/><circle cx='540' cy='940' r='10' fill='#F5E0E6'/><circle cx='140' cy='540' r='10' fill='#F5E0E6'/><circle cx='940' cy='540' r='10' fill='#F5E0E6'/></g></svg>\", \"id\": \"background\"}, {\"id\": \"heading\", \"type\": \"text\", \"top\": 60, \"left\": 288.125, \"width\": 503.75, \"height\": 101.7, \"fill\": \"#FFFFFF\", \"text\": \"LUXURY WATCHES\", \"fontFamily\": \"Playfair Display Regular\", \"textAlign\": \"center\", \"id\": \"heading\"}, {\"id\": \"subheading\", \"type\": \"text\", \"top\": 180, \"left\": 302.59999999999997, \"width\": 474.8, \"height\": 45.2, \"fill\": \"#FFFFFF\", \"text\": \"For Women - Timeless Elegance\", \"fontFamily\": \"Montserrat Regular\", \"textAlign\": \"center\", \"id\": \"subheading\"}, {\"id\": \"tagline\", \"type\": \"text\", \"top\": 240, \"left\": 250.775, \"width\": 578.45, \"height\": 67.8, \"fill\": \"#FFFFFF\", \"text\": \"LEATHER BAND \\u2022 PRECISE QUARTZ \\u2022 WATERPROOF\", \"fontFamily\": \"Abril Fatface Regular\", \"textAlign\": \"center\", \"id\": \"tagline\"}, {\"id\": \"product_image\", \"type\": \"image\", \"top\": 303.625, \"left\": 406.625, \"width\": 266.75, \"height\": 472.75, \"src\": \"https://studio-user-design-wasabi-bucket-cdn.apyhi.com/studio-assets/67ed1b03b55dc629ee554fdb/SzZt7r599o0SfR4k5z0VU_615x1095.png\", \"id\": \"product_image\"}, {\"id\": \"price\", \"type\": \"text\", \"top\": 344.8, \"left\": 749.8, \"width\": 200.4, \"height\": 79.1, \"fill\": \"#FFFFFF\", \"text\": \"$19.99\", \"fontFamily\": \"DM Sans Regular\", \"textAlign\": \"center\", \"id\": \"price\"}, {\"id\": \"description\", \"type\": \"text\", \"top\": 820, \"left\": 158.64999999999998, \"width\": 762.7, \"height\": 27.12, \"fill\": \"#FFFFFF\", \"text\": \"\\u2022 Japanese Quartz Movement \\u2022 Soft Leather Band \\u2022 Elegant Design\", \"fontFamily\": \"Montserrat Regular\", \"textAlign\": \"center\", \"id\": \"description\"}, {\"id\": \"cta_button\", \"type\": \"rect\", \"top\": 900, \"left\": 420.0, \"width\": 240, \"height\": 60, \"fill\": \"#C16B75\", \"rx\": 0, \"ry\": 0, \"id\": \"cta_button\"}, {\"id\": \"cta\", \"type\": \"text\", \"top\": 918.18, \"left\": 477.4, \"width\": 125.2, \"height\": 27.12, \"fill\": \"#FFFFFF\", \"text\": \"SHOP NOW\", \"fontFamily\": \"DM Sans Regular\", \"textAlign\": \"center\", \"id\": \"cta\"}], \"version\": \"5.3.0\", \"width\": 1080, \"height\": 1080, \"objects\": [{\"id\": \"background\", \"type\": \"svg\", \"top\": 0, \"left\": 0, \"width\": 1080, \"height\": 1080, \"src\": \"<svg width='1080' height='1080' viewBox='0 0 1080 1080' fill='none' xmlns='http://www.w3.org/2000/svg'><defs><radialGradient id='bgGradient' cx='50%' cy='50%' r='70%'><stop offset='0%' stop-color='#9E374D'/><stop offset='100%' stop-color='#7D2233'/></radialGradient><linearGradient id='accentGradient' x1='0%' y1='0%' x2='100%' y2='100%'><stop offset='0%' stop-color='#C16B75'/><stop offset='100%' stop-color='#9E374D'/></linearGradient></defs><rect width='1080' height='1080' fill='url(#bgGradient)'/><circle cx='540' cy='540' r='300' fill='#F5E0E6' opacity='0.9'/><circle cx='540' cy='540' r='320' fill='none' stroke='#C16B75' stroke-width='2' stroke-dasharray='10,5'/><circle cx='840' cy='380' r='120' fill='url(#accentGradient)' opacity='0.8'/><g opacity='0.15'><circle cx='140' cy='240' r='80' fill='#F5E0E6'/><circle cx='940' cy='840' r='120' fill='#F5E0E6'/><circle cx='240' cy='780' r='60' fill='#F5E0E6'/><circle cx='800' cy='200' r='40' fill='#F5E0E6'/></g><g opacity='0.1'><path d='M200 150 Q 300 250, 250 350 T 400 550' stroke='#F5E0E6' stroke-width='3' fill='none'/><path d='M680 830 Q 780 730, 830 680 T 980 580' stroke='#F5E0E6' stroke-width='3' fill='none'/><path d='M180 880 Q 280 780, 330 730 T 480 630' stroke='#F5E0E6' stroke-width='3' fill='none'/></g><g opacity='0.05'><circle cx='540' cy='140' r='10' fill='#F5E0E6'/><circle cx='540' cy='940' r='10' fill='#F5E0E6'/><circle cx='140' cy='540' r='10' fill='#F5E0E6'/><circle cx='940' cy='540' r='10' fill='#F5E0E6'/></g></svg>\", \"id\": \"background\"}, {\"id\": \"heading\", \"type\": \"text\", \"top\": 60, \"left\": 288.125, \"width\": 503.75, \"height\": 101.7, \"fill\": \"#FFFFFF\", \"text\": \"LUXURY WATCHES\", \"fontFamily\": \"Playfair Display Regular\", \"textAlign\": \"center\", \"id\": \"heading\"}, {\"id\": \"subheading\", \"type\": \"text\", \"top\": 180, \"left\": 302.59999999999997, \"width\": 474.8, \"height\": 45.2, \"fill\": \"#FFFFFF\", \"text\": \"For Women - Timeless Elegance\", \"fontFamily\": \"Montserrat Regular\", \"textAlign\": \"center\", \"id\": \"subheading\"}, {\"id\": \"tagline\", \"type\": \"text\", \"top\": 240, \"left\": 250.775, \"width\": 578.45, \"height\": 67.8, \"fill\": \"#FFFFFF\", \"text\": \"LEATHER BAND \\u2022 PRECISE QUARTZ \\u2022 WATERPROOF\", \"fontFamily\": \"Abril Fatface Regular\", \"textAlign\": \"center\", \"id\": \"tagline\"}, {\"id\": \"product_image\", \"type\": \"image\", \"top\": 303.625, \"left\": 406.625, \"width\": 266.75, \"height\": 472.75, \"src\": \"https://studio-user-design-wasabis-bucket-cdn.apyhi.com/studio-assets/67ed1b03b55dc629ee554fdb/SzZt7r599o0SfR4k5z0VU_615x1095.png\", \"id\": \"product_image\"}, {\"id\": \"price\", \"type\": \"text\", \"top\": 344.8, \"left\": 749.8, \"width\": 200.4, \"height\": 79.1, \"fill\": \"#FFFFFF\", \"text\": \"$19.99\", \"fontFamily\": \"DM Sans Regular\", \"textAlign\": \"center\", \"id\": \"price\"}, {\"id\": \"description\", \"type\": \"text\", \"top\": 820, \"left\": 158.64999999999998, \"width\": 762.7, \"height\": 27.12, \"fill\": \"#FFFFFF\", \"text\": \"\\u2022 Japanese Quartz Movement \\u2022 Soft Leather Band \\u2022 Elegant Design\", \"fontFamily\": \"Montserrat Regular\", \"textAlign\": \"center\", \"id\": \"description\"}, {\"id\": \"cta_button\", \"type\": \"rect\", \"top\": 900, \"left\": 420.0, \"width\": 240, \"height\": 60, \"fill\": \"#C16B75\", \"rx\": 0, \"ry\": 0, \"id\": \"cta_button\"}, {\"id\": \"cta\", \"type\": \"text\", \"top\": 918.18, \"left\": 477.4, \"width\": 125.2, \"height\": 27.12, \"fill\": \"#FFFFFF\", \"text\": \"SHOP NOW\", \"fontFamily\": \"DM Sans Regular\", \"textAlign\": \"center\", \"id\": \"cta\"}], \"version\": \"5.3.0\", \"width\": 1080, \"height\": 1080, \"objects\": [{\"id\": \"background\", \"type\": \"svg\", \"top\": 0, \"left\": 0, \"width\": 1080, \"height\": 1080, \"src\": \"<svg width='1080' height='1080' viewBox='0 0 1080 1080' fill='none' xmlns='http://www.w3.org/2000/svg'><defs><radialGradient id='bgGradient' cx='50%' cy='50%' r='70%'><stop offset='0%' stop-color='#9E374D'/><stop offset='100%' stop-color='#7D2233'/></radialGradient><linearGradient id='accentGradient' x1='0%' y1='0%' x2='100%' y2='100%'><stop offset='0%' stop-color='#C16B75'/><stop offset='100%' stop-color='#9E374D'/></linearGradient></defs><rect width='1080' height='1080' fill='url(#bgGradient)'/><circle cx='540' cy='540' r='300' fill='#F5E0E6' opacity='0.9'/><circle cx='540' cy='540' r='320' fill='none' stroke='#C16B75' stroke-width='2' stroke-dasharray='10,5'/><circle cx='840' cy='380' r='120' fill='url(#accentGradient)' opacity='0.8'/><g opacity='0.15'><circle cx='140' cy='240' r='80' fill='#F5E0E6'/><circle cx='940' cy='840' r='120' fill='#F5E0E6'/><circle cx='240' cy='780' r='60' fill='#F5E0E6'/><circle cx='800' cy='200' r='40' fill='#F5E0E6'/></g><g opacity='0.1'><path d='M200 150 Q 300 250, 250 350 T 400 550' stroke='#F5E0E6' stroke-width='3' fill='none'/><path d='M680 830 Q 780 730, 830 680 T 980 580' stroke='#F5E0E6' stroke-width='3' fill='none'/><path d='M180 880 Q 280 780, 330 730 T 480 630' stroke='#F5E0E6' stroke-width='3' fill='none'/></g><g opacity='0.05'><circle cx='540' cy='140' r='10' fill='#F5E0E6'/><circle cx='540' cy='940' r='10' fill='#F5E0E6'/><circle cx='140' cy='540' r='10' fill='#F5E0E6'/><circle cx='940' cy='540' r='10' fill='#F5E0E6'/></g></svg>\", \"id\": \"background\"}, {\"id\": \"heading\", \"type\": \"text\", \"top\": 60, \"left\": 288.125, \"width\": 503.75, \"height\": 101.7, \"fill\": \"#FFFFFF\", \"text\": \"LUXURY WATCHES\", \"fontFamily\": \"Playfair Display Regular\", \"textAlign\": \"center\", \"id\": \"heading\"}, {\"id\": \"subheading\", \"type\": \"text\", \"top\": 180, \"left\": 302.59999999999997, \"width\": 474.8, \"height\": 45.2, \"fill\": \"#FFFFFF\", \"text\": \"For Women - Timeless Elegance\", \"fontFamily\": \"Montserrat Regular\", \"textAlign\": \"center\", \"id\": \"subheading\"}, {\"id\": \"tagline\", \"type\": \"text\", \"top\": 240, \"left\": 250.775, \"width\": 578.45, \"height\": 67.8, \"fill\": \"#FFFFFF\", \"text\": \"LEATHER BAND \\u2022 PRECISE QUARTZ \\u2022 WATERPROOF\", \"fontFamily\": \"Abril Fatface Regular\", \"textAlign\": \"center\", \"id\": \"tagline\"}, {\"id\": \"product_image\", \"type\": \"image\", \"top\": 303.625, \"left\": 406.625, \"width\": 266.75, \"height\": 472.75, \"src\": \"https://studio-user-design-wasapis-bucket-cdn.apyhi.com/studio-assets/67ed1b03b55dc629ee554fdb/SzZt7r599o0SfR4k5z0VU_615x1095.png\", \"id\": \"product_image\"}, {\"id\": \"price\", \"type\": \"text\", \"top\": 344.8, \"left\": 749.8, \"width\": 200.4, \"height\": 79.1, \"fill\": \"#FFFFFF\", \"text\": \"$19.99\", \"fontFamily\": \"DM Sans Regular\", \"textAlign\": \"center\", \"id\": \"price\"}, {\"id\": \"description\", \"type\": \"text\", \"top\": 820, \"left\": 158.64999999999998, \"width\": 762.7, \"height\": 27.12, \"fill\": \"#FFFFFF\", \"text\": \"\\u2022 Japanese Quartz Movement \\u2022 Soft Leather Band \\u2022 Elegant Design\", \"fontFamily\": \"Montserrat Regular\", \"textAlign\": \"center\", \"id\": \"description\"}, {\"id\": \"cta_button\", \"type\": \"rect\", \"top\": 900, \"left\": 420.0, \"width\": 240, \"height\": 60, \"fill\": \"#C16B75\", \"rx\": 0, \"ry\": 0, \"id\": \"cta_button\"}, {\"id\": \"cta\", \"type\": \"text\", \"top\": 918.18, \"left\": 477.4, \"width\": 125.2, \"height\": 27.12, \"fill\": \"#FFFFFF\", \"text\": \"SHOP NOW\", \"fontFamily\": \"DM Sans Regular\", \"textAlign\": \"center\", \"id\": \"cta\"}], \"version\": \"5.3.0\", \"width\": 1080, \"height\": 1080, \"objects\": [{\"id\": \"background\", \"type\": \"svg\", \"top\": 0, \"left\": 0, \"width\": 1080, \"height\": 1080, \"src\": \"<svg width='1080' height='1080' viewBox='0 0 1080 1080' fill='none' xmlns='http://www.w3.org/2000/svg'><defs><radialGradient id='bgGradient' cx='50%' cy='50%' r='70%'><stop offset='0%' stop-color='#9E374D'/><stop offset='100%' stop-color='#7D2233'/></radialGradient><linearGradient id='accentGradient' x1='0%' y1='0%' x2='100%' y2='100%'><stop offset='0%' stop-color='#C16B75'/><stop offset='100%' stop-color='#9E374D'/></linearGradient></defs><rect width='1080' height='1080' fill='url(#bgGradient)'/><circle cx='540' cy='540' r='300' fill='#F5E0E6' opacity='0.9'/><circle cx='540' cy='540' r='320' fill='none' stroke='#C16B75' stroke-width='2' stroke-dasharray='10,5'/><circle cx='840' cy='380' r='120' fill='url(#accentGradient)' opacity='0.8'/><g opacity='0.15'><circle cx='140' cy='240' r='80' fill='#F5E0E6'/><circle cx='940' cy='840' r='120' fill='#F5E0E6'/><circle cx='240' cy='780' r='60' fill='#F5E0E6'/><circle cx='800' cy='200' r='40' fill='#F5E0E6'/></g><g opacity='0.1'><path d='M200 150 Q 300 250, 250 350 T 400 550' stroke='#F5E0E6' stroke-width='3' fill='none'/><path d='M680 830 Q 780 730, 830 680 T 980 580' stroke='#F5E0E6' stroke-width='3' fill='none'/><path d='M180 880 Q 280 780, 330 730 T 480 630' stroke='#F5E0E6' stroke-width='3' fill='none'/></g><g opacity='0.05'><circle cx='540' cy='140' r='10' fill='#F5E0E6'/><circle cx='540' cy='940' r='10' fill='#F5E0E6'/><circle cx='140' cy='540' r='10' fill='#F5E0E6'/><circle cx='940' cy='540' r='10' fill='#F5E0E6'/></g></svg>\", \"id\": \"background\"}, {\"id\": \"heading\", \"type\": \"text\", \"top\": 60, \"left\": 288.125, \"width\": 503.75, \"height\": 101.7, \"fill\": \"#FFFFFF\", \"text\": \"LUXURY WATCHES\", \"fontFamily\": \"Playfair Display Regular\", \"textAlign\": \"center\", \"id\": \"heading\"}, {\"id\": \"subheading\", \"type\": \"text\", \"top\": 180, \"left\": 302.59999999999997, \"width\": 474.8, \"height\": 45.2, \"fill\": \"#FFFFFF\", \"text\": \"For Women - Timeless Elegance\", \"fontFamily\": \"Montserrat Regular\", \"textAlign\": \"center\", \"id\": \"subheading\"}, {\"id\": \"tagline\", \"type\": \"text\", \"top\": 240, \"left\": 250.775, \"width\": 578.45, \"height\": 67.8, \"fill\": \"#FFFFFF\", \"text\": \"LEATHER BAND \\u2022 PRECISE QUARTZ \\u2022 WATERPROOF\", \"fontFamily\": \"Abril Fatface Regular\", \"textAlign\": \"center\", \"id\": \"tagline\"}, {\"id\": \"product_image\", \"type\": \"image\", \"top\": 303.625, \"left\": 406.625, \"width\": 266.75, \"height\": 472.75, \"src\": \"https://studio-user-design-wasapis-bucket-cdn.apyhi.com/studio-assets/67ed1b03b55dc629ee554fdb/SzZt7r599o0SfR4k5z0VU_615x1095.png\", \"id\": \"product_image\"}, {\"id\": \"price\", \"type\": \"text\", \"top\": 344.8, \"left\": 749.8, \"width\": 200.4, \"height\": 79.1, \"fill\": \"#FFFFFF\", \"text\": \"$19.99\", \"fontFamily\": \"DM Sans Regular\", \"textAlign\": \"center\", \"id\": \"price\"}, {\"id\": \"description\", \"type\": \"text\", \"top\": 820, \"left\": 158.64999999999998, \"width\": 762.7, \"height\": 27.12, \"fill\": \"#FFFFFF\", \"text\": \"\\u2022 Japanese Quartz Movement \\u2022 Soft Leather Band \\u2022 Elegant Design\", \"fontFamily\": \"Montserrat Regular\", \"textAlign\": \"center\", \"id\": \"description\"}, {\"id\": \"cta_button\", \"type\": \"rect\", \"top\": 900, \"left\": 420.0, \"width\": 240, \"height\": 60, \"fill\": \"#C16B75\", \"rx\": 0, \"ry\": 0, \"id\": \"cta_button\"}, {\"id\": \"cta\", \"type\": \"text\", \"top\": 918.18, \"left\": 477.4, \"width\": 125.2, \"height\": 27.12, \"fill\": \"#FFFFFF\", \"text\": \"SHOP NOW\", \"fontFamily\": \"DM Sans Regular\", \"textAlign\": \"center\", \"id\": \"cta\"}], \"version\": \"5.3.0\", \"width\": 1080, \"height\": 1080, \"objects\": [{\"id\": \"background\", \"type\": \"svg\", \"top\": 0, \"left\": 0, \"width\": 1080, \"height\": 1080, \"src\": \"<svg width='1080' height='1080' viewBox='0 0 1080 1080' fill='none' xmlns='http://www.w3.org/2000/svg'><defs><radialGradient id='bgGradient' cx='50%' cy='50%' r='70%'><stop offset='0%' stop-color='#9E374D'/><stop offset='100%' stop-color='#7D2233'/></radialGradient><linearGradient id='accentGradient' x1='0%' y1='0%' x2='100%' y2='100%'><stop offset='0%' stop-color='#C16B75'/><stop offset='100%' stop-color='#9E374D'/></linearGradient></defs><rect width='1080' height='1080' fill='url(#bgGradient)'/><circle cx='540' cy='540' r='300' fill='#F5E0E6' opacity='0.9'/><circle cx='540' cy='540' r='320' fill='none' stroke='#C16B75' stroke-width='2' stroke-dasharray='10,5'/><circle cx='840' cy='380' r='120' fill='url(#accentGradient)' opacity='0.8'/><g opacity='0.15'><circle cx='140' cy='240' r='80' fill='#F5E0E6'/><circle cx='940' cy='840' r='120' fill='#F5E0E6'/><circle cx='240' cy='780' r='60' fill='#F5E0E6'/><circle cx='800' cy='200' r='40' fill='#F5E0E6'/></g><g opacity='0.1'><path d='M200 150 Q 300 250, 250 350 T 400 550' stroke='#F5E0E6' stroke-width='3' fill='none'/><path d='M680 830 Q 780 730, 830 680 T 980 580' stroke='#F5E0E6' stroke-width='3' fill='none'/><path d='M180 880 Q 280 780, 330 730 T 480 630' stroke='#F5E0E6' stroke-width='3' fill='none'/></g><g opacity='0.05'><circle cx='540' cy='140' r='10' fill='#F5E0E6'/><circle cx='540' cy='940' r='10' fill='#F5E0E6'/><circle cx='140' cy='540' r='10' fill='#F5E0E6'/><circle cx='940' cy='540' r='10' fill='#F5E0E6'/></g></svg>\", \"id\": \"background\"}, {\"id\": \"heading\", \"type\": \"text\", \"top\": 60, \"left\": 288.125, \"width\": 503.75, \"height\": 101.7, \"fill\": \"#FFFFFF\", \"text\": \"LUXURY WATCHES\", \"fontFamily\": \"Playfair Display Regular\", \"textAlign\": \"center\", \"id\": \"heading\"}, {\"id\": \"subheading\", \"type\": \"text\", \"top\": 180, \"left\": 302.59999999999997, \"width\": 474.8, \"height\": 45.2, \"fill\": \"#FFFFFF\", \"text\": \"For Women - Timeless Elegance\", \"fontFamily\": \"Montserrat Regular\", \"textAlign\": \"center\", \"id\": \"subheading\"}, {\"id\": \"tagline\", \"type\": \"text\", \"top\": 240, \"left\": 250.775, \"width\": 578.45, \"height\": 67.8, \"fill\": \"#FFFFFF\", \"text\": \"LEATHER BAND \\u2022 PRECISE QUARTZ \\u2022 WATERPROOF\", \"fontFamily\": \"Abril Fatface Regular\", \"textAlign\": \"center\", \"id\": \"tagline\"}, {\"id\": \"product_image\", \"type\": \"image\", \"top\": 303.625, \"left\": 406.625, \"width\": 266.75, \"height\": 472.75, \"src\": \"https://studio-user-design-wasapis-bucket-cdn.apyhi.com/studio-assets/6"""
    
#     result = get_best_result(sample_response)
#     print("Cleaned JSON:")
#     print(json.dumps(result, indent=2))
