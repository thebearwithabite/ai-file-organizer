import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto("http://localhost:5173/organize")
        # Wait for dropzone to be present
        await page.wait_for_selector('text=Drag & drop a file here')

        # Test keyboard navigation
        await page.locator('body').click()

        # Tab through elements
        for _ in range(15):
            await page.keyboard.press('Tab')
            active_el = await page.evaluate("() => document.activeElement.textContent || document.activeElement.tagName")
            print(f"Active element: {active_el}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
