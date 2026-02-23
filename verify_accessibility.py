from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Navigating to dashboard...")
        page.goto("http://localhost:5173/")

        # Wait for content to load
        page.wait_for_load_state("networkidle")

        print("Verifying 'Notifications' button...")
        # Use get_by_role to be more specific and avoid conflict with toast region
        notification_btn = page.get_by_role("button", name="Notifications")

        # Check if it exists and is visible
        if notification_btn.count() > 0:
             print("Found Notifications button by role and name!")
             notification_btn.hover()
        else:
             print("ERROR: Notifications button not found!")
             exit(1)

        # Take a screenshot of the header
        header = page.locator("header")
        header.screenshot(path="header_accessibility.png")
        print("Screenshot saved to header_accessibility.png")

        print("Verifying 'User menu' button...")
        user_btn = page.get_by_role("button", name="User menu")
        if user_btn.count() > 0:
            print("Found User menu button by role and name!")
        else:
             print("ERROR: User menu button not found!")
             exit(1)

        browser.close()

if __name__ == "__main__":
    run()
