import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# Launch browser
driver = uc.Chrome()

# Function to get brand part links
def get_brand_part_links(start_url, category):
    driver.get(start_url)

    wait = WebDriverWait(driver, 20)  # Wait up to 20 seconds

    try:
        # Wait for the h2 with the category name (ShopByBrand)
        category_h2 = wait.until(EC.presence_of_element_located((By.ID, category)))

        # Scroll into view just in case
        driver.execute_script("arguments[0].scrollIntoView(true);", category_h2)

        # Get the <ul> following the category <h2>
        ul_element = category_h2.find_element(By.XPATH, "following-sibling::ul[@class='nf__links']")

        # Get all links inside that <ul>
        link_elements = ul_element.find_elements(By.TAG_NAME, "a")
        links = [link.get_attribute("href") for link in link_elements if link.get_attribute("href")]

        return links

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# MAIN
dishwasher_url = "http://www.partselect.com/Dishwasher-Parts.htm"
refrigerator_url = "http://www.partselect.com/Refrigerator-Parts.htm"

# Get links for dishwasher parts and refrigerator parts
dishwasher_links = get_brand_part_links(dishwasher_url, "ShopByBrand")
refrigerator_links = get_brand_part_links(refrigerator_url, "ShopByBrand")

# Combine the links into a dictionary
brand_part_links = {
    "dishwasher_parts": dishwasher_links,
    "refrigerator_parts": refrigerator_links
}

# Output the links to a JSON file
with open('brand_part_links.json', 'w') as json_file:
    json.dump(brand_part_links, json_file, indent=4)

print(f"Saved {len(dishwasher_links)} dishwasher part links and {len(refrigerator_links)} refrigerator part links to 'brand_part_links.json'.")

# Properly close the driver
driver.quit()
