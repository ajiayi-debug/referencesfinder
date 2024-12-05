import socket
import asyncio
import logging

# Define an asyncio.Event to track internet connectivity
internet_event = asyncio.Event()

# Initially, assume internet is connected
internet_event.set()

def is_network_available():
    try:
        # Attempt to connect to Google's public DNS server
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

async def monitor_internet_connection():
    global internet_event
    while True:
        if is_network_available():
            if not internet_event.is_set():
                logging.info("Internet connection restored.")
                internet_event.set()
        else:
            if internet_event.is_set():
                logging.warning("Internet connection lost. Stopping all processes...")
                internet_event.clear()
        await asyncio.sleep(5)  # Check every 5 seconds
