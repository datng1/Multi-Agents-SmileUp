from __future__ import annotations

import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def _login_if_needed(driver) -> None:
    if "/login" not in driver.current_url:
        return
    username = os.getenv("CMO_SMOKE_USERNAME", "")
    password = os.getenv("CMO_SMOKE_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("CMO_SMOKE_USERNAME and CMO_SMOKE_PASSWORD are required for an authenticated UI smoke test")
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(1)


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    for width, height in ((1440, 1000), (390, 844)):
        driver = webdriver.Chrome(options=options)
        try:
            driver.set_window_size(width, height)
            driver.get(url)
            _login_if_needed(driver)
            time.sleep(1)
            scroll_width = int(driver.execute_script("return document.documentElement.scrollWidth"))
            client_width = int(driver.execute_script("return document.documentElement.clientWidth"))
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            overflow = scroll_width - client_width
            assert overflow <= 2, f"{width}x{height} horizontal overflow: {overflow}px"
            assert driver.find_element(By.ID, "runButton").is_displayed()
            assert driver.find_element(By.ID, "productionTasks").is_displayed()
            assert driver.find_element(By.ID, "approvalGates").is_displayed()
            assert "20 ads" in body_text
            assert "đăng bài" not in body_text
            assert "tải ảnh" not in body_text
            print(f"UI SMOKE OK {width}x{height}")
        finally:
            driver.quit()


if __name__ == "__main__":
    main()
