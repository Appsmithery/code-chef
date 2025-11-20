#!/usr/bin/env python3
import httpx

API_KEY = 'sk-do-GtfPvjcgL04ICXm-UXFYJ5eyqaeKAq4BPMIxjQjYAkNmGQ3C5JNis2it75'
response = httpx.post(
    'https://inference.do-ai.run/v1/embeddings',
    headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    },
    json={
        'model': 'text-embedding-ada-002',
        'input': ['test']
    },
    timeout=30
)
print(f'Status: {response.status_code}')
if response.status_code == 200:
    data = response.json()
    print(f'Embeddings: {len(data.get("data", []))} returned')
    print(f'Vector size: {len(data["data"][0]["embedding"])}')
else:
    print(f'Error: {response.text}')
