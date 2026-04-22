from playwright.sync_api import sync_playwright

def verify_breadcrumbs():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the dashboard (root)
        print("Navigating to Dashboard...")
        page.goto("http://localhost:5173")
        page.wait_for_selector("text=Dashboard")

        # Take a screenshot of the Dashboard
        page.screenshot(path="frontend_v2/tests/verification/dashboard_breadcrumbs.png")
        print("Screenshot saved: dashboard_breadcrumbs.png")

        # Navigate to another page (e.g., Organize)
        print("Navigating to Organize page...")
        page.goto("http://localhost:5173/organize")
        page.wait_for_selector("text=Organize")

        # Take a screenshot of the Organize page
        page.screenshot(path="frontend_v2/tests/verification/organize_breadcrumbs.png")
        print("Screenshot saved: organize_breadcrumbs.png")

        browser.close()

if __name__ == "__main__":
    verify_breadcrumbs()
