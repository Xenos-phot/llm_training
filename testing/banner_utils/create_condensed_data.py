import os
import json
from tqdm import tqdm
import traceback
import sys
import time
from PIL import Image
import requests
from io import BytesIO
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from banner_utils.add_color_pallete import get_color_pallete
important_fields = {
    "svg": ["type", "top", "left", "width", "height", "src", "id"],
    "text": ["type", "top", "left", "width", "height", "fill", "text", "fontSize", "fontFamily", "textAlign", "id"],
    "image": ["type", "top", "left", "width", "height", "src", "id"],
    "rect": ["type", "top", "left", "width", "height", "fill", "rx", "ry", "id"],
    "circle": ["type", "top", "left", "width", "height", "fill", "radius", "id"],
    "path": ["type", "top", "left", "width", "height", "fill", "path", "id"]
}

general_text_layer = {
                "type": "text",
                "originX": "left",
                "originY": "top",
                "left": 122,
                "top": 83,
                "width": 837.84,
                "height": 113,
                "fill": "#8B5A2B",
                "strokeWidth": 0,
                "scaleX": 1,
                "scaleY": 1,
                "angle": 0,
                "opacity": 1,
                "backgroundColor": "",
                "fontFamily": "Ultra-Regular",
                "fontWeight": "normal",
                "fontSize": 100,
                "text": "LUXURY TOTE",
                "textAlign": "left",
                "fontStyle": "normal",
                "lineHeight": 1,
                "charSpacing": 0,
                "fontURL": "https://ai-image-editor-wasabi-bucket.apyhi.com/fonts/font/Regular-2470cb70-cda8-4dae-a26f-428d9f6749bc.ttf",
                "id": "heading"
            }

general_svg_layer ={
                "type": "svg",
                "originX": "left",
                "originY": "top",
                "left": 0,
                "top": 0,
                "width": 1080,
                "height": 1080,
                "fill": "rgb(0,0,0)",
                "strokeWidth": 0,
                "scaleX": 1,
                "scaleY": 1,
                "angle": 0,
                "opacity": 1,
                "backgroundColor": "",
                "src": "<svg xmlns='http://www.w3.org/2000/svg' width='1080' height='1080' viewBox='0 0 1080 1080'><defs><linearGradient id='bgGrad' x1='0%' y1='0%' x2='100%' y2='100%'><stop offset='0%' style='stop-color:#1A1A1A'/><stop offset='50%' style='stop-color:#222222'/><stop offset='100%' style='stop-color:#2A2A2A'/></linearGradient><linearGradient id='accentGrad' x1='0%' y1='0%' x2='100%' y2='100%'><stop offset='0%' style='stop-color:#0078D7'/><stop offset='100%' style='stop-color:#00A2FF'/></linearGradient></defs><rect width='1080' height='1080' fill='url(#bgGrad)'/><path d='M1080 0 L1080 1080 L0 1080 Z' fill='#303030'/><path d='M1080 0 L0 1080 L0 800 L800 0 Z' fill='url(#accentGrad)' opacity='0.1'/><g opacity='0.15'><circle cx='200' cy='200' r='5' fill='#FFFFFF'/><circle cx='240' cy='200' r='5' fill='#FFFFFF'/><circle cx='280' cy='200' r='5' fill='#FFFFFF'/><circle cx='200' cy='240' r='5' fill='#FFFFFF'/><circle cx='240' cy='240' r='5' fill='#FFFFFF'/><circle cx='280' cy='240' r='5' fill='#FFFFFF'/><circle cx='200' cy='280' r='5' fill='#FFFFFF'/><circle cx='240' cy='280' r='5' fill='#FFFFFF'/><circle cx='280' cy='280' r='5' fill='#FFFFFF'/></g><g opacity='0.1'><rect x='900' y='100' width='100' height='2' fill='#00A2FF'/><rect x='850' y='150' width='150' height='2' fill='#00A2FF'/><rect x='800' y='200' width='200' height='2' fill='#00A2FF'/><rect x='750' y='250' width='250' height='2' fill='#00A2FF'/><rect x='700' y='300' width='300' height='2' fill='#00A2FF'/><rect x='650' y='350' width='350' height='2' fill='#00A2FF'/><rect x='600' y='400' width='400' height='2' fill='#00A2FF'/><rect x='550' y='450' width='450' height='2' fill='#00A2FF'/><rect x='500' y='500' width='500' height='2' fill='#00A2FF'/><rect x='450' y='550' width='550' height='2' fill='#00A2FF'/><rect x='400' y='600' width='600' height='2' fill='#00A2FF'/><rect x='350' y='650' width='650' height='2' fill='#00A2FF'/><rect x='300' y='700' width='700' height='2' fill='#00A2FF'/><rect x='250' y='750' width='750' height='2' fill='#00A2FF'/><rect x='200' y='800' width='800' height='2' fill='#00A2FF'/><rect x='150' y='850' width='850' height='2' fill='#00A2FF'/><rect x='100' y='900' width='900' height='2' fill='#00A2FF'/><rect x='50' y='950' width='950' height='2' fill='#00A2FF'/><rect x='0' y='1000' width='1000' height='2' fill='#00A2FF'/></g><path d='M1080 0 L0 1080' stroke='#00A2FF' stroke-width='4' opacity='0.5'/><circle cx='540' cy='540' r='400' fill='none' stroke='#00A2FF' stroke-width='1' opacity='0.2'/><circle cx='540' cy='540' r='300' fill='none' stroke='#00A2FF' stroke-width='1' opacity='0.2'/><circle cx='540' cy='540' r='200' fill='none' stroke='#00A2FF' stroke-width='1' opacity='0.2'/></svg>",
                "id": "background"
            }

general_rect_layer = {
                "type": "rect",
                "originX": "left",
                "originY": "top",
                "left": 94,
                "top": 946,
                "width": 200,
                "height": 60,
                "fill": "#C49A6C",
                "strokeWidth": 0,
                "scaleX": 1,
                "scaleY": 1,
                "angle": 0,
                "opacity": 1,
                "backgroundColor": "",
                "rx": 5,
                "ry": 5,
                "id": "cta_button"
            }


general_image_layer = {
                "type": "image",
                "originX": "left",
                "originY": "top",
                "left": 500,
                "top": 348,
                "width": 1214,
                "height": 1439,
                "fill": "rgb(0,0,0)",
                "strokeWidth": 0,
                "scaleX": 0.45,
                "scaleY": 0.45,
                "angle": 0,
                "opacity": 1,
                "backgroundColor": "",
                "src": "https://s3.us-east-2.wasabisys.com/ai-image-editor-webapp/test-images/65592cc4-1937-406a-9260-9904e6aa840c_nobg_1214x1439.png",
                "id": "product_image"
            }

general_path_layer = {
                "type": "path",
                "originX": "left",
                "originY": "top",
                "left": 350,
                "top": 350,
                "width": 90,
                "height": 90,
                "fill": "#B4567E",
                "strokeWidth": 1,
                "scaleX": 1,
                "scaleY": 1,
                "angle": 0,
                "opacity": 1,
                "backgroundColor": "",
                "path": [
                    [
                        "M",
                        50,
                        5
                    ],
                    [
                        "C",
                        60,
                        20,
                        80,
                        20,
                        95,
                        50
                    ],
                    [
                        "C",
                        80,
                        80,
                        60,
                        80,
                        50,
                        95
                    ],
                    [
                        "C",
                        40,
                        80,
                        20,
                        80,
                        5,
                        50
                    ],
                    [
                        "C",
                        20,
                        20,
                        40,
                        20,
                        50,
                        5
                    ],
                    [
                        "Z"
                    ]
                ],
                "id": "decorative_1"
            }

general_circle_layer = {
                "type": "circle",
                "originX": "left",
                "originY": "top",
                "left": 760.0,
                "top": 320.0,
                "width": 180,
                "height": 180,
                "fill": "#FFD100",
                "strokeWidth": 0,
                "scaleX": 1,
                "scaleY": 1,
                "angle": 0,
                "opacity": 1,
                "backgroundColor": "",
                "radius": 90,
                "id": "price_background"
            }
GENERAL_LAYERS = {
    "svg": general_svg_layer,
    "text": general_text_layer,
    "image": general_image_layer,
    "rect": general_rect_layer,
    "circle": general_circle_layer,
    "path": general_path_layer
}
def create_condensed_data(file_path, output_folder="condensed_data"):
    with open(file_path, "r") as f:
        data = json.load(f)
    condensed_data = data["output"].copy()
    condensed_data["objects"] = []
    product_url = None
    for idx, layer in enumerate(data["output"]['objects']):
        if layer["type"] in important_fields:
            if layer["type"] == "image":
                product_url = layer["src"]
            new_layer = {}
            fields = important_fields[layer["type"]]
            for field in fields:
                if field == 'width' and layer["type"] == "image":
                    new_layer[field] = layer["width"] * layer["scaleX"]
                elif field == 'height' and layer["type"] == "image":
                    new_layer[field] = layer["height"] * layer["scaleY"]

                new_layer[field] = layer.get(field, 0)
            condensed_data["objects"].append(new_layer)
        else:
            print(f"File {file_path} has a layer that is not in the important_fields {layer['type']}")
            condensed_data["objects"].append(layer)
    data["output"] = condensed_data
    data['product_color']= get_color_pallete(product_url)
    with open(os.path.join(output_folder, file_path.split("/")[-1]), "w") as f:
        json.dump(data, f)

def get_original_data(condensed_json, image_url, fonts=json.load(open("../assets/fonts.json", "r"))["english"]):
    response = requests.get(image_url)
    product_image_shape = Image.open(BytesIO(response.content)).size
    original_data = condensed_json.copy()
    for idx, layer in enumerate(condensed_json['objects']):
        if layer["type"] in GENERAL_LAYERS:
            for field in GENERAL_LAYERS[layer["type"]]:
                if field not in layer:
                    layer[field] = GENERAL_LAYERS[layer["type"]][field]
            if layer["type"] == "image":
                
                scaleX = layer["width"] / product_image_shape[0]
                scaleY = layer["height"] / product_image_shape[1]
                scale = min(scaleX, scaleY)
                new_width = product_image_shape[0] * scale
                new_height = product_image_shape[1] * scale
                layer["scaleX"] = scale
                layer["scaleY"] = scale
                original_center_x = layer["left"] + layer["width"] / 2
                original_center_y = layer["top"] + layer["height"] / 2
                layer["left"] = original_center_x - new_width / 2
                layer["top"] = original_center_y - new_height / 2
                layer["width"] = product_image_shape[0]
                layer["height"] = product_image_shape[1]
                layer["src"] = image_url
            if layer["type"] == "text" or layer["type"] == "textbox":
                if layer["fontFamily"] in fonts:
                    layer["fontURL"] = fonts[layer["fontFamily"]]
          
            original_data['objects'][idx] = layer
        else:
            print(f"Unknown layer type: {layer['type']}")
    return original_data


if __name__ == "__main__":
    with open("assets/fonts.json", "r") as f:
        fonts = json.load(f)["english"]

    output_folder = "final_data"
    os.makedirs(output_folder, exist_ok=True)
    
    for file in tqdm(sorted(os.listdir("training_data"), key=lambda x: int(x.split(".")[0]))):
        try:
            create_condensed_data(os.path.join("training_data", file), output_folder)
            time.sleep(2)
        except Exception as e:
            print(f"Error creating condensed data for {file}: {e}")
            traceback.print_exc()
            continue