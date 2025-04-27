import json
import time
import random
import zipfile
import os
import logging
from datetime import datetime
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
import undetected_chromedriver as uc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

def initialize_driver():
    """Initialize and return a Chrome driver with proper configuration"""
    # Decodo proxy credentials
    decodo_proxy_host = "gate.decodo.com"
    decodo_proxy_port = 10001
    decodo_proxy_user = "omitted"
    decodo_proxy_pass = "omitted"

    # Setup Chrome Options
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

    # Launch browser with retry mechanism
    max_retries = 3
    for attempt in range(max_retries):
        try:
            driver = uc.Chrome(options=options)
            return driver
        except Exception as e:
            if attempt < max_retries - 1:
                logger.error(f"Driver initialization failed (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(5)  # Wait before retrying
            else:
                logger.critical(f"Failed to initialize driver after {max_retries} attempts: {e}")
                raise

def safe_find_element(driver, by, selector, default=""):
    """Safely find an element, return default value if not found"""
    try:
        element = driver.find_element(by, selector)
        if element:
            return element.text.strip()
        return default
    except Exception:
        return default

def scrape_product_info(driver, url, retry_count=0, max_retries=2):
    """Scrape product information from a given URL with retry logic"""
    try:
        logger.info(f"Scraping: {url}")
        driver.get(url)
        # Use variable wait times to appear more human-like
        wait_time = random.uniform(2.5, 4.0)
        time.sleep(wait_time)
        
        # Basic product information
        part_name = safe_find_element(driver, By.CSS_SELECTOR, 'h1.title-lg')
        partselect_part_number = safe_find_element(driver, By.CSS_SELECTOR, 'div.mt-3.mb-2 span[itemprop="productID"]')
        manufacturer_part_number = safe_find_element(driver, By.CSS_SELECTOR, 'div.mb-2 span[itemprop="mpn"]')
        manufacturer = safe_find_element(driver, By.CSS_SELECTOR, 'div.mb-2 span[itemprop="brand"] span[itemprop="name"]')
        
        # Check if the page loaded properly by verifying essential elements
        if not part_name or not partselect_part_number:
            if retry_count < max_retries:
                logger.warning(f"Essential elements not found, retrying ({retry_count+1}/{max_retries}): {url}")
                time.sleep(random.uniform(3, 5))  # Wait longer before retry
                return scrape_product_info(driver, url, retry_count + 1, max_retries)
            else:
                logger.error(f"Failed to scrape after {max_retries} retries: {url}")
                return {
                    "url": url,
                    "error": "Failed to load page properly",
                    "scraped_at": datetime.now().isoformat()
                }
        
        # Description
        description = ""
        try:
            description_elements = driver.find_elements(By.CSS_SELECTOR, 'div[itemprop="description"].mt-3')
            if description_elements:
                description = description_elements[0].text.strip()
        except Exception as e:
            logger.warning(f"Error extracting description for {url}: {e}")
        
        # Price
        price = safe_find_element(driver, By.CSS_SELECTOR, 'span.js-partPrice')
        
        # Rating and reviews
        rating = None
        num_reviews = 0
        try:
            rating_element = driver.find_element(By.CSS_SELECTOR, 'div.pd__cust-review__header__rating__chart--border')
            if rating_element:
                rating_text = rating_element.text.strip()
                if rating_text and rating_text.replace('.', '', 1).isdigit():
                    rating = float(rating_text)
                
            reviews_element = driver.find_element(By.CSS_SELECTOR, 'span.rating__count')
            if reviews_element:
                reviews_text = reviews_element.text.strip()
                # Extract the number from text like "42 Reviews"
                if reviews_text:
                    num_reviews = int(reviews_text.split()[0])
        except Exception as e:
            logger.debug(f"No rating/reviews found for {url}: {e}")
        
        # Made for field
        made_for = []
        try:
            made_for_element = driver.find_element(By.XPATH, "//div[contains(text(), 'Manufactured by')]/span[2]")
            if made_for_element:
                made_for_text = made_for_element.text.strip()
                if "for " in made_for_text:
                    made_for_text = made_for_text.split("for ")[1]
                made_for = [company.strip() for company in made_for_text.split(",")]
        except Exception as e:
            logger.debug(f"No 'made for' information found for {url}: {e}")
        
        # Scrape compatible models with pagination handling
        compatible_models = []
        try:
            # Initial model collection
            model_rows = driver.find_elements(By.CSS_SELECTOR, 'div.pd__crossref__list div.row')
            for row in model_rows:
                try:
                    model_number_element = row.find_element(By.CSS_SELECTOR, 'a')
                    if model_number_element:
                        model_number = model_number_element.text.strip()
                        if model_number and model_number not in compatible_models:
                            compatible_models.append(model_number)
                except Exception:
                    continue
            
            # Handle pagination - only load up to 3 more pages to avoid excessive time
            page_count = 1
            max_pages = 4
            
            while page_count < max_pages:
                try:
                    load_more_buttons = driver.find_elements(By.CSS_SELECTOR, 'div.js-loadNext')
                    
                    if load_more_buttons and load_more_buttons[0].is_displayed():
                        # Use JavaScript click which can be more reliable
                        driver.execute_script("arguments[0].click();", load_more_buttons[0])
                        logger.debug(f"Clicked 'Load more' button (page {page_count}) for {url}")
                        # Random wait to simulate human behavior
                        time.sleep(random.uniform(1.5, 2.5))
                        
                        # Process newly loaded rows
                        all_rows = driver.find_elements(By.CSS_SELECTOR, 'div.pd__crossref__list div.row')
                        
                        for row in all_rows:
                            try:
                                model_number_element = row.find_element(By.CSS_SELECTOR, 'a')
                                if model_number_element:
                                    model_number = model_number_element.text.strip()
                                    if model_number and model_number not in compatible_models:
                                        compatible_models.append(model_number)
                            except Exception:
                                continue
                        
                        page_count += 1
                    else:
                        # No more "Load more" button visible, exit the loop
                        break
                except Exception as e:
                    logger.warning(f"Error during pagination on page {page_count} for {url}: {e}")
                    break
        
        except Exception as e:
            logger.warning(f"Error scraping compatible models for {url}: {e}")
        
        # Troubleshooting information
        troubleshooting = ""
        try:
            # Find the troubleshooting section - try different approaches
            troubleshooting_elements = []
            
            # Try finding by ID first
            try:
                trouble_section = driver.find_element(By.XPATH, "//div[@id='Troubleshooting']/following-sibling::div[@class='pd__wrap row']")
                if trouble_section:
                    troubleshooting_elements = trouble_section.find_elements(By.XPATH, "./div[contains(@class, 'col-md-6')]")
            except Exception:
                # Try alternative approach - look for specific text in columns
                try:
                    troubleshooting_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'col-md-6') and .//div[contains(text(), 'This part') or contains(text(), 'replaces these')]]")
                except Exception:
                    pass
            
            # Process each troubleshooting element found
            troubleshooting_parts = []
            
            for element in troubleshooting_elements:
                try:
                    element_text = element.text.strip()
                    if element_text:
                        # Clean up the text to format it as needed
                        if "This part works with the following products:" in element_text:
                            products = element_text.replace("This part works with the following products:", "").strip()
                            troubleshooting_parts.append(f"This part works with the following products: {products}")
                        
                        elif "This part fixes the following symptoms:" in element_text:
                            symptoms = element_text.replace("This part fixes the following symptoms:", "").strip()
                            troubleshooting_parts.append(f"This part fixes the following symptoms: {symptoms}")
                        
                        elif "replaces these:" in element_text:
                            if "Part#" in element_text:
                                part_info = element_text
                            else:
                                header = "Part# replaces these:"
                                replacement_text = element_text.replace(header, "").strip()
                                part_info = f"Part# {manufacturer_part_number} replaces these: {replacement_text}"
                            
                            troubleshooting_parts.append(part_info)
                        
                        # If element doesn't match any known format but has useful info, add it as is
                        elif len(element_text.split()) > 3 and not element_text.startswith("Back to"):
                            troubleshooting_parts.append(element_text)
                
                except Exception as e:
                    logger.debug(f"Error processing troubleshooting element for {url}: {e}")
            
            # Combine all found troubleshooting information
            troubleshooting = ". ".join(troubleshooting_parts).replace("..", ".")
            
            # If we didn't find anything with the above approach, try a more general one
            if not troubleshooting:
                try:
                    # Try to get all text from expanded sections that might contain troubleshooting info
                    expanded_sections = driver.find_elements(By.CSS_SELECTOR, "div.expanded.dynamic-height")
                    for section in expanded_sections:
                        section_title_element = section.find_elements(By.CSS_SELECTOR, "div.section-title")
                        if section_title_element and "Troubleshooting" in section_title_element[0].text.strip():
                            # Get all text from this section excluding the title and footer
                            section_content_element = section.find_elements(By.CSS_SELECTOR, "div.pd__wrap")
                            if section_content_element:
                                section_content = section_content_element[0].text
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
                    logger.debug(f"Error with alternative troubleshooting extraction for {url}: {e}")
            
        except Exception as e:
            logger.warning(f"Error extracting troubleshooting information for {url}: {e}")
        
        # Return the scraped data
        return {
            "url": url,
            "part_name": part_name,
            "partselect_part_number": partselect_part_number,
            "manufacturer_part_number": manufacturer_part_number,
            "manufacturer": manufacturer,
            "description": description,
            "price": price,
            "rating": rating,
            "num_reviews": num_reviews,
            "made_for": made_for,
            "compatible_models": compatible_models[:100],  # Limit to avoid excessive data
            "troubleshooting": troubleshooting,
            "scraped_at": datetime.now().isoformat()
        }
        
    except TimeoutException as e:
        logger.error(f"Timeout while scraping {url}: {e}")
        if retry_count < max_retries:
            logger.info(f"Retrying {url} after timeout ({retry_count+1}/{max_retries})")
            time.sleep(random.uniform(5, 10))  # Longer wait after timeout
            return scrape_product_info(driver, url, retry_count + 1, max_retries)
        return {"url": url, "error": f"Timeout: {str(e)}", "scraped_at": datetime.now().isoformat()}
        
    except WebDriverException as e:
        logger.error(f"WebDriver error while scraping {url}: {e}")
        if "chrome not reachable" in str(e).lower() and retry_count < max_retries:
            logger.info("Browser crashed, restarting and retrying...")
            # We need to return a special signal to restart the browser
            return {"restart_browser": True, "url": url, "retry_count": retry_count}
        return {"url": url, "error": f"WebDriver error: {str(e)}", "scraped_at": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        if retry_count < max_retries:
            logger.info(f"Retrying {url} after error ({retry_count+1}/{max_retries})")
            time.sleep(random.uniform(3, 7))
            return scrape_product_info(driver, url, retry_count + 1, max_retries)
        return {"url": url, "error": str(e), "scraped_at": datetime.now().isoformat()}

def process_in_batches(urls, batch_size=10, save_interval=20):
    """Process URLs in batches to manage resources and enable partial progress saving"""
    
    total_urls = len(urls)
    logger.info(f"Starting to process {total_urls} URLs in batches of {batch_size}")
    
    all_results = []
    successful_count = 0
    failed_count = 0
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Load progress from previous run if exists
    progress_file = "output/scraping_progress.json"
    processed_urls = set()
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
                processed_urls = set(progress_data.get("processed_urls", []))
                logger.info(f"Loaded progress: {len(processed_urls)} URLs already processed")
                
                # Also load previous results if available
                results_file = "output/partselect_data.json"
                if os.path.exists(results_file):
                    with open(results_file, 'r') as rf:
                        all_results = json.load(rf)
                        logger.info(f"Loaded {len(all_results)} previously scraped products")
        except Exception as e:
            logger.error(f"Error loading progress file: {e}")
    
    # Filter out already processed URLs
    urls_to_process = [url for url in urls if url not in processed_urls]
    logger.info(f"{len(urls_to_process)} URLs remaining to process")
    
    # Calculate batches
    num_batches = (len(urls_to_process) + batch_size - 1) // batch_size
    
    # Initialize the driver outside the batch loop to reuse it
    driver = None
    current_batch_results = []
    
    try:
        driver = initialize_driver()
        
        for batch_num in range(num_batches):
            batch_start = batch_num * batch_size
            batch_end = min((batch_num + 1) * batch_size, len(urls_to_process))
            current_batch = urls_to_process[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_num+1}/{num_batches} with {len(current_batch)} URLs")
            
            for url_index, url in enumerate(current_batch):
                overall_index = batch_start + url_index + 1
                logger.info(f"Processing {overall_index}/{len(urls_to_process)}: {url}")
                
                # Random delay between requests to avoid detection
                if url_index > 0:
                    time.sleep(random.uniform(1, 3))
                
                result = scrape_product_info(driver, url)
                
                # Check if we need to restart the browser
                if isinstance(result, dict) and result.get("restart_browser", False):
                    logger.info("Restarting browser as requested...")
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                    driver = initialize_driver()
                    url = result["url"]
                    retry_count = result.get("retry_count", 0)
                    # Retry with the new browser
                    result = scrape_product_info(driver, url, retry_count=retry_count+1)
                
                # Track successful and failed scrapes
                if "error" in result:
                    failed_count += 1
                else:
                    successful_count += 1
                
                # Add to results and current batch
                all_results.append(result)
                current_batch_results.append(result)
                processed_urls.add(url)
                
                # Save progress periodically based on total processed
                if (overall_index % save_interval == 0) or (overall_index == len(urls_to_process)):
                    # Save current progress
                    progress_data = {
                        "processed_urls": list(processed_urls),
                        "last_processed": overall_index,
                        "total_to_process": len(urls_to_process),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    with open(progress_file, 'w') as f:
                        json.dump(progress_data, f, indent=2)
                    
                    # Save all data collected so far
                    with open("output/partselect_data.json", 'w') as f:
                        json.dump(all_results, f, indent=2)
                    
                    logger.info(f"Saved progress: {overall_index}/{len(urls_to_process)} URLs processed")
            
            # Save batch results separately
            batch_filename = f"output/partselect_batch_{batch_num+1}.json"
            with open(batch_filename, 'w') as f:
                json.dump(current_batch_results, f, indent=2)
            
            logger.info(f"Completed batch {batch_num+1}/{num_batches}, saved to {batch_filename}")
            current_batch_results = []  # Reset for next batch
            
            # Add a longer delay between batches
            if batch_num < num_batches - 1:
                wait_time = random.uniform(5, 10)
                logger.info(f"Waiting {wait_time:.2f} seconds before next batch...")
                time.sleep(wait_time)
    
    except KeyboardInterrupt:
        logger.warning("Script interrupted by user, saving progress...")
        # Save current progress before exiting
        progress_data = {
            "processed_urls": list(processed_urls),
            "last_processed": len(processed_urls),
            "total_to_process": len(urls_to_process),
            "timestamp": datetime.now().isoformat(),
            "status": "interrupted"
        }
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
            
        with open("output/partselect_data.json", 'w') as f:
            json.dump(all_results, f, indent=2)
            
    except Exception as e:
        logger.critical(f"Unexpected error in batch processing: {e}")
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        # Final summary
        total_processed = successful_count + failed_count
        success_rate = (successful_count / total_processed * 100) if total_processed > 0 else 0
        
        logger.info(f"Scraping completed: {total_processed} URLs processed")
        logger.info(f"Success: {successful_count} ({success_rate:.2f}%), Failed: {failed_count}")
        
        return all_results

def main():
    """Main function to load URLs and start scraping"""
    # Start time for tracking total execution time
    start_time = time.time()
    
    # Load product links from JSON file
    input_file = "product_links.json"  # Change to your input file
    
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
            product_links = data.get("product_links", [])
            
        if not product_links:
            logger.error(f"No product links found in {input_file}")
            return
            
        logger.info(f"Loaded {len(product_links)} URLs from {input_file}")
        
        # Process URLs in batches
        results = process_in_batches(product_links, batch_size=10, save_interval=20)
        
        # Save final results
        output_file = "output/partselect_final_data.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"All data saved to {output_file}")
        
        # Calculate and log execution time
        elapsed_time = time.time() - start_time
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        logger.info(f"Total execution time: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            
    except FileNotFoundError:
        logger.error(f"Input file {input_file} not found")
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in {input_file}")
    except Exception as e:
        logger.critical(f"Error in main function: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}")