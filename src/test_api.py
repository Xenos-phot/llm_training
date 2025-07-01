#!/usr/bin/env python3
"""
Test script for the Ray Serve Banner Generation API
"""

import requests
import json
import time

def test_health_endpoint(base_url="http://localhost:8000"):
    """Test the health check endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error testing health endpoint: {e}")
        return False

def test_available_layouts(base_url="http://localhost:8000"):
    """Test the available layouts endpoint"""
    print("\nTesting available layouts endpoint...")
    try:
        response = requests.get(f"{base_url}/available_layouts")
        print(f"Available layouts status: {response.status_code}")
        if response.status_code == 200:
            layouts_data = response.json()
            print(f"Available layouts: {layouts_data['layouts']}")
            return layouts_data['layouts']
        else:
            print(f"Error: {response.text}")
            return []
    except Exception as e:
        print(f"Error testing layouts endpoint: {e}")
        return []

def test_banner_generation(base_url="http://localhost:8000"):
    """Test banner generation endpoint"""
    print("\nTesting banner generation endpoint...")
    
    # Sample request data (similar to the test data in src/test.py)
    test_data = {
        "product_name": "Aldo Legoirii Bag",
        "product_description": "Spacious Stylish Design\nPremium Faux Leather Material\nGold Hardware Accents\nVersatile Everyday Carry",
        "product_price": "$65.00",
        "layout": "split_vertical",
        "image_url": "https://s3.us-east-2.wasabisys.com/ai-image-editor-webapp/test-images/65592cc4-1937-406a-9260-9904e6aa840c_nobg_1214x1439.png",
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 20
    }
    
    try:
        print("Sending banner generation request...")
        print(f"Request data: {json.dumps(test_data, indent=2)}")
        
        start_time = time.time()
        response = requests.post(
            f"{base_url}/generate_banner", 
            json=test_data,
            timeout=300  # 5 minute timeout for generation
        )
        request_time = time.time() - start_time
        
        print(f"Response status: {response.status_code}")
        print(f"Total request time: {request_time:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Generation successful: {result['success']}")
            if result['success']:
                print(f"Model generation time: {result.get('generation_time', 'N/A'):.2f} seconds")
                print("Generated banner JSON keys:", list(result['banner_json'].keys()) if result['banner_json'] else 'None')
                
                # Save the generated banner JSON
                if result['banner_json']:
                    print(json.dumps(result['banner_json'], indent=2))
                    print("Generated banner saved to 'generated_banner.json'")
                    
                return True
            else:
                print(f"Generation failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"Request failed: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("Request timed out - this might be normal for the first request as the model loads")
        return False
    except Exception as e:
        print(f"Error testing banner generation: {e}")
        return False


def main():
    """Run all API tests"""
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("Ray Serve Banner Generation API Test Suite")
    print("=" * 60)
    
    # Test 1: Health check
    health_ok = test_health_endpoint(base_url)
    
    # Test 2: Available layouts
    layouts = test_available_layouts(base_url)
    
    # Test 3: Banner generation with image
    if health_ok and layouts:
        banner_test_1 = test_banner_generation(base_url)
        
        
        print("\n" + "=" * 60)
        print("Test Results Summary:")
        print("=" * 60)
        print(f"Health check: {'✓ PASS' if health_ok else '✗ FAIL'}")
        print(f"Available layouts: {'✓ PASS' if layouts else '✗ FAIL'}")
        print(f"Banner generation (with image): {'✓ PASS' if banner_test_1 else '✗ FAIL'}")
        
        if all([health_ok, layouts, banner_test_1]):
            print("\n🎉 All tests passed! The API is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Check the output above for details.")
    else:
        print("\n❌ Basic health checks failed. Make sure Ray Serve is running.")

if __name__ == "__main__":
    main() 