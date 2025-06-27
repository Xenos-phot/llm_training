import json
import base64
from pathlib import Path

class BannerExampleLoader:
    def __init__(self):
        self.sample_dir = Path('sample-banners')

    def _load_generic_examples(self):
        """Load generic banner examples from the generic directory"""
        examples = []
        generic_dir = self.sample_dir / 'generic'
        
        for banner_dir in sorted(generic_dir.glob('banner*')):
            if banner_dir.is_dir():
                config_file = banner_dir / 'config.json'
                image_file = banner_dir / 'rendered.png'
                
                if config_file.exists() and image_file.exists():
                    try:
                        with open(config_file, 'r') as f:
                            print(f"Reading generic config file: {config_file}")
                            config = json.load(f)
                    except json.JSONDecodeError as e:
                        print(f"Error in config file {config_file}: {str(e)}")
                        continue
                    
                    with open(image_file, 'rb') as f:
                        image_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    examples.append({
                        'config': config,
                        'image': image_data,
                        'name': banner_dir.name,
                        'type': 'generic'
                    })
                    
        return examples

    def _load_layout_examples(self, layout_id):
        """Load layout-specific banner examples for the given layout_id"""
        examples = []
        if not layout_id:
            return examples
            
        print(f"\nDEBUG: Loading layout-specific examples for layout: {layout_id}")
        layout_dir = self.sample_dir / 'layouts' / layout_id
        
        if layout_dir.exists():
            print(f"Layout directory exists: {layout_dir}")
            for banner_dir in sorted(layout_dir.glob('banner*')):
                if banner_dir.is_dir():
                    config_file = banner_dir / 'config.json'
                    image_file = banner_dir / 'rendered.png'
                    
                    if config_file.exists() and image_file.exists():
                        try:
                            with open(config_file, 'r') as f:
                                print(f"Reading layout config file: {config_file}")
                                config = json.load(f)
                        except json.JSONDecodeError as e:
                            print(f"Error in layout config file {config_file}: {str(e)}")
                            continue
                            
                        with open(image_file, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                        
                        examples.append({
                            'config': config,
                            'image': image_data,
                            'name': banner_dir.name,
                            'type': 'layout_specific'
                        })
        else:
            print(f"Layout directory not found: {layout_dir}")
            
        return examples

    def _load_dimension_examples(self, dimension_id:str):
        """Load dimension-specific banner examples for the given dimension_id"""
        examples = []
        if not dimension_id:
            return examples
            
        print(f"\nDEBUG: Loading dimension-specific examples for dimension: {dimension_id}")
        dimension_dir = self.sample_dir / 'dimensions' / dimension_id
        
        if dimension_dir.exists():
            print(f"Dimension directory exists: {dimension_dir}")
            for banner_dir in sorted(dimension_dir.glob('banner*')):
                if banner_dir.is_dir():
                    config_file = banner_dir / 'config.json'
                    image_file = banner_dir / 'rendered.png'
                    
                    if config_file.exists() and image_file.exists():
                        try:
                            with open(config_file, 'r') as f:
                                print(f"Reading dimension config file: {config_file}")
                                config = json.load(f)
                        except json.JSONDecodeError as e:
                            print(f"Error in dimension config file {config_file}: {str(e)}")
                            continue
                            
                        with open(image_file, 'rb') as f:
                            image_data = base64.b64encode(f.read()).decode('utf-8')
                        
                        examples.append({
                            'config': config,
                            'image': image_data,
                            'name': banner_dir.name,
                            'type': 'dimension_specific'
                        })
        else:
            print(f"Dimension directory not found: {dimension_dir}")
            
        return examples

    def load_banner_examples(self, layout_id=None, dimension_id=None, load_generic=True):
        """
        Load and combine both generic and layout-specific banner examples.
        If layout_id is provided, includes layout-specific examples.
        """
        try:
            print(f"\nDEBUG: Loading examples for layout_id: {layout_id}")
            print(f"\nDEBUG: Loading examples for dimension_id: {dimension_id}")

            # Load both types of examples
            generic_examples = self._load_generic_examples() if load_generic else []
            layout_examples = self._load_layout_examples(layout_id)
            dimension_examples = self._load_dimension_examples(dimension_id)
            
            # Combine examples
            examples = generic_examples + layout_examples + dimension_examples
            
            print(f"Loaded {len(examples)} banner examples ({len(generic_examples)} generic, {len(layout_examples)} layout-specific, {len(dimension_examples)} dimension-specific)")
            return examples
            
        except Exception as e:
            print(f"Error loading banner examples: {str(e)}")
            raise