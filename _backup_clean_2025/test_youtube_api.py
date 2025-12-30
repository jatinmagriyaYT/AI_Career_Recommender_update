import requests
import os
import sys
import django

# Setup Django if needed for settings access
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Career_Recommender.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings

def test_key():
    api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    print(f"Testing API Key: {api_key}")
    
    if not api_key:
        print("No API Key found.")
        return

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'q': 'Python tutorial',
        'type': 'video',
        'maxResults': 1,
        'key': api_key
    }
    
    try:
        print("Sending request...")
        response = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS: API Key is valid.")
            data = response.json()
            print(f"Items found: {len(data.get('items', []))}")
        else:
            print("FAILED: API Key is invalid or quota exceeded.")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_key()
