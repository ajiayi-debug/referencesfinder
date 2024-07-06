import requests

url = 'https://weather.com/weather/today/l/bfbafb71cea3672231349f36b198478ecc3d5fd524d0918b8051ee838f743675'
response = requests.get(url, verify=False)  # Ignoring SSL verification for testing

if response.status_code == 200:
    # Print or process the content here
    print(response.content)
else:
    print(f"Failed to fetch weather data. Status code: {response.status_code}")