from tls_client import Session
from utils import Utils
from logger import log_success, log_error, log_info
import json
import payloads

class ShopifyAuto:
    def __init__(self, store_url):
        """Initialize the class with TLS session and base Shopify URL."""
        self.base_url = 'https://' + store_url
        self.store_url = store_url
        self.session = Session()  # Secure TLS session
        self.utils = Utils()
        self.cart_url = f"{self.base_url}/cart"
        self.tax_amount = '0'
        log_info(0, "Initialized Shopify Automation Tool")

    def start(self, cc, ano, mes, cvv):
        self.product_counter = -1
        self.cheapest_products = self.find_cheapest_product()
        while True:
            self.product_counter += 1
            if self.product_counter == len(self.cheapest_products):
                log_error(1, "No Products Found")
                return None
            if self.cheapest_products[self.product_counter]['variants'][0]['available'] == False:
                continue
            if self.cheapest_products[self.product_counter]:
                self.variant_id = self.cheapest_products[self.product_counter]['variants'][0]['id']
                self.product_id = self.cheapest_products[self.product_counter]['id']
                self.amount = self.cheapest_products[self.product_counter]['variants'][0]['price']
                break
            else:
                log_error(1, "No Products Found")
                return None
            log_success(1, f"Cheapest Product Found: {self.cheapest_products[self.product_counter]['title']} at ${self.cheapest_products[self.product_counter]['variants'][0]['price']}")
        while True:
            self.add_to_cart(self.product_id, self.variant_id)
            if self.update_session_token():
                break
            else:
                self.product_counter += 1
                if self.product_counter == len(self.cheapest_products):
                    log_error(1, "No Products Found")
                    return None
                if self.cheapest_products[self.product_counter]['variants'][0]['available'] == False:
                    continue
                self.variant_id = self.cheapest_products[self.product_counter]['variants'][0]['id']
                self.product_id = self.cheapest_products[self.product_counter]['id']
                self.amount = self.cheapest_products[self.product_counter]['variants'][0]['price']
                log_success(1, f"New Cheapest Product Found: {self.cheapest_products[self.product_counter]['title']} at ${self.cheapest_products[self.product_counter]['variants'][0]['price']}")
                break
        self.update_values()
        self.fetch_cheapest_delivery()
        self.fetch_payment_id(cc, ano, mes, cvv)
        self.fetch_receipt()
        self.submit_receipt()

    def get_products(self):
        """Fetch all products from the store."""
        try:
            response = self.session.get(f"{self.base_url}/products.json")
            if response.status_code == 200:
                log_success(1, "Fetched products successfully")
                return response.json()
            else:
                log_error(1, f"Failed to fetch products, Status: {response.status_code}")
                return None
        except Exception as e:
            log_error(1, f"Exception while fetching products: {e}")
            return None

    def find_cheapest_product(self):
        products = self.get_products()
        if not products:
            return None
        all_products = products.get("products", [])
        if not all_products:
            log_error(1, "No products found in store.")
            return None
        
        cheapest = sorted(all_products, key=lambda p: float(p['variants'][0]['price']))
        return cheapest

    def add_to_cart(self, product_id, variant_id, quantity=1):
        payload = {
            "form_type": "product",
            "id": variant_id,
            "product-id": product_id,
            "quantity": quantity,
        }
        try:
            response = self.session.post(f"{self.base_url}/cart/add", data=payload)
            if response.status_code == 302:
                self.cartToken = self.session.cookies['cart'].split('%3')[0]
                log_success(2, f"Added Product {product_id} to Cart")
                return True
            else:
                log_error(2, f"Failed to add to cart, Status: {response.status_code}")
                return False
        except Exception as e:
            log_error(2, f"Exception while adding to cart: {e}")
            return False

    def update_session_token(self):
        payload = {
            "updates[]": 1,
            "checkout": ""
        }
        try:
            response = self.session.post(f"{self.cart_url}", data=payload)
            if response.status_code == 302:
                self.sessionToken = self.utils.convert_utf8_json(self.session.cookies['checkout_session_token__cn__' + self.cartToken])['token']
                log_success(3, "Session Token Fetched")
                return True
            else:
                log_error(3, f"Failed to fetch session token, Status: {response.status_code}")
                return False
        except Exception as e:
            log_error(3, f"Exception while fetchingg session token: {e}")
            return False

    def update_values(self):
        try:
            response = self.session.get(f"{self.base_url}/checkouts/cn/{self.cartToken}")
            self.queueToken = self.utils.parse_between(response.text, 'queueToken&quot;:&quot;', '&quot;')
            log_success(4, "Queue Token: " + self.queueToken)
            self.amount = self.utils.parse_between(response.text, 'amount&quot;:&quot;', '&quot;')
            log_success(4, "Amount: " + self.amount)
            self.currency = self.utils.parse_between(response.text, 'currencyCode&quot;:&quot;', '&quot;')
            log_success(4, "Currency: " + self.currency)
            self.payment_identifier = self.utils.parse_between(response.text, 'paymentMethodIdentifier&quot;:&quot;', '&quot;')
            log_success(4, "Payment Identifier: " + self.payment_identifier)
            return True
        except Exception as e:
            log_error(4, f"Exception while fetching queue token: {e}")
            return False

    def fetch_cheapest_delivery(self):
        payload = payloads.proposal_payload(self.sessionToken, self.queueToken, self.variant_id, self.amount, self.currency)
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Checkout-Version": "2016-09-26",
            "X-Shopify-Checkout-Id": self.sessionToken
        }
        try:
            response = self.session.post(f"{self.base_url}/checkouts/unstable/graphql?operationName=Proposal", headers=headers, json=payload)
            if response.status_code == 200:
                if "Handles" not in  response.text:
                    self.fetch_cheapest_delivery()
                else:
                    self.cheapest_delivery = self.utils.get_cheapest_delivery(response.json()['data']['session']['negotiate']['result']['sellerProposal']['delivery'])
                    log_success(5, f"Cheapest delivery: {self.cheapest_delivery['amount']}")
                    log_success(5, f"Delivery handle: {self.cheapest_delivery['handle']}")
                    self.stableId = response.json()['data']['session']['negotiate']['result']['sellerProposal']['delivery']['deliveryLines'][0]['targetMerchandise']['linesV2'][0]['stableId']
                    log_success(5, f"Stable ID: {self.stableId}")
                    self.queueToken = response.json()['data']['session']['negotiate']['result']['queueToken']
                    log_success(5, f"Updated queue token: {self.queueToken}")
                    return True
            else:
                log_error(5, f"Failed to make proposal, Status: {response.status_code}")
                return False
        except Exception as e:
            log_error(5, f"Exception while making proposal: {e}")
            return False

    def fetch_payment_id(self, cc, mes, ano, cvv):
        payload = {
            "credit_card": {
                "number": cc,
                "month": mes,
                "year": ano,
                "verification_value": cvv,
                "start_month": mes,
                "start_year": ano,
                "issue_number": "",
                "name": "Lonewolf"
            },
            "payment_session_scope": self.store_url
        }
        try:
            response = Session().post("https://deposit.shopifycs.com/sessions", json=payload)
            if response.status_code == 200:
                log_success(6, "Fetched payment id: " + response.json()['id'])
                self.payment_id = response.json()['id']
                return True
            else:
                log_error(6, f"Failed to add card, Status: {response.text}")
                return None
        except Exception as e:
            log_error(6, f"Exception while adding card: {e}")
            return None

    def fetch_receipt(self):
        payload = payloads.submission_payload(self.sessionToken, self.queueToken, self.variant_id, self.amount, self.currency, self.payment_id, self.payment_identifier, self.cartToken, self.stableId, self.tax_amount, self.cheapest_delivery['amount'], self.cheapest_delivery['handle'], self.store_url)
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Checkout-Version": "2016-09-26",
            "x-checkout-one-session-token": self.sessionToken,
            "x-checkout-web-source-id": self.cartToken
        }
        response = self.session.post(f"{self.base_url}/checkouts/unstable/graphql?operationName=SubmitForCompletion", headers=headers, json=payload)
        log_info(7, payload)
        try:
            if response.status_code == 200:
                if 'TAX_NEW_TAX_MUST_BE_ACCEPTED' in response.text:
                    self.tax_amount = response.json()['data']['submitForCompletion']['sellerProposal']['tax']['totalTaxAmount']['value']['amount']
                    self.fetch_receipt()
                else:
                    self.receipt_id = response.json()['data']['submitForCompletion']['receipt']['id']
                    log_success(7, f"Receipt Fetched: {self.receipt_id}")
                    return True
            else:
                log_error(7, f"Failed to checkout, Status: {response.status_code}")
                return False
        except Exception as e:
            log_info(7, response.text)
            log_error(7, f"Exception while checking out: {e}")
            return False

    def submit_receipt(self):
        payload = payloads.receipt_payload(self.sessionToken, self.receipt_id)
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Checkout-Version": "2016-09-26",
            "x-checkout-one-session-token": self.sessionToken,
            "x-checkout-web-source-id": self.cartToken
        }
        try:
            response = self.session.post(f"{self.base_url}/checkouts/unstable/graphql?operationName=PollForReceipt", json=payload, headers=headers)
            if response.status_code == 200:
                if 'discounts' in response.text:
                    self.submit_receipt()
                elif 'Error' in response.text:
                    log_error(8, f"Decline code: {response.json()['data']['receipt']['processingError']['code']} | Card: ")
                    return False
                else:
                    log_success(8, response.text)
                    return True
            else:
                log_error(8, f"Failed to submit receipt, Status: {response.text}")
                return False
        except Exception as e:
            log_error(8, f"Exception while submitting receipt: {e}")
            return False

if __name__ == "__main__":
    # shopify = ShopifyAuto('kbdfans.com')
    shopify = ShopifyAuto('sokoglam.com')
    shopify.start("4242424242424242", "12", "2025", "123")