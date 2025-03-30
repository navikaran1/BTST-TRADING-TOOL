import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (UnexpectedAlertPresentException, 
                                      NoAlertPresentException, 
                                      TimeoutException)
import time
import logging
from typing import List, Optional
from pathlib import Path
import json
from dataclasses import dataclass
from functools import wraps
import sys

# Configuration
@dataclass
class Config:
    excel_path: str = 'D:/[01] Python Projects For Trading/Downlaod data vai link/9/ChalinkAll.xlsx'
    max_links: int = 2350
    download_timeout: int = 10
    page_load_timeout: int = 10
    retry_attempts: int = 3
    retry_delay: int = 5
    log_file: str = 'download_log.txt'
    download_button_xpath: str = '/html/body/div[2]/div/div[7]/div/div/div/div[1]/div[2]/a'
    headless: bool = False

def setup_logging(config: Config) -> None:
    """Configure logging with file and console handlers"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(config.log_file)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def retry_on_failure(max_retries: int = 3, delay: int = 5):
    """Decorator to retry a function on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logging.warning(f"Attempt {attempt} failed: {str(e)}")
                    if attempt < max_retries:
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

class DataDownloader:
    def __init__(self, config: Config):
        self.config = config
        self.driver = None
        setup_logging(config)

    def __enter__(self):
        """Context manager entry"""
        options = webdriver.ChromeOptions()
        if self.config.headless:
            options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(self.config.page_load_timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.driver:
            self.driver.quit()

    @retry_on_failure()
    def handle_alert(self) -> bool:
        """Handle any unexpected alerts"""
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            logging.warning(f"Alert present with text: {alert_text}")
            alert.accept()
            return True
        except NoAlertPresentException:
            return False

    @retry_on_failure()
    def download_link(self, link: str) -> bool:
        """Process a single download link"""
        try:
            self.driver.get(link)
            
            # Wait for page to load
            WebDriverWait(self.driver, self.config.page_load_timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            # Handle any alerts
            if self.handle_alert():
                time.sleep(2)  # Additional wait after alert
            
            # Find and click download button
            download_button = WebDriverWait(self.driver, self.config.download_timeout).until(
                EC.element_to_be_clickable((By.XPATH, self.config.download_button_xpath))
            )
            download_button.click()
            
            # Verify download completion
            WebDriverWait(self.driver, self.config.download_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
            )
            
            logging.info(f'Successfully downloaded from {link}')
            return True
            
        except TimeoutException as e:
            logging.error(f"Timeout processing {link}: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"Error processing {link}: {str(e)}")
            return False

    def process_excel(self) -> None:
        """Process all links from the Excel file"""
        try:
            df = pd.read_excel(self.config.excel_path)
            success_count = 0
            
            for index, row in df.iterrows():
                if index >= self.config.max_links:
                    break
                    
                link = row[0]  # First column contains links
                logging.info(f"Processing link {index + 1}/{min(len(df), self.config.max_links)}: {link}")
                
                if self.download_link(link):
                    success_count += 1
                
                time.sleep(1)  # Brief pause between downloads
            
            logging.info(f"Completed. Successfully downloaded {success_count} of {min(len(df), self.config.max_links)} files")
            
        except Exception as e:
            logging.error(f"Error reading Excel file: {str(e)}")
            sys.exit(1)

def main():
    """Main execution function"""
    config = Config()  # Load default config
    
    # Load config from JSON if available
    config_path = Path('downloader_config.json')
    if config_path.exists():
        try:
            with open(config_path) as f:
                config_data = json.load(f)
                for key, value in config_data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
        except Exception as e:
            logging.warning(f"Error loading config: {str(e)}")
    
    with DataDownloader(config) as downloader:
        downloader.process_excel()

if __name__ == "__main__":
    main()
