import urllib.request
import os

url = "https://vjs.zencdn.net/v/oceans.mp4"
dest = r"c:\Users\ykane\Desktop\GAINDE2000\frontend\public\assets\port1.mp4"

print(f"Downloading video from {url} to {dest}...")
try:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    with urllib.request.urlopen(req) as response, open(dest, 'wb') as out_file:
        data = response.read()
        out_file.write(data)
    print("Download completed successfully!")
except Exception as e:
    print(f"Error downloading video: {e}")
