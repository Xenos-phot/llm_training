import json
from unsloth import FastLanguageModel
import torch
import time
from PIL import Image
import requests
from banner_utils.create_condensed_data import get_original_data
from banner_utils.add_color_pallete import get_color_pallete
from banner_utils.give_font_family import get_font_families

def load_model(checkpoint_path):
    """Load the fine-tuned model from checkpoint"""
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=checkpoint_path,
        max_seq_length=8192,
        load_in_4bit=True,
        load_in_8bit=False,
        full_finetuning=False,
    )
    return model, tokenizer

def prepare_input(product_name, product_description, product_price, layout, layout_template, product_color="", fontFamilyList=[]):
    """Prepare input text for the model based on training format"""
    
    # Handle empty fields as in training
    if product_name == "":
        product_name = "Product Name Not Available"
    if product_description == "":
        product_description = "Product Details Not Available"
    if product_price == "":
        product_price = "Product Price Not Available"
    
    important_fields = {
        "svg": ["top", "left", "width", "height", "src", "id"],
        "text": ["top", "left", "width", "height", "fill", "text", "fontSize", "fontFamily", "textAlign", "id"],
        "image": ["top", "left", "width", "height", "src", "id"],
        "rect": ["top", "left", "width", "height", "fill", "rx", "ry", "id"],
        "circle": ["top", "left", "width", "height", "fill", "radius", "id"],
        "path": ["top", "left", "width", "height", "fill", "path", "id"]
    }
    assert layout in layout_template, f"Layout {layout} not found in layout template"
    layout_description = " ".join(layout_template.get(layout, ["centered_hero"]))
    
    input_text = f"I want you to create a beautiful advertisement banner of dimension 1080*1080, following the best practices, in form of condensed FabricJs json(with less keys), for the given product with the following details:\n\n\n##Product Details:\n\n **Product Name:** {product_name}\n **Product Description:** {product_description}\n **Product Price:** {product_price}\n\n **Product Color:** {product_color}\n\n\n.The banner should follow the {layout} layout\n ###Layout Description:\n\n {layout_description}.\n\n\n##Instructions:\n\n 1. Create a banner in condensed fabric js format, which have following important keys for given layer type: \n{json.dumps(important_fields)}.\n2. Focus on placement of layers to give a beautiful banner in given layout, with proper spacing between each layer. Make sure no two text layers overlap each other and entire banner is visible in 1080*1080 canvas. \n  2.1 Use *top*(y coordinate of top-left of the layer), *left*(x coordinate of top-left of the layer), *width*(width of the layer), *height*(height of the layer) keys. \n2.2 the text width and height don't have an effect in fabricjs, so place them correctly using  *top*, *left* and *fontSize* keys."
    
    if fontFamilyList:
        input_text += f"\n 3.You must strictly choose fontFamily for the text layers from the following list: {json.dumps(fontFamilyList)}."
    
    input_text += "\n\n Think step by step and then create the banner."

    with open("input_test_text.txt", "w") as f:
        f.write(input_text)
    
    return input_text

def generate_banner(model, tokenizer, input_text, temperature=0.7, top_p=0.9, top_k=20):
    """Generate FabricJS banner JSON from input text"""
    # Create conversation format
    conversation = [{"role": "user", "content": input_text}]
    
    # Apply chat template
    prompt = tokenizer.apply_chat_template(
        conversation,
        enable_thinking=True,
        add_generation_prompt=True,
        tokenize=False
    )
    
    # Generate response
    with torch.no_grad():
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        outputs = model.generate(
            **inputs,
            max_new_tokens=4096,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
        
        # Decode the response
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract just the generated part (remove the input prompt)
        generated_text = response[len(prompt):].strip()
        
    return generated_text

def extract_json_from_response(response):
    """Extract JSON from the model response"""
    try:
        # Look for JSON within <json> tags
        if "<json>" in response and "</json>" in response:
            start = response.find("<json>") + 6
            end = response.find("</json>")
            json_str = response[start:end].strip()
            return json.loads(json_str)
        else:
            # Try to find JSON in the response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None
    
    return None

def test_model(product_name, product_description, product_price, layout, image_url, model=None, tokenizer=None):
    # Load layout template (from training script)
    layout_file = "../assets/layout.json"
    checkpoint_path = "/home/ubuntu/rishabh/banner_training/model/checkpoint-8"
    
    try:
        with open(layout_file, "r") as f:
            layout_template = json.load(f)
    except FileNotFoundError:
        print("Layout template not found, using default")
        layout_template = {"frame_layout": ["frame layout with decorative elements"]}
    
    
    # Generate color palette description from image
    print("Generating color palette from image...")
    product_color = get_color_pallete(image_url)
    print(f"Generated color palette: {product_color[:100]}...")


    # Generate font family list from image
    print("Generating font family list from image...")
    fontFamilyList = get_font_families(image_url, product_name, product_description)
    print(f"Generated font family list: {fontFamilyList}")
    
    # Load the model - using the latest checkpoint
    print(f"Loading model from {checkpoint_path}...")
    if model is None or tokenizer is None:
        model, tokenizer = load_model(checkpoint_path)
    
    
    # Prepare input
    input_text = prepare_input(product_name, product_description, product_price, layout, layout_template, product_color, fontFamilyList)
    print("Input prepared:")
    print("-" * 50)
    print(input_text[:500] + "..." if len(input_text) > 500 else input_text)
    print("-" * 50)
    
    # Generate banner
    print("Generating banner...")
    generate_time = time.time()
    generated_response = generate_banner(model, tokenizer, input_text)
    print(f"Time taken to generate banner: {time.time() - generate_time} seconds")
    
    print("\nGenerated Response:")
    print("=" * 50)
    print(generated_response)
    print("=" * 50)
    
    # Extract and save JSON
    try:
        generated_json = extract_json_from_response(generated_response)
        width, height = Image.open(requests.get(image_url, stream=True).raw).size
        generated_json = get_original_data(generated_json, [width, height])
    except Exception as e:
        print(f"Error extracting JSON: {e}")
        return generated_response
    
    return generated_json

# if __name__ == "__main__":
#     product_name = "Aldo Legoirii Bag"
#     product_description = "Spacious Stylish Design\nPremium Faux Leather Material\nGold Hardware Accents\nVersatile Everyday Carry"
#     product_price = "$65.00"
#     layout = "centered_hero"
#     image_url = "https://example.com/image.jpg"  # Replace with actual image URL
#     generated_json = test_model(product_name, product_description, product_price, layout, image_url)
#     print(generated_json)

  
