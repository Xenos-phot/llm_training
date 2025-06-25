import json
from unsloth import FastLanguageModel
import pandas as pd
from datasets import Dataset
from trl import SFTTrainer, SFTConfig
import os
with open("assets/fonts.json", "r") as f:
    fonts = json.load(f)
    fonts = fonts["english"]

with open("assets/layout.json", "r") as f:
    layout_template = json.load(f)


def json_dataset(data):
    conversations=[]
    for item in data:
        item_input = item['input']
        product_name = item_input.get("product_name", "")
        product_details = item_input.get("product_details", "")
        product_price = item_input.get("product_price", "")
        layout = item_input.get("layout", "centered_hero")
        important_fields = {
            "svg": ["top", "left", "width", "height", "src", "id"],
            "text": ["top", "left", "width", "height", "fill", "text", "fontSize", "fontFamily", "textAlign", "id"],
            "image": ["top", "left", "width", "height", "src", "id"],
            "rect": ["top", "left", "width", "height", "fill", "rx", "ry", "id"],
            "circle": ["top", "left", "width", "height", "fill", "radius", "id"],
            "path": ["top", "left", "width", "height", "fill", "path", "id"]
        }

        if product_name == "":
            product_name = "Product Name Not Available"
        if product_details == "":
            product_details = "Product Details Not Available"
        if product_price == "":
            product_price = "Product Price Not Available"

        layout_description = " ".join(layout_template[layout])

        input_text = f'I want you to create a beautiful advertisement banner, following the best practices in form of condensed fabricjs json for the given product with the following details:\n\n##Product Details:\n\n **Product Name:** {product_name}\n **Product Description:** {product_details}\n **Product Price:** {product_price}\n\n. The banner should follow the {layout} layout\n\ ###Layout Description:\n\n {layout_description}.\n\n Think step by step and then create the banner. '
        reasoning_text = f"Let me think step-by-step, The user wants me to create a banner in condensed fabric js format, which have following important fields for given layer type: \n{important_fields}\n\n I have to ensure that no two text layers overlap, and maintain proportional spacing between each layer to support a natural visual flow for the viewer. So I have to place layers carefully using *top*(y coordinate of top-left of the layer), *left*(x coordinate of top-left of the layer), *width*(width of the layer), *height*(height of the layer) keys. But for the text width and height don't have an effect in fabricjs, so I will place them correctly using  *top*, *left* and *fontSize* keys. The text are readable, with contrasting color to the background. Let me give an overview of the banner: \n\n"+ item['banner_details']+ "\nNow I will create the banner."
        output_text = f'{json.dumps(item["output"])}'
        conversations.append({"input":input_text,
                              "output":f"\n<think>\n{reasoning_text}\n</think>\n FabricJS JSON:\n<json>{output_text}</json>"})
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
    data_path = "training_data"
    training_data = []
    for file in os.listdir(data_path):
        with open(os.path.join(data_path, file), "r") as f:
            training_data.append(json.load(f))
    dataset = data_prep(training_data, tokenizer)
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        eval_dataset=None,
        args=SFTConfig(
            output_dir="model",
            dataset_text_field="text",
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            num_train_epochs=30,
            learning_rate= 2e-4,
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            save_strategy="steps",
            save_steps=100,
            save_total_limit=50,
            report_to="wandb",
            resume_from_checkpoint="/home/ubuntu/rishabh/llm_training/model/checkpoint-2104",
    ))

    # Start training
    trainer.train()

if __name__ == "__main__":
    main()