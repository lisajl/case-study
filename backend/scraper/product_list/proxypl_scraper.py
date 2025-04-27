import json
import time
import random
import zipfile
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

"Modified scraper for collecting product links from brand pages JSON on PartSelect.com, using rotating proxies from Decodo"
"and random user agents"


# List of realistic user agents 
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.111 Safari/537.36",
]

# Function to create a proxy extension for Decodo
def create_proxy_extension(proxy_host, proxy_port, proxy_user, proxy_pass):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Proxy Extension",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        }
    }
    """

    background_js = f"""
    var config = {{
            mode: "fixed_servers",
            rules: {{
              singleProxy: {{
                scheme: "http",
                host: "{proxy_host}",
                port: parseInt({proxy_port})
              }},
              bypassList: ["localhost"]
            }}
          }};
    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});
    chrome.webRequest.onAuthRequired.addListener(
        function(details) {{
            return {{
                authCredentials: {{
                    username: "{proxy_user}",
                    password: "{proxy_pass}"
                }}
            }};
        }},
        {{urls: ["<all_urls>"]}},
        ['blocking']
    );
    """

    pluginfile = 'proxy_auth_plugin.zip'

    with zipfile.ZipFile(pluginfile, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return pluginfile

# === Decodo proxy credentials ===
decodo_proxy_host = "gate.decodo.com"
decodo_proxy_port = 11111
decodo_proxy_user = "OMITTED!"
decodo_proxy_pass = "OMITTED!"

# === Setup Chrome Options ===
options = uc.ChromeOptions()

# Randomize user-agent
user_agent = random.choice(USER_AGENTS)
options.add_argument(f"user-agent={user_agent}")

# Add common headers via arguments
options.add_argument("--accept-language=en-US,en;q=0.9")
options.add_argument("--accept-encoding=gzip, deflate, br")
options.add_argument("--upgrade-insecure-requests")

# Disable images & CSS to save bandwidth
prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.managed_default_content_settings.stylesheets": 2,
}
options.add_experimental_option("prefs", prefs)

# Add proxy extension
proxy_plugin_path = create_proxy_extension(
    proxy_host=decodo_proxy_host,
    proxy_port=decodo_proxy_port,
    proxy_user=decodo_proxy_user,
    proxy_pass=decodo_proxy_pass
)
options.add_extension(proxy_plugin_path)

# Launch browser
driver = uc.Chrome(options=options)

# Function to scroll down the page like a human (in small steps)
def human_scroll(driver, total_scrolls=10, delay_range=(0.2, 0.6)):
    for _ in range(total_scrolls):
        driver.execute_script("window.scrollBy(0, window.innerHeight / 2);")
        time.sleep(random.uniform(*delay_range))

# Function to get product links from a brand page
def get_product_links(start_url):
    driver.get(start_url)
    wait = WebDriverWait(driver, 60)

    try:
        human_scroll(driver, total_scrolls=random.randint(8, 15), delay_range=(0.3, 0.7))

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "nf__part__detail__title")))
        link_elements = driver.find_elements(By.CLASS_NAME, "nf__part__detail__title")
        product_links = [link.get_attribute("href") for link in link_elements if link.get_attribute("href")]

        body_text = driver.page_source
        if "Page Not Found" in body_text or "Access Denied" in body_text:
            print(f"Page error: {start_url}")
            return []

        return product_links

    except Exception as e:
        print(f"An error occurred on {start_url}: {e}")
        return []

# MAIN
try:
    with open('product_links.json', 'r') as json_file:
        data = json.load(json_file)
        existing_product_links = data.get("product_links", [])
        failed_urls = data.get("failed_urls", [])
except FileNotFoundError:
    existing_product_links = []
    failed_urls = []

with open('brand_part_links.json', 'r') as json_file:
    brand_part_links = json.load(json_file)

all_brand_links = brand_part_links.get("dishwasher_parts", []) + brand_part_links.get("refrigerator_parts", [])
all_product_links = existing_product_links

for brand_url in all_brand_links:
    print(f"Trying to collect product links from: {brand_url}")
    product_links = get_product_links(brand_url)

    if product_links:
        all_product_links.extend(product_links)
    else:
        failed_urls.append(brand_url)

    with open('product_links.json', 'w') as json_file:
        json.dump({
            "product_links": list(set(all_product_links)),
            "failed_urls": failed_urls
        }, json_file, indent=4)

    sleep_duration = random.uniform(2, 6)
    print(f"Sleeping for {sleep_duration:.2f} seconds to mimic human behavior...")
    time.sleep(sleep_duration)

with open('product_links.json', 'w') as json_file:
    json.dump({
        "product_links": list(set(all_product_links)),
        "failed_urls": failed_urls
    }, json_file, indent=4)

print(f"Saved {len(all_product_links)} unique product links to 'product_links.json'.")
print(f"Failed URLs: {len(failed_urls)}")

driver.quit()

# Clean up proxy plugin file
if os.path.exists(proxy_plugin_path):
    os.remove(proxy_plugin_path)
