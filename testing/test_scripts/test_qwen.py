import json
from unsloth import FastLanguageModel
import os
import torch
from transformers import TextStreamer
import time
from PIL import Image
import requests
from banner_utils.create_condensed_data import get_original_data

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

def prepare_input(product_name, product_description, product_price, layout, layout_template):
    """Prepare input text for the model based on training format"""
    
    # Handle empty fields as in training
    if product_name == "":
        product_name = "Product Name Not Available"
    if product_description == "":
        product_description = "Product Details Not Available"
    if product_price == "":
        product_price = "Product Price Not Available"
    
    layout_description = " ".join(layout_template.get(layout, ["centered_hero"]))
    
    input_text = f'I want you to create a beautiful advertisement banner, following the best practices in form of condensed fabricjs json for the given product with the following details:\n\n##Product Details:\n\n **Product Name:** {product_name}\n **Product Description:** {product_description}\n **Product Price:** {product_price}\n\n. The banner should follow the {layout} layout\n\n###Layout Description:\n\n {layout_description}.\n\n Think step by step and then create the banner. '
    
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
    layout_file = "layout.json"
    checkpoint_path = "/home/ubuntu/rishabh/llm_training/model/checkpoint-2102"
    try:
        with open(layout_file, "r") as f:
            layout_template = json.load(f)
    except FileNotFoundError:
        print("Layout template not found, using default")
        layout_template = {"frame_layout": ["frame layout with decorative elements"]}
    
    # Load the model - using the latest checkpoint
    print(f"Loading model from {checkpoint_path}...")
    if model is None or tokenizer is None:
        model, tokenizer = load_model(checkpoint_path)
    
    
    # Prepare input
    input_text = prepare_input(product_name, product_description, product_price, layout, layout_template)
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
    generated_json = extract_json_from_response(generated_response)
    if not generated_json:
        return "failed to extract json"
    width, height = Image.open(requests.get(image_url, stream=True).raw).size
    generated_json = get_original_data(generated_json, [width, height])

    return generated_json

# if __name__ == "__main__":
#     product_name = "Aldo Legoirii Bag"
#     product_description = "Spacious Stylish Design\nPremium Faux Leather Material\nGold Hardware Accents\nVersatile Everyday Carry"
#     product_price = "$65.00"
#     layout = "centered_hero"
#     generated_json = test_model(product_name, product_description, product_price, layout)
#     print(generated_json)

  
