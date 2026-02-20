import os
import time
import pyotp
import logging
from playwright.sync_api import sync_playwright
from razer.utils.telegram_utils import send_telegram_message
from .models import TaskAccounts

BROWSER_HEADLESS = True



def run_task(
        value: str,
        player_id: str = None,
        product: str = None
):  
    if product == "jawaker":
        
        product_url = "https://gold.razer.com/global/en/gold/catalog/jawaker-direct-topup"
    else:
        product_url = "https://gold.razer.com/global/en/gold/catalog/freefire-direct-top-up"
    try:
        print(f"Task started:, {value} Token")
        accounts = TaskAccounts.objects.all().order_by("-gold_balance")
        data_login = None
        for acc in accounts:
            email = acc.email
            password = acc.password
            auth_key = acc.auth_key
            data_login = login_razer(email, password, auth_key, value, player_id=player_id,
                                       product_url=product_url)
            if not data_login['success'] and "Not enought balance to purchase" in data_login['message']:
                send_telegram_message(f"⚠️ Skipping {email} due to insufficient balance")
                continue
            elif  data_login['success']:
                acc.gold_balance = float(data_login['gold'])
                acc.silver_balance = float(data_login['silver'])
                if float(data_login['gold'])<=30:
                    send_telegram_message(f"Account {email} has low balance after purchase of 30 Gold top up")
                acc.save()
                break
            else:
                send_telegram_message(f"❌ **Task failed for {email}:** {data_login['message']}")
                break
        if not data_login['success']:
            send_telegram_message(data_login['message'])
            return {"success": False, "message": f"❌ **Task failed:** {data_login['message']}"}
        print(f"✅ Task completed successfully")
        send_telegram_message(f"✅ **Task completed successfully:**  - {value} Token")
        print(data_login.get("transaction_id", "N/A"))
        return {"success": True, "transaction_id": data_login.get("transaction_id", "N/A"), "message": f"✅ Task completed successfully"}
    except Exception as e:
        send_telegram_message(f"❌ **Task failed:** {e}")
        return {"success": False, "message": f"❌ **Task failed:** {e}"}


def ensure_generate_folder():
    os.makedirs("generate", exist_ok=True)

SESSION_FILE = "razer_session.json"

log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(log_dir, "playwright_logs.log"),
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s"
)




def get_or_create_json_session():
    if os.path.exists(SESSION_FILE):
        return True
    else:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            f.write("{}")
        return False


def save_pin(
        email: str,
        value: str,
        pin_code: str
) -> None:
    ensure_generate_folder()
    filename = f"generate/{email}_{value}.txt"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(pin_code + "\n")



def get_session_file(email):
    os.makedirs("sessions", exist_ok=True)
    safe_email = email.replace("@", "_at_").replace(".", "_")
    return f"sessions/{safe_email}.json"

def ensure_login(page, email, password):

    page.goto("https://gold.razer.com/global/en",
              wait_until="domcontentloaded")

    # Agar login qilingan bo‘lsa
    if page.locator('[data-cs-override-id="nav-gold-balance"]').count() > 0:
        return

    # Aks holda qayta login qilamiz
    login(page, email, password)

    page.wait_for_selector(
        '[data-cs-override-id="nav-gold-balance"]',
        timeout=20000
    )

    page.context.storage_state(path=SESSION_FILE)


def login_razer(email, password, auth_key, value, product_url, player_id=None):

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=BROWSER_HEADLESS)
        get_or_create_json_session()
        session_file = get_session_file(email)

        if os.path.exists(session_file):
            context = browser.new_context(storage_state=session_file)
        else:
            os.remove(session_file) if os.path.exists(session_file) else None
            context = browser.new_context()
        page = context.new_page()
        block_resources(page)

        
        page.goto(product_url, timeout=10000, wait_until="domcontentloaded")
        handle_cookies(page)
        if page.locator('[data-cs-override-id="nav-gold-balance"]').count() == 0:
            login(page, email, password, auth_key)
            page.wait_for_selector(
            '[data-cs-override-id="nav-gold-balance"]',
            timeout=20000
        )   
            page.context.storage_state(path=session_file)

        if not navigate_to_coin_page(page):
            return {"success": False, "message": f"Page: {product_url} not found with player id {player_id}"}
        enter_player_number(page, player_id)
        
        checkout_result = checkout_coin(page, value)
        print("Checkout result:", checkout_result)
        if not checkout_result["success"]:
            return checkout_result

        pin_code = generate_pin(page, auth_key)

        if not pin_code:
            return {"success": False, "message": f"PIN not generated for {email} with value {value}"}
        page.wait_for_selector('[data-cs-override-id="nav-gold-balance"]', timeout=15000)
        gold_balance = page.locator('[data-cs-override-id="nav-gold-balance"] span.text--zgold').text_content()
        silver_balance = page.locator(
            '[data-cs-override-id="nav-silver-balance"] span.text--zsilver').text_content()
        page.wait_for_selector("div.row.my-2 div.col-sm-8 span")

        transaction_id = page.locator(
    "div.row.my-2 div.col-sm-8 span"
).nth(5).text_content().strip()
        save_pin(email, value, pin_code)
        print(f"PIN code generated and saved: {pin_code}")
        return {"success": True, "pin": pin_code,"gold":float(gold_balance),"silver":float(silver_balance),"transaction_id": transaction_id}


def enter_player_number(page, player_id: str):
    player_input = page.locator(
        '#accountNumber6, input[name="accountNumber"]'
    ).first

    player_input.wait_for(state="visible")
    player_input.fill(player_id)






def handle_cookies(page) -> None:
    try:
        page.wait_for_selector("button.cky-btn-accept", timeout=5000)
        page.click("button.cky-btn-accept")

        page.wait_for_selector("a[aria-label='I Agree']", timeout=5000)
        page.click("a[aria-label='I Agree']")
    except Exception as e:
        print(f"Cookie handling error: {e}")


def close_announcement_popup(page) -> None:
    try:
        dialog = page.locator("//div[@id='dialogContainer']")
        if dialog.is_visible():
            close_button = dialog.locator("//a[@aria-label='close']")
            if close_button.is_visible():
                close_button.click()
                page.wait_for_timeout(2000)
                print("✅")
            else:
                print("ℹ️ Not found")
        else:
            print("ℹ️ Not found")
    except Exception as e:
        print(f"❌ Error closing: {e}")


def login(page, email: str, password: str, auth_key: str) -> None:
    try:
        # Boshlanish - login oynasini ochish
        page.click("a[aria-label='Log in your razer id account']")
        page.wait_for_selector("#input-login-email")

        # Email kiritish
        page.fill("#input-login-email", email)
        print("Email kiritildi")

        # Parol maydonidan readonly atributni olib tashlash
        page.evaluate("document.querySelector('#input-login-password').removeAttribute('readonly')")
        page.fill("#input-login-password", password)
        print("Parol kiritildi")

        # Login tugmasini bosish
        page.click("#btn-log-in")
        page.wait_for_selector("#btn-skip")
        page.click("#btn-skip")
        page.wait_for_selector(
        '[data-cs-override-id="nav-gold-balance"]',
        timeout=20000
    )
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")



def navigate_to_coin_page(page) -> bool:
    print("Navigating to Coin page...")
    # page.wait_for_load_state("networkidle")
    print("Navigating to Coin page 2...")
    locator = page.locator('p.text-icon.text-icon-alert-line.text-icon--default.mb-0.d-flex.align-items-center')
    print("locator", locator)
    if locator.count() > 0 and locator.is_visible():
        print("Product not found")
        return False
    else:
        print("Product found")
        return True


def checkout_coin(page, product_price: str) -> dict:
    try:
        print(f"Selecting product: {product_price}")

        page.wait_for_load_state("domcontentloaded")

        tile = page.locator(f"text={product_price}").first
        tile.wait_for(timeout=10000)
        tile.click()

        print("✔ Product selected")

        
        page.get_by_text("Spend Gold Earn Silver", exact=True).click()
        reload_btn = page.locator('[data-cs-override-id="purchase-webshop-reload-checkout-btn"]')
        if reload_btn.is_visible(timeout=5000):
            return {"success": False, "message": f"Not enought balance to purchase {product_price} product"}
        btn = page.locator('[data-cs-override-id="purchase-webshop-checkout-btn"]')

        btn.wait_for(state="visible", timeout=15000)

        page.wait_for_function(
            "() => !document.querySelector('[data-cs-override-id=\"purchase-webshop-checkout-btn\"]').disabled"
        )
        btn.click()
        print("Checkout button clicked")
        

        # Redirect tekshiruv
        print("After checkout URL:", page.url)

        if "about" in page.url:
            return {
                "success": False,
                "message": "Redirected to about page (anti-fraud triggered)"
            }

        return {"success": True, "message": "Checkout successful"}

    except Exception as e:
        return {"success": False, "message": str(e)}




def generate_pin(page, auth_key: str, retries=2):
    for attempt in range(1, retries + 1):
        try:
            for sub_attempt in range(1, 9):
                totp = pyotp.TOTP(auth_key)
                otp_code = totp.now()
                print(f"Try {attempt}.{sub_attempt} - OTP:", otp_code)

                otp_iframe = page.locator("iframe[title=\"Razer OTP\"]").content_frame
                try:
                    otp_iframe.locator(".input-otp").first.wait_for(timeout=20000)
                except:
                    print("Input not found, trying to get PIN code directly...")
                    page.wait_for_selector('.pin-code')
                    pin_code = page.inner_text('.pin-code')
                    if pin_code and pin_code.strip():
                        return pin_code.strip()

                inputs = otp_iframe.locator(".input-group-otp .input-otp").all()
                if len(inputs) != 6:
                    raise Exception(f"Expected 6 OTP inputs, found: {len(inputs)}")

                for idx, inp in enumerate(inputs):
                    inp.fill(otp_code[idx])
                    time.sleep(0.1)
                time.sleep(1)
                page.wait_for_function(
    "() => window.location.href.includes('transaction') || window.location.href.includes('region=GLOBAL')",
    timeout=30000
                )
                print("OTP submitted, waiting for PIN code...",page.url)


                # 1️⃣ Agar transaction page ochilgan bo‘lsa
                if "transaction" in page.url:
                    print("Transaction page detected - job done")
                    return "TRANSACTION_SUCCESS"

                if otp_iframe.get_by_text("Invalid code. Please try").is_visible(timeout=3000):
                    print(f"Sub-attempt {sub_attempt}: Invalid OTP code, retrying...")
                    continue

                page.wait_for_selector('.pin-code', timeout=10000)
                pin_code = page.inner_text('.pin-code')
                if pin_code and pin_code.strip():
                    return pin_code.strip()
                else:
                    print("No pin-code returned yet, retrying...")

            raise Exception("Max OTP retries reached due to invalid code.")

        except Exception as e:
            print(f"Error on attempt {attempt}: {e}")
            if attempt == retries:
                return {"success": False, "message": f"Error generating PIN ({attempt}/{retries}): {e}"}
            time.sleep(2)

    return None



def block_resources(page):
    def handler(route):
        url = route.request.url

        if route.request.resource_type in ["image", "font", "media"]:
            return route.abort()

        if any(domain in url for domain in [
            "google-analytics",
            "doubleclick",
            "facebook",
            "hotjar",
            "clarity",
            "segment"
        ]):
            return route.abort()

        route.continue_()

    page.route("**/*", handler)

