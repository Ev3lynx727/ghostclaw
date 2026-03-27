import logging
import requests

logging.basicConfig(level=logging.INFO)

def main():
    logging.info("Starting automated logfire instrumentation test")
    
    # Send a mock request so opentelemetry-instrumentation-requests can intercept it
    response = requests.get("https://httpbin.org/get")
    
    logging.info(f"Received proxy response: {response.status_code}")

if __name__ == "__main__":
    main()
