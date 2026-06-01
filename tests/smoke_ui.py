from __future__ import annotations

import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


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
            time.sleep(1.2)
            scroll_width = int(driver.execute_script("return document.documentElement.scrollWidth"))
            client_width = int(driver.execute_script("return document.documentElement.clientWidth"))
            role = driver.execute_script(
                "var e=document.getElementById('processingScreen');"
                "return e ? e.getAttribute('role') : null;"
            )
            image_fit = driver.execute_script(
                """
                var box = document.getElementById('fbPreviewImage');
                box.className = 'fb-preview-image has-image';
                box.innerHTML = '<img alt="fit test" src="/assets/clinic-overview.png"><span>Ảnh test</span>';
                var img = box.querySelector('img');
                var b = box.getBoundingClientRect();
                var r = img.getBoundingClientRect();
                return {
                  boxWidth: b.width,
                  boxHeight: b.height,
                  imgWidth: r.width,
                  imgHeight: r.height,
                  left: r.left - b.left,
                  right: b.right - r.right,
                  top: r.top - b.top,
                  bottom: b.bottom - r.bottom
                };
                """
            )
            body_text = driver.find_element(By.TAG_NAME, "body").text
            overflow = scroll_width - client_width
            assert overflow <= 2, f"{width}x{height} horizontal overflow: {overflow}px"
            assert role == "status", f"{width}x{height} processingScreen role={role!r}"
            assert image_fit["imgWidth"] <= image_fit["boxWidth"] + 1, f"{width}x{height} preview image overflows width: {image_fit}"
            assert image_fit["imgHeight"] <= image_fit["boxHeight"] + 1, f"{width}x{height} preview image overflows height: {image_fit}"
            assert image_fit["left"] >= -1 and image_fit["right"] >= -1, f"{width}x{height} preview image spills horizontally: {image_fit}"
            assert image_fit["top"] >= -1 and image_fit["bottom"] >= -1, f"{width}x{height} preview image spills vertically: {image_fit}"
            assert "Page 2466359750553689" not in body_text, "raw fallback page id is visible"
            print(f"UI SMOKE OK {width}x{height}")
        finally:
            driver.quit()


if __name__ == "__main__":
    main()
