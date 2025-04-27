import json
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc


"Base scraper for collecting product links from brand pages JSON on PartSelect.com"

# Block images and CSS to speed up loading
options = uc.ChromeOptions()
prefs = {
    "profile.managed_default_content_settings.images": 2,  # Disable images
    "profile.managed_default_content_settings.stylesheets": 2,  # Disable CSS
}
options.add_experimental_option("prefs", prefs)

# Launch the browser
driver = uc.Chrome(options=options)

# Function to scroll down the page like a human (in small steps)
def human_scroll(driver, total_scrolls=10, delay_range=(0.2, 0.6)):
    """Scrolls down the page in small steps with random delays."""
    for _ in range(total_scrolls):
        driver.execute_script("window.scrollBy(0, window.innerHeight / 2);")  # Scroll down half screen
        time.sleep(random.uniform(*delay_range))  # Random delay between scrolls

# Function to get product links from a brand page
def get_product_links(start_url):
    driver.get(start_url)

    wait = WebDriverWait(driver, 60)  # Wait for the page to load

    try:
        # Human-like scroll to bottom
        human_scroll(driver, total_scrolls=random.randint(8, 15), delay_range=(0.3, 0.7))

        # Wait for the product links to be loaded (waiting for a specific element to appear)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "nf__part__detail__title")))

        # Now grab all the product links that are visible
        link_elements = driver.find_elements(By.CLASS_NAME, "nf__part__detail__title")
        product_links = [link.get_attribute("href") for link in link_elements if link.get_attribute("href")]

        # Check if the "Page Not Found" error or "Access Denied" is displayed on the page
        body_text = driver.page_source
        if "Page Not Found" or "Access Denied" in body_text:
            print(f"Page error: {start_url}")
            return []  # Return an empty list if the page is not found

        return product_links

    except Exception as e:
        print(f"An error occurred on {start_url}: {e}")
        return []

# MAIN
# Load the existing brand links and product links from the JSON file
try:
    with open('product_links.json', 'r') as json_file:
        data = json.load(json_file)
        existing_product_links = data.get("product_links", [])
        failed_urls = data.get("failed_urls", [])
except FileNotFoundError:
    existing_product_links = []
    failed_urls = []

# Load the brand links from the brand_part_links JSON file
with open('brand_part_links.json', 'r') as json_file:
    brand_part_links = json.load(json_file)

# Combine dishwasher and refrigerator links
all_brand_links = brand_part_links.get("dishwasher_parts", []) + brand_part_links.get("refrigerator_parts", [])

# List to store all product links
all_product_links = existing_product_links  # Start with previously saved product links

# Scrape product links from each brand page
for brand_url in all_brand_links:
    print(f"Trying to collect product links from: {brand_url}")
    product_links = get_product_links(brand_url)

    if product_links:
        all_product_links.extend(product_links)
    else:
        failed_urls.append(brand_url)  # Log the URL if it fails

    # Save progress every iteration in case of timeout or failure
    with open('product_links.json', 'w') as json_file:
        json.dump({
            "product_links": list(set(all_product_links)),  # Remove duplicates
            "failed_urls": failed_urls
        }, json_file, indent=4)

    # Random sleep after scraping each brand
    sleep_duration = random.uniform(2, 6)
    print(f"Sleeping for {sleep_duration:.2f} seconds to mimic human behavior...")
    time.sleep(sleep_duration)

# Final save to JSON with updated product links and failed URLs
with open('product_links.json', 'w') as json_file:
    json.dump({
        "product_links": list(set(all_product_links)),  # Remove duplicates
        "failed_urls": failed_urls
    }, json_file, indent=4)

print(f"Saved {len(all_product_links)} unique product links to 'product_links.json'.")
print(f"Failed URLs: {len(failed_urls)}")

# Close browser
driver.quit()
