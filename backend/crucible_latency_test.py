import time
import requests
import json

API_URL = "http://127.0.0.1:8000/v1/voice/execute"

print("🔥 Firing the Crucible Latency Test (v3 - Multipart Auth)...")

# 1. The ID Payload
data_payload = {
    "user_id": "rosh_test_profile_001"
}

# 2. The Mock Audio File
# We send a tiny stream of dummy bytes pretending to be a .wav file 
# to bypass the FastAPI file validator.
files_payload = {
    "file": ("real_test.wav", open("real_test.wav", "rb"), "audio/wav")
}

start_time = time.time()

# Send as a multipart form data request instead of raw JSON
response = requests.post(API_URL, data=data_payload, files=files_payload)

latency = time.time() - start_time

print(f"📡 Status Code: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print("✅ SUCCESS! The Sovereign Engine Processed It.")
    print(f"⏱️ True Latency: {latency:.2f} seconds")
    print("-" * 40)
    print("\n=== SYSTEM PAYLOAD ===")
    print(json.dumps(result, indent=2))
    print("======================\n")
    print("🧠 Agent Reasoning Trace:")
    print(json.dumps(result.get("reasoning_explanation", "No trace found"), indent=2))
    print("-" * 40)
else:
    print("❌ REQUEST REJECTED OR FAILED")
    print("Error Details:")
    try:
        data = response.json()
        print("\n=== SYSTEM PAYLOAD ===")
        print(json.dumps(data, indent=2))
        print("======================\n")
    except:
        print(response.text)

