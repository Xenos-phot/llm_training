import json
from unsloth import FastLanguageModel
import pandas as pd
from datasets import Dataset
from trl import SFTTrainer, SFTConfig
import os
import numpy as np


with open("assets/layout.json", "r") as f:
    layout_template = json.load(f)


def json_dataset(data):
    conversations=[]
    for item in data:
        item_input = item['input']
        item_output = item['output']
        product_details = item_input.get("product_details", "")
        product_name = product_details.get("name", "")
        product_price = product_details.get("price", "")
        product_color = item.get("product_color", "")
        product_description = product_details.get("description", "")
        layout = item_input.get("layout", "centered_hero")
        fontFamilyList = []
        for layers in item_output["objects"]:
            layer_font_family = layers.get("fontFamily", "")
            if layer_font_family not in fontFamilyList:
                fontFamilyList.append(layer_font_family)

        output_format = """
        <think>
        ...
        </think>
        Here is your condensed FabricJS JSON:
        <json>
        {
        "backgroundColor": "#ffffff",
        "height": 1080,
        "width": 1080,
        "objects": [
            {
                "type": "svg",
                "top": 0,
                "left": 0,
                "width": 1080,
                "height": 1080,
                "src": ...
                "id": "background",
            },
            {
            ...
            },
            ...
        ],
        "version": "5.3.0"
        }
        </json>
        """
        important_fields = {
            "svg": ["top", "left", "width", "height", "src", "id"],
            "text": ["top", "left", "width", "height", "fill", "text",  "fontFamily", "textAlign", "id"],
            "image": ["top", "left", "width", "height", "src", "id"],
            "rect": ["top", "left", "width", "height", "fill", "rx", "ry", "id"],
            "circle": ["top", "left", "width", "height", "fill", "radius", "id"],
            "path": ["top", "left", "width", "height", "fill", "path", "id"]
        }

        if product_name == "":
            product_name = "Product Name Not Available"
        if product_description == "":
            product_description = "Product Description Not Available"
        if product_price == "":
            product_price = "Product Price Not Available"

        layout_description = " ".join(layout_template[layout])

        input_text = f"I want you to create a beautiful advertisement banner of dimension 1080*1080, following the best practices, in form of condensed FabricJs json(with less keys), for the given product with the following details:\n\n\n##Product Details:\n\n **Product Name:** {product_name}\n **Product Description:** {product_description}\n **Product Price:** {product_price}\n\n **Product Color:** {product_color}\n\n\n.The banner should follow the {layout} layout\n ###Layout Description:\n\n {layout_description}.\n\n\n##Instructions:\n\n 1. Create a banner in condensed fabric js format, which have following important keys for given layer type: \n{json.dumps(important_fields)}.\n2. Focus on placement of layers to give a beautiful banner in given layout, with proper spacing between each layer.  \n    2.1 Carefully use *top*(y coordinate of top-left of the layer), *left*(x coordinate of top-left of the layer), *width*(width of the layer), *height*(height of the layer) keys to adjust placement. \n    2.2 Make sure no two text layers overlap each other and entire banner is visible in 1080*1080 canvas.  \n 3.You must strictly choose fontFamily for the text layers from the following list: {json.dumps(fontFamilyList)}.\n\n\n Have following output format:\n{output_format}\n\n .Think step by step and then create the banner."
        
        
        reasoning_text = f"Let me think step-by-step for creating a 1080*1080 banner for the product: {product_name}. I have to make sure that no two text layers overlap, and maintain proportional spacing between each layer to support a natural visual flow for the viewer, following the layout, {layout}. The text must be readable, with contrasting color to the background, with suitable svg for the background. Let me give an overview of the banner: \n\n"+ item['banner_details']+ "\nNow I will create the banner."
        
        
        output_text = f'{json.dumps(item["output"])}'

        with open("input_text.txt", "w") as f:
            f.write(input_text)
            f.write("\n\n---------------------------------\n\n")
            f.write(reasoning_text)
            f.write("\n\n---------------------------------\n\n")
            f.write(output_text)
            f.write("\n\n---------------------------------\n\n")



        conversations.append({"input":input_text,
                              "output":f"\n<think>\n{reasoning_text}\n</think>\n Here is your condensed FabricJS JSON:\n<json>{output_text}</json>"})
        


    df = Dataset.from_pandas(pd.DataFrame(conversations))
    return df
def generate_conversation(df_data):
    problems  = df_data["input"]
    solutions = df_data["output"]
    conversations = []
    for problem, solution in zip(problems, solutions):
        conversations.append([
            {"role" : "user",      "content" : problem},
            {"role" : "assistant", "content" : solution},
        ])
    return { "conversations": conversations }

def data_prep(data, tokenizer):
    df_data=json_dataset(data)
    
    template_conversations = tokenizer.apply_chat_template(
    df_data.map(generate_conversation, batched = True)["conversations"],
    tokenize = False)
    
    # Count tokens for each sample
    token_counts = []
    for text in template_conversations:
        tokens = tokenizer.encode(text)
        token_count = len(tokens)
        token_counts.append(token_count)
    
    # Print token statistics
    print(f"\n=== Token Count Statistics ===")
    print(f"Total samples: {len(token_counts)}")
    print(f"Min tokens: {min(token_counts)}")
    print(f"Max tokens: {max(token_counts)}")
    print(f"Mean tokens: {np.mean(token_counts):.2f}")
    print(f"Median tokens: {np.median(token_counts):.2f}")
    print(f"95th percentile: {np.percentile(token_counts, 95):.2f}")
    print(f"Samples > 8192 tokens: {sum(1 for count in token_counts if count > 8192)}")
    print("===============================\n")
    
    data = pd.Series(template_conversations, name="text")
    combined_dataset = Dataset.from_pandas(pd.DataFrame(data))
    combined_dataset = combined_dataset.shuffle(seed=42)
    return combined_dataset

def load_model():
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen3-14B",
        max_seq_length=8192,
        load_in_4bit=True,
        load_in_8bit=False,
        full_finetuning=False,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=32,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing= "unsloth",
        random_state=3407,
        use_rslora=False,
        loftq_config=None,
    )
    return model, tokenizer

def main():
    # Load data from environment
    model, tokenizer = load_model()
    data_path = "final_data"     
    training_data = [] 
    eval_data=[]
    layouts = {"centered_hero": 0, "minimalist_center": 0, "circular_focus": 0, "split_vertical": 0, "grid_four": 0, "z_pattern": 0, "frame_layout": 0, "diagonal_split": 0}
    for file in os.listdir(data_path):
        with open(os.path.join(data_path, file), "r") as f:
            json_data = json.load(f)
            layout = json_data["input"]["layout"]
            assert layout in layouts, f"Layout {layout} not found in layouts"
            layouts[layout] += 1
            if layouts[layout] <  5:
                eval_data.append(json_data)
            else:
                training_data.append(json_data)

    dataset = data_prep(training_data, tokenizer)
    eval_dataset = data_prep(eval_data, tokenizer)
    print("Training data size: ", len(dataset))
    print("Eval data size: ", len(eval_dataset))
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        eval_dataset=eval_dataset,
        args=SFTConfig(
            output_dir="model",
            dataset_text_field="text",
            per_device_train_batch_size=2,#batch size per device
            gradient_accumulation_steps=4,#gradient accumulation steps
            warmup_steps=5,#warmup steps
            num_train_epochs=30,#number of epochs
            learning_rate= 2e-4,#learning rate
            logging_steps=1,#log every 1 step
            optim="adamw_8bit",#adamw optimizer with 8-bit quantization
            weight_decay=0.01,#weight decay for regularization
            lr_scheduler_type="linear",#linear learning rate scheduler
            save_strategy="steps", 
            save_steps=50,#save every 100 steps
            save_total_limit=100,#save only last 100 checkpoints
            eval_strategy="steps",  # Enable evaluation during training
            eval_steps=50,          # Evaluate every 50 steps,
            report_to="wandb",
    ))

    # Start training
    trainer.train()

if __name__ == "__main__":
    main()