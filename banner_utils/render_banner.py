import os
import json
import time
import requests
import subprocess
import copy
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed


def fix_font_size(banner_config):
    text_objects = {}

    os.makedirs('tmp/fonts', exist_ok=True)
    for layers in banner_config['objects']:
        if layers['type'] == 'text' or layers['type'] == 'textbox':
            fontUrl = layers['fontURL']
            save_name = fontUrl.split('/')[-1]
            if os.path.exists(f'tmp/fonts/{save_name}'):
                continue
            response = requests.get(fontUrl)
            print(save_name, response.status_code)
            if response.status_code == 200:
                with open(f'tmp/fonts/{save_name}', 'wb') as f:
                    f.write(response.content)

    for layer in banner_config['objects']:
        if layer['type'] == 'text' or layer['type'] == 'textbox':
            text_objects[layer['id']] = layer

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {text_id: executor.submit(get_font_size, text_objects[text_id]) for text_id in text_objects}
        for text_id, future in futures.items():
            text_object = future.result()
            for idx, layer in enumerate(banner_config['objects']):
                if layer['id'] == text_id:
                    banner_config['objects'][idx] = text_object
                    break
    return banner_config


def get_font_size(text_object):
    text_obj = copy.deepcopy(text_object)
    text_obj["ideal_top"] = text_obj['top']
    text_obj["ideal_left"] = text_obj['left']
    text_obj["ideal_width"] = text_obj['width']
    text_obj["ideal_height"] = text_obj['height']
    input_file = f'/tmp/{uuid4()}.json'
    output_file = f'{input_file[:-5]}_updated.json'
    with open(input_file, 'w') as f:
        json.dump(text_obj, f, indent=4)
    
    os.system(f'/content/llm_training/versions/node/v22.17.0/bin/node node_scripts/get_font_size.js {input_file} {output_file}')
    with open(output_file, 'r') as f:
        result = json.load(f)
    os.remove(input_file)
    os.remove(output_file)
    left = result['left']
    top = result['top']
    width = result['width']
    height = result['height']
    font_size = result['fontSize']

    alignment = text_object['textAlign']

    if alignment == 'center':
        original_center_x = text_object['left'] + text_object['width']/2
        text_object['left'] = original_center_x - width/2
        text_object['top'] = top
        text_object['width'] = width
        text_object['height'] = height
        text_object['fontSize'] = font_size
    elif alignment == 'right':
        text_object['left'] = text_object['left'] - (width - text_object['width'])
        text_object['top'] = top
        text_object['width'] = width
        text_object['height'] = height
        text_object['fontSize'] = font_size
    elif alignment == 'left':
        text_object['left'] = text_object['left']
        text_object['top'] = top
        text_object['width'] = width
        text_object['height'] = height
        text_object['fontSize'] = font_size
    return text_object


def render_banner(banner_config, input_file='input_config.json', output_file='updated_config.json', create_png=False):

    """
    Render a banner using FabricJS configuration and Node.js rendering engine.
    
    This function takes a banner configuration object containing FabricJS JSON data
    and renders it using a Node.js script. It handles font downloading, temporary
    file management, and can optionally create PNG output.
    
    Args:
        banner_config (dict): FabricJS JSON configuration object containing banner layout,
                             objects (text, images, shapes), and styling information.
                             Expected format: {"width": int, "height": int, "objects": [...]}
        
        input_file (str, optional): Temporary file path for the input configuration.
                                   Defaults to 'input_config.json'.
        
        output_file (str, optional): Temporary file path for the output configuration.
                                    Defaults to 'updated_config.json'.
        
        create_png (bool, optional): Whether to generate PNG output in addition to JSON.
                                   Defaults to False. The Image is create at the output_file path.
    
    Returns:
        dict: Updated banner configuration with rendered positioning and styling.
              The returned object maintains the same structure as input but with
              processed coordinates, font sizes, and layout adjustments.
    
    Raises:
        subprocess.CalledProcessError: If the Node.js rendering script fails to execute.
        FileNotFoundError: If required Node.js executable or script files are missing.
        requests.RequestException: If font downloading fails.
    
    Example:
        >>> banner_config = {
        ...     "width": 1200,
        ...     "height": 600,
        ...     "objects": [
        ...         {"type": "text", "text": "Hello World", "left": 100, "top": 100}
        ...     ]
        ... }
        >>> result = render_banner(banner_config, create_png=True)
        >>> print(f"Banner rendered with {len(result['objects'])} objects")
    """
    start_time = time.time()
    os.makedirs('tmp', exist_ok=True)
    os.makedirs('tmp/fonts', exist_ok=True)
    for layers in banner_config['objects']:
        if layers['type'] == 'text' or layers['type'] == 'textbox':
            fontUrl = layers['fontURL']
            save_name = fontUrl.split('/')[-1]
            response = requests.get(fontUrl)
            if response.status_code == 200:
                with open(f'tmp/fonts/{save_name}', 'wb') as f:
                    f.write(response.content)
    with open(input_file, 'w') as f:
        json.dump(banner_config, f, indent=4)
    
    # Use full path to node executable from NVM
    node_path = '/content/llm_training/versions/node/v22.17.0/bin/node'
    script_path = 'node_scripts/render_banner.js'
    if create_png:
        result = subprocess.run([node_path, script_path, input_file, output_file, '--png'], 
                              capture_output=True, text=True, check=True)
    else:
        result = subprocess.run([node_path, script_path, input_file, output_file], 
                              capture_output=True, text=True, check=True)
    
    with open(output_file, 'r') as f:
        updated_config = json.load(f)
    if input_file == 'input_config.json':
        os.remove(input_file)
    os.remove(output_file)
    end_time = time.time()
    return updated_config

    

# if __name__ == "__main__":
#     banner_config = {
#     "backgroundColor": "#ffffff",
#     "height": 1080,
#     "width": 1080,
#     "objects": [
#         {
#             "id": "1",
#             "layerCategory": "background",
#             "type": "svg",
#             "originX": "left",
#             "originY": "top",
#             "left": 0,
#             "top": 0,
#             "width": 1080,
#             "height": 1080,
#             "fill": "rgb(0,0,0)",
#             "strokeWidth": 0,
#             "scaleX": 1,
#             "scaleY": 1,
#             "angle": 0,
#             "opacity": 1,
#             "backgroundColor": "",
#             "src": "<svg width='1080' height='1080' viewBox='0 0 1080 1080' xmlns='http://www.w3.org/2000/svg'><rect width='1080' height='1080' fill='#F5EEE8'/><defs><radialGradient id='circleGradient' cx='540' cy='540' r='320' gradientUnits='userSpaceOnUse'><stop offset='0%' stop-color='#E8D0C0'/><stop offset='100%' stop-color='#D9BBA8'/></radialGradient><linearGradient id='goldGradient' x1='0%' y1='0%' x2='100%' y2='100%'><stop offset='0%' stop-color='#E8C496'/><stop offset='100%' stop-color='#C4A278'/></linearGradient></defs><circle cx='540' cy='540' r='320' fill='url(#circleGradient)' stroke='#E6D5C5' stroke-width='5'/><circle cx='840' cy='380' r='120' fill='url(#goldGradient)' stroke='#D9BBA8' stroke-width='3'/><g opacity='0.2'><circle cx='140' cy='240' r='15' fill='#D9BBA8'/><circle cx='180' cy='280' r='10' fill='#D9BBA8'/><circle cx='160' cy='320' r='12' fill='#D9BBA8'/><circle cx='900' cy='800' r='15' fill='#D9BBA8'/><circle cx='940' cy='840' r='10' fill='#D9BBA8'/><circle cx='920' cy='880' r='12' fill='#D9BBA8'/></g><path d='M180 150 L220 190 M880 900 L920 940' stroke='#E6D5C5' stroke-width='2'/><path d='M850 170 C870 190, 900 160, 920 180 M150 880 C170 900, 200 870, 220 890' stroke='#E6D5C5' stroke-width='2' fill='none'/><rect x='0' y='0' width='1080' height='1080' stroke='#E6D5C5' stroke-width='15' fill='none' opacity='0.3'/></svg>"
#         },
#         {
#             "id": "2",
#             "layerCategory": "heading",
#             "type": "text",
#             "originX": "left",
#             "originY": "top",
#             "left": 202.88,
#             "top": 50,
#             "width": 674.24,
#             "height": 113,
#             "fill": "#8B5A2B",
#             "strokeWidth": 0,
#             "scaleX": 1,
#             "scaleY": 1,
#             "angle": 0,
#             "opacity": 1,
#             "backgroundColor": "",
#             "fontFamily": "Lexend Bold",
#             "fontWeight": "normal",
#             "fontSize": 100,
#             "text": "ELEGANCE",
#             "textAlign": "center",
#             "fontStyle": "normal",
#             "lineHeight": 1,
#             "charSpacing": 0,
#             "fontURL": "https://ai-image-editor-wasabi-bucket.apyhi.com/fonts/font/Bold-cc8776c1-f593-4e2e-a9e2-6499f7b7e514.ttf"
#         },
#         {
#             "id": "3",
#             "layerCategory": "subheading",
#             "type": "text",
#             "originX": "left",
#             "originY": "top",
#             "left": 218.67000000000002,
#             "top": 160,
#             "width": 642.66,
#             "height": 67.8,
#             "fill": "#A67C52",
#             "strokeWidth": 0,
#             "scaleX": 1,
#             "scaleY": 1,
#             "angle": 0,
#             "opacity": 1,
#             "backgroundColor": "",
#             "fontFamily": "Taviraj Regular",
#             "fontWeight": "normal",
#             "fontSize": 60,
#             "text": "ALDO LEGOIRII TOTE",
#             "textAlign": "center",
#             "fontStyle": "normal",
#             "lineHeight": 1,
#             "charSpacing": 0,
#             "fontURL": "https://ai-image-editor-wasabi-bucket.apyhi.com/fonts/font/Regular-70b996a0-2fe8-4b93-b72d-ea43c97e1576.ttf"
#         },
#         {
#             "id": "4",
#             "layerCategory": "image",
#             "type": "image",
#             "originX": "left",
#             "originY": "top",
#             "left": 297.2,
#             "top": 252.2,
#             "width": 1214,
#             "height": 1439,
#             "fill": "rgb(0,0,0)",
#             "strokeWidth": 0,
#             "scaleX": 0.4,
#             "scaleY": 0.4,
#             "angle": 0,
#             "opacity": 1,
#             "backgroundColor": "",
#             "src": "https://s3.us-east-2.wasabisys.com/ai-image-editor-webapp/test-images/cef64dbb-aad8-46f9-9a16-cb16df8fa6bc_nobg_1214x1439.png"
#         },
#         {
#             "id": "5",
#             "layerCategory": "price",
#             "type": "text",
#             "originX": "left",
#             "originY": "top",
#             "left": 742.5,
#             "top": 334.8,
#             "width": 195,
#             "height": 90.4,
#             "fill": "#6B4226",
#             "strokeWidth": 0,
#             "scaleX": 1,
#             "scaleY": 1,
#             "angle": 0,
#             "opacity": 1,
#             "backgroundColor": "",
#             "fontFamily": "Orbitron Bold",
#             "fontWeight": "normal",
#             "fontSize": 80,
#             "text": "$65",
#             "textAlign": "center",
#             "fontStyle": "normal",
#             "lineHeight": 1,
#             "charSpacing": 0,
#             "fontURL": "https://ai-image-editor-wasabi-bucket.apyhi.com/fonts/font/Bold-b27c2d74-4778-4723-82bd-f07e9b837ea3.ttf"
#         },
#         {
#             "id": "6",
#             "layerCategory": "features",
#             "type": "text",
#             "originX": "left",
#             "originY": "top",
#             "left": 122.5,
#             "top": 865,
#             "width": 835,
#             "height": 38.42,
#             "fill": "#6B4226",
#             "strokeWidth": 0,
#             "scaleX": 1,
#             "scaleY": 1,
#             "angle": 0,
#             "opacity": 1,
#             "backgroundColor": "",
#             "fontFamily": "Assistant Regular",
#             "fontWeight": "normal",
#             "fontSize": 34,
#             "text": "\u2022 SPACIOUS DESIGN \u2022 PREMIUM QUALITY \u2022 GOLD HARDWARE",
#             "textAlign": "center",
#             "fontStyle": "normal",
#             "lineHeight": 1,
#             "charSpacing": 0,
#             "fontURL": "https://ai-image-editor-wasabi-bucket.apyhi.com/fonts/font/Regular-aa9a6259-43a0-4ad1-b325-67e400d476dd.ttf"
#         },
#         {
#             "id": "7",
#             "layerCategory": "button",
#             "type": "rect",
#             "originX": "left",
#             "originY": "top",
#             "left": 430.0,
#             "top": 940,
#             "width": 220,
#             "height": 60,
#             "fill": "#C4A278",
#             "strokeWidth": 0,
#             "scaleX": 1,
#             "scaleY": 1,
#             "angle": 0,
#             "opacity": 1,
#             "backgroundColor": "",
#             "rx": 0,
#             "ry": 0
#         },
#         {
#             "id": "8",
#             "layerCategory": "cta",
#             "type": "text",
#             "originX": "left",
#             "originY": "top",
#             "left": 460.0,
#             "top": 956.44,
#             "width": 160,
#             "height": 27.12,
#             "fill": "#FFFFFF",
#             "strokeWidth": 0,
#             "scaleX": 1,
#             "scaleY": 1,
#             "angle": 0,
#             "opacity": 1,
#             "backgroundColor": "",
#             "fontFamily": "League Spartan-Bold",
#             "fontWeight": "normal",
#             "fontSize": 24,
#             "text": "SHOP NOW",
#             "textAlign": "center",
#             "fontStyle": "normal",
#             "lineHeight": 1,
#             "charSpacing": 0,
#             "fontURL": "https://ai-image-editor-wasabi-bucket.apyhi.com/fonts/font/Bold-7ea34b7e-b898-4af9-89a2-b9a469045b96.ttf"
#         }
#     ],
#     "version": "5.3.0"
#     }
#     updated_banner_config = render_banner(banner_config)
#     with open('updated_config.json', 'w') as f:
#         json.dump(updated_banner_config, f, indent=4)