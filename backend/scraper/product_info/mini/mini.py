import json
import time
import random
import zipfile
import os
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

# List of realistic user agents (removing the Gecko-based one)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; rv:115.0) Gecko/20100101 Firefox/115.0",  # Removed, using others instead
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
decodo_proxy_port = 10001
decodo_proxy_user = "omitted"
decodo_proxy_pass = "omitted"

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

# Define the list of product links
product_links = [
    "https://www.partselect.com/PS16662680-LG-MAN64890501-Door-Bin-Shelf.htm?SourceCode=18",
    "https://www.partselect.com/PS12727331-GE-WR30X30972-Ice-Maker-Assembly-Kit.htm?SourceCode=18",
    "https://www.partselect.com/PS734936-Frigidaire-240534701-Door-Shelf-Retainer-Bar.htm?SourceCode=18"
]

def scrape_product_info(url):
    driver.get(url)
    time.sleep(3)  # Wait for the page to load
    
    # Existing code for scraping basic info
    part_name = driver.find_element(By.CSS_SELECTOR, 'h1.title-lg').text
    partselect_part_number = driver.find_element(By.CSS_SELECTOR, 'div.mt-3.mb-2 span[itemprop="productID"]').text
    manufacturer_part_number = driver.find_element(By.CSS_SELECTOR, 'div.mb-2 span[itemprop="mpn"]').text
    manufacturer = driver.find_element(By.CSS_SELECTOR, 'div.mb-2 span[itemprop="brand"] span[itemprop="name"]').text
    
    # Scraping description 
    description = ""
    try:
        description_elements = driver.find_elements(By.CSS_SELECTOR, 'div[itemprop="description"].mt-3')
        if description_elements:
            description = description_elements[0].text
    except Exception as e:
        print(f"No description found: {e}")
    
    price = driver.find_element(By.CSS_SELECTOR, 'span.js-partPrice').text
    
    # Rating and reviews code (existing)
    rating = None
    num_reviews = 0
    try:
        rating_element = driver.find_element(By.CSS_SELECTOR, 'div.pd__cust-review__header__rating__chart--border')
        if rating_element:
            rating = float(rating_element.text.strip())
            
        reviews_element = driver.find_element(By.CSS_SELECTOR, 'span.rating__count')
        if reviews_element:
            reviews_text = reviews_element.text.strip()
            num_reviews = int(reviews_text.split()[0])
    except Exception as e:
        print(f"Error extracting rating/reviews: {e}")
    
    # Scraping made_for field (existing)
    try:
        made_for_text = driver.find_element(By.XPATH, "//div[contains(text(), 'Manufactured by')]/span[2]").text.strip()
        
        if "for " in made_for_text:
            made_for_text = made_for_text.split("for ")[1]
        
        made_for = [company.strip() for company in made_for_text.split(",")]
    except Exception as e:
        print(f"Error extracting made_for field: {e}")
        made_for = []
    
    # Scrape compatible models
    compatible_models = []
    try:
        # Extract the models currently visible on the page
        model_rows = driver.find_elements(By.CSS_SELECTOR, 'div.pd__crossref__list div.row')
        
        for row in model_rows:
            try:
                # Extract model number from the second column (model number column)
                model_number_element = row.find_element(By.CSS_SELECTOR, 'a')
                if model_number_element:
                    model_number = model_number_element.text.strip()
                    if model_number and model_number not in compatible_models:
                        compatible_models.append(model_number)
            except Exception as e:
                print(f"Error extracting model from row: {e}")
                continue
        
        # Check if there's a "Load more" button and handle pagination
        # Use a more robust approach with a while loop for multiple pages
        page_count = 1
        max_pages = 5  # Limit to prevent infinite loops
        
        while page_count < max_pages:
            try:
                # Find the button each time to avoid stale element references
                load_more_button = driver.find_elements(By.CSS_SELECTOR, 'div.js-loadNext')
                
                if load_more_button and load_more_button[0].is_displayed():
                    # Use JavaScript click which can be more reliable
                    driver.execute_script("arguments[0].click();", load_more_button[0])
                    print(f"Clicked 'Load more' button (page {page_count})")
                    time.sleep(2)  # Wait for more models to load
                    
                    # Get all model rows after loading more (including previously loaded ones)
                    all_rows = driver.find_elements(By.CSS_SELECTOR, 'div.pd__crossref__list div.row')
                    
                    # Process only the newly loaded rows to avoid duplicates
                    for row in all_rows:
                        try:
                            model_number_element = row.find_element(By.CSS_SELECTOR, 'a')
                            if model_number_element:
                                model_number = model_number_element.text.strip()
                                if model_number and model_number not in compatible_models:
                                    compatible_models.append(model_number)
                        except Exception as e:
                            continue
                    
                    page_count += 1
                else:
                    # No more "Load more" button visible, exit the loop
                    break
            except Exception as e:
                print(f"Error during pagination on page {page_count}: {e}")
                break
    
    except Exception as e:
        print(f"Error scraping compatible models: {e}")
    
    # IMPROVED CODE FOR TROUBLESHOOTING INFO
    troubleshooting = ""
    try:
        # Find the troubleshooting section - try different approaches
        troubleshooting_elements = []
        
        # Try finding by ID first
        try:
            trouble_section = driver.find_element(By.XPATH, "//div[@id='Troubleshooting']/following-sibling::div[@class='pd__wrap row']")
            if trouble_section:
                troubleshooting_elements = trouble_section.find_elements(By.XPATH, "./div[contains(@class, 'col-md-6')]")
        except Exception as e:
            print(f"Could not find troubleshooting section by ID: {e}")
            
            # Try alternative approach - look for specific text in columns
            try:
                troubleshooting_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'col-md-6') and .//div[contains(text(), 'This part') or contains(text(), 'replaces these')]]")
            except Exception as e:
                print(f"Could not find troubleshooting elements by text: {e}")
        
        # Process each troubleshooting element found
        troubleshooting_parts = []
        
        for element in troubleshooting_elements:
            try:
                element_text = element.text.strip()
                if element_text:
                    # Clean up the text to format it as needed
                    if "This part works with the following products:" in element_text:
                        # Format: "This part works with the following products: X."
                        products = element_text.replace("This part works with the following products:", "").strip()
                        troubleshooting_parts.append(f"This part works with the following products: {products}")
                    
                    elif "This part fixes the following symptoms:" in element_text:
                        # Format: "This part fixes the following symptoms: X."
                        symptoms = element_text.replace("This part fixes the following symptoms:", "").strip()
                        troubleshooting_parts.append(f"This part fixes the following symptoms: {symptoms}")
                    
                    elif "replaces these:" in element_text:
                        # Format: "Part# X replaces these: Y, Z."
                        # Extract the part number if present in the text
                        if "Part#" in element_text:
                            part_info = element_text
                        else:
                            # If part# not in text, use manufacturer_part_number
                            header = "Part# replaces these:"
                            replacement_text = element_text.replace(header, "").strip()
                            part_info = f"Part# {manufacturer_part_number} replaces these: {replacement_text}"
                        
                        troubleshooting_parts.append(part_info)
                    
                    # If element doesn't match any known format but has useful info, add it as is
                    elif len(element_text.split()) > 3 and not element_text.startswith("Back to"):
                        troubleshooting_parts.append(element_text)
            
            except Exception as e:
                print(f"Error processing troubleshooting element: {e}")
        
        # Combine all found troubleshooting information
        troubleshooting = ". ".join(troubleshooting_parts).replace("..", ".")
        
        # If we didn't find anything with the above approach, try a more general one
        if not troubleshooting:
            try:
                # Try to get all text from expanded sections that might contain troubleshooting info
                expanded_sections = driver.find_elements(By.CSS_SELECTOR, "div.expanded.dynamic-height")
                for section in expanded_sections:
                    section_title = section.find_element(By.CSS_SELECTOR, "div.section-title").text.strip()
                    if "Troubleshooting" in section_title:
                        # Get all text from this section excluding the title and footer
                        section_content = section.find_element(By.CSS_SELECTOR, "div.pd__wrap").text
                        if "Back to Top" in section_content:
                            section_content = section_content.split("Back to Top")[0].strip()
                        
                        # Process the content to format it properly
                        lines = [line.strip() for line in section_content.split("\n") if line.strip()]
                        formatted_lines = []
                        
                        i = 0
                        while i < len(lines):
                            if "This part" in lines[i] or "Part#" in lines[i]:
                                # This is a header line, combine with the next line if it exists
                                if i + 1 < len(lines):
                                    formatted_lines.append(f"{lines[i]}: {lines[i+1]}")
                                    i += 2
                                else:
                                    formatted_lines.append(lines[i])
                                    i += 1
                            else:
                                formatted_lines.append(lines[i])
                                i += 1
                        
                        troubleshooting = ". ".join(formatted_lines).replace("..", ".")
                        break
            except Exception as e:
                print(f"Error with alternative troubleshooting extraction: {e}")
        
    except Exception as e:
        print(f"Error extracting troubleshooting information: {e}")
    return {
        "part_name": part_name,
        "partselect_part_number": partselect_part_number,
        "manufacturer_part_number": manufacturer_part_number,
        "manufacturer": manufacturer,
        "description": description,  
        "price": price,
        "rating": rating,  
        "num_reviews": num_reviews,  
        "made_for": made_for,
        "compatible_models": compatible_models,
        "troubleshooting": troubleshooting
    }

def main():
    scraped_data = []
    for url in product_links:
        try:
            product_info = scrape_product_info(url)
            scraped_data.append(product_info)
            print(f"Successfully scraped: {product_info['part_name']}")
            print(f"Made for brands: {product_info['made_for']}")
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    
    # Save the scraped data into a JSON file
    with open("m_scraped.json", "w") as f:
        json.dump(scraped_data, f, indent=4)

    print("Scraping completed and data saved to m_scraped.json.")

if __name__ == "__main__":
    try:
        main()
    finally:
        driver.quit()  # Close the browser when done