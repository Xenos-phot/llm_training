import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from spreadsheet.update_fabric_json import UpdateFabricJson

from tqdm import tqdm
import torch




# Sheet number: model_checkpoint_path
checkpoints_to_test = {
    "4": "/root/llm_training/model/checkpoint-1400",
    "5": "/root/llm_training/model/checkpoint-1500",
    "6": "/root/llm_training/model/checkpoint-1600",
}


for sheet_number, checkpoint_path in tqdm(checkpoints_to_test.items()):
    u = UpdateFabricJson(sheet_number=int(sheet_number), checkpoint_path=checkpoint_path)
    success = u.process_all_products(3.0)
    
    if success:
        print("Successfully updated Google Sheets with FabricJS JSON!")
    else:
        print("Failed to update Google Sheets. Please check the error messages above.")

    del u
    torch.cuda.empty_cache()

