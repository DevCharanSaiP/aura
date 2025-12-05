import requests

url = "http://127.0.0.1:8000/orchestrate/anomaly"

payload = {
    "vehicle_id": "V001",
    "anomaly_score": 0.87,
    "subsystems": {"brakes": 0.92}
}

resp = requests.post(url, json=payload)
print("POST status:", resp.status_code, resp.text)

resp2 = requests.get("http://127.0.0.1:8000/health/V001")
print("GET status:", resp2.status_code, resp2.text)