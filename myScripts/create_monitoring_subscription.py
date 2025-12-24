import asyncio
import httpx
from quart import Quart, request
from hypercorn.config import Config
from hypercorn.asyncio import serve

# --- CONFIGURATION ---
NOTIFY_HOST = "172.25.70.53"
NOTIFY_PORT = 4040
NOTIFY_PATH = "/notify"

AMF_SUBSCRIPTION_URL = "http://192.168.70.132:8080/namf-evts/v1/subscriptions"

# 1. Define the Quart App (HTTP/2 Compatible Server)
app = Quart(__name__)

# 2. Define the Notification Payload
payload = {
    "subscription": {
        "eventList": [
            {"type": "LOCATION_REPORT"},
            {"type": "PRESENCE_IN_AOI_REPORT"},
            {"type": "TIMEZONE_REPORT"},
            {"type": "ACCESS_TYPE_REPORT"},
            {"type": "REGISTRATION_STATE_REPORT"},
            {"type": "CONNECTIVITY_STATE_REPORT"},
            {"type": "REACHABILITY_REPORT"},
            {"type": "COMMUNICATION_FAILURE_REPORT"},
            {"type": "UES_IN_AREA_REPORT"},
            {"type": "SUBSCRIPTION_ID_CHANGE"},
            {"type": "SUBSCRIPTION_ID_ADDITION"},
            {"type": "LOSS_OF_CONNECTIVITY"}
        ],
        "eventNotifyUri": f"http://{NOTIFY_HOST}:{NOTIFY_PORT}{NOTIFY_PATH}",
        "notifyCorrelationId": "notif-001",
        "nfId": "123e4567-e89b-12d3-a456-426614174000"
    }
}

# 3. Define the Route to handle AMF Notifications
@app.route(NOTIFY_PATH, methods=['POST'])
async def receive_notification():
    """
    Handles the HTTP/2 POST request from the AMF.
    """
    try:
        # Read the JSON body
        body = await request.get_json()
        
        print(f"\n--- Notification received from AMF ---")
        print(f"Path: {request.path}")
        print(f"Body: {body}")
        
        # 5G SBIs expect 204 No Content for successful notifications
        return "", 204
    except Exception as e:
        print(f"Error processing notification: {e}")
        return "", 500

# 4. Define the Client Task (Send Subscription)
async def send_subscription_request():
    """
    Sends the subscription request to the AMF after a short delay
    to ensure the server is up.
    """
    # Wait a second to ensure Hypercorn is fully listening
    await asyncio.sleep(1) 
    
    print(f"\n--- Sending Subscription Request to {AMF_SUBSCRIPTION_URL} ---")
    
    try:
        # Use AsyncClient for compatibility with the async loop
        async with httpx.AsyncClient(http2=True, http1=False) as client:
            response = await client.post(
                AMF_SUBSCRIPTION_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"Return Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            
    except httpx.RequestError as exc:
        print(f"An error occurred while sending subscription: {exc}")

# 5. Hook to run client logic when server starts
@app.before_serving
async def startup_tasks():
    # Schedule the subscription request to run in the background
    app.add_background_task(send_subscription_request)

# 6. Main Entry Point
if __name__ == "__main__":
    print(f"🚀 Starting HTTP/2 Notification Server on {NOTIFY_HOST}:{NOTIFY_PORT}...")
    
    config = Config()
    config.bind = [f"{NOTIFY_HOST}:{NOTIFY_PORT}"]
    # Log access to console
    config.accesslog = "-" 
    
    # Run the server (Hypercorn handles the HTTP/2 frames automatically)
    asyncio.run(serve(app, config))