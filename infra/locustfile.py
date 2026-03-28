import os
import requests
from locust import HttpUser, task, between, events

# ── TM2 ingest endpoint ──────────────────────────────────────────
# Set INGEST_URL env var to your TM2's ngrok URL, e.g.:
#   export INGEST_URL=https://abc123.ngrok-free.app/ingest
# Falls back to localhost for local testing only.
INGEST_URL = os.environ.get("INGEST_URL", "http://host.docker.internal:5000/ingest")

@events.request.add_listener
def send_to_remote_db(request_type, name, response_time, response_length,
                      exception, context, **kwargs):
    payload = {
        "method": request_type,
        "endpoint": name,
        "response_time": response_time,
        "success": exception is None,
    }
    try:
        requests.post(INGEST_URL, json=payload, timeout=2)
    except Exception:
        pass


class BoutiqueUser(HttpUser):
    # host is passed via --host flag in docker-compose, no need to hardcode
    wait_time = between(1, 3)

    @task(3)
    def browse_products(self):
        self.client.get("/")
        self.client.get("/product/OLJCESPC7Z")

    @task(2)
    def browse_another_product(self):
        self.client.get("/product/66VCHSJNUP")

    @task(1)
    def add_to_cart(self):
        self.client.post("/setCurrency", data={"currency_code": "USD"})
        self.client.post("/cart", data={
            "item_id": "OLJCESPC7Z",
            "quantity": 1,
        })

    @task(1)
    def view_cart(self):
        self.client.get("/cart")