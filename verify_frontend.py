from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 720})

    # Navigate to the app
    page.goto("http://localhost:5173/")

    # Wait for the header to be visible
    notification_btn = page.get_by_label("View notifications")
    notification_btn.wait_for()

    # Hide all list items (toasts usually live in ol/ul)
    # Or just hide everything with fixed position and high z-index at top right?
    # This is a hack but should work for a screenshot.
    page.evaluate("""
        const alerts = document.querySelectorAll('li[role="status"], [data-sonner-toast], .fixed');
        alerts.forEach(el => {
            if (el.innerText.includes("Failed")) {
                el.style.display = 'none';
            }
        });
    """)

    # Focus on notification button to show focus ring
    notification_btn.focus()
    page.wait_for_timeout(500) # Wait for focus styles

    # Take screenshot of the header specifically
    header = page.locator("header")
    header.screenshot(path="verification_header_clean_2.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
