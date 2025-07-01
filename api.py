import json
import os
import sys
import time
from typing import Dict, Any, Optional, Union
from src.test import load_model
import ray
from ray import serve
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from logging.handlers import RotatingFileHandler
import logging
import uuid
# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import functions from existing test script
from src.test import test_model

# FastAPI app
app = FastAPI(title="Banner Generation API", version="1.0.0")

# Set up logging
if not os.path.exists('logs'):
    os.mkdir('logs')





class BannerRequest(BaseModel):
    product_name: str
    product_description: str
    product_price: str
    layout: str
    image_url: str
    order_id: Optional[str] = 'rishabh_'+str(uuid.uuid4())
    product_color: Optional[str] = None
    font_family_list: Optional[list] = None
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 20

class BannerResponse(BaseModel):
    success: bool
    banner_json: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    generation_time: Optional[float] = None

@serve.deployment(
    num_replicas=1,
    ray_actor_options={"num_gpus": 1, "num_cpus": 3}
)
@serve.ingress(app)
class BannerGenerationService:
    def __init__(self):
        """Initialize the service"""
        # Set up logger for this deployment
        logger = logging.getLogger("api_logger")
        logger.setLevel(logging.INFO)

        # Create file handler
        log_handler = RotatingFileHandler('logs/app.log', maxBytes=10 * 1024 * 1024, backupCount=5)
        log_handler.setLevel(logging.INFO)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        # Add handler to logger
        logger.addHandler(log_handler)

        # Also add console handler for better debugging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)

        self.logger = logger
        self.logger.info("Banner generation service initialized!")
        self.model, self.tokenizer = load_model("model/")
        # Load layout template for validation
        self.layout_template = self._load_layout_template()

    def _load_layout_template(self):
        """Load layout template from file"""
        try:
            with open("assets/layout.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning("Layout template not found, using default")
            return {"frame_layout": ["frame layout with decorative elements"]}
    
    @app.get("/health")
    def health_check(self):
        """Health check endpoint"""
        return {"status": "healthy", "message": "Banner generation service is running"}
    
    @app.post("/generate_banner", response_model=BannerResponse)
    def generate_banner(self, request: BannerRequest) -> BannerResponse:
        """Generate a banner from product details using test_model function"""
        try:
            order_id = request.order_id
            self.logger.info(f"Running for Order ID: {order_id}..........................")
            start_time = time.time()
            
            # Use test_model function directly - it handles everything internally
            generated_json = test_model(
                product_name=request.product_name,
                product_description=request.product_description,
                product_price=request.product_price,
                layout=request.layout,
                image_url=request.image_url,
                model=self.model,  # Let test_model load the model
                tokenizer=self.tokenizer,  # Let test_model load the tokenizer
                product_color=request.product_color,
                fontFamilyList=request.font_family_list,
                logger=self.logger
            )
            
            generation_time = time.time() - start_time
            self.logger.info(f"Generation time for Order ID: {order_id} is {generation_time} seconds")
            
            if generated_json:
                return BannerResponse(
                    success=True,
                    banner_json=generated_json,
                    generation_time=generation_time
                )
            else:
                return BannerResponse(
                    success=False,
                    error="Failed to generate valid banner JSON",
                    generation_time=generation_time
                )
                
        except Exception as e:
            self.logger.error(f"Error generating banner: {e}")
            return BannerResponse(
                success=False,
                error=str(e)
            )
    
    @app.get("/available_layouts")
    def get_available_layouts(self):
        """Get list of available layouts"""
        return {
            "layouts": list(self.layout_template.keys()),
            "layout_descriptions": self.layout_template
        }

# Deployment
deployment = BannerGenerationService.bind()
