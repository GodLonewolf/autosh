from httpx import Client
from utils import Utils
from logger import log_success, log_error, log_info
import json
import payloads

class ShopifyAuto:
    def __init__(self, store_url):
        self.base_url = 'https://' + store_url
        self.store_url = store_url
        self.session = Client()
        self.utils = Utils()
        self.cart_url = f"{self.base_url}/cart"
        self.tax = '0'
        self.email = Utils().generate_random_string(length=15) + "@gmail.com"
        self.phone = '+19174' + Utils().generate_random_digits(length=6)

    def start(self, cc):
        self.cc = cc.strip().split('|')
        self.product_counter = -1
        self.cheapest_products = self.find_cheapest_product()
        if not self.cheapest_products:
            return
        while True:
            self.product_counter += 1
            if self.product_counter == len(self.cheapest_products):
                log_error(1, "NO_PRODUCTS", self.cc)
                return
            if self.cheapest_products[self.product_counter]['variants'][0]['available'] == False or self.cheapest_products[self.product_counter]['variants'][0]['price'] == '0.00':
                continue
            if self.cheapest_products[self.product_counter]:
                self.shipping = self.cheapest_products[self.product_counter]['variants'][0]['requires_shipping']
                self.variant_id = self.cheapest_products[self.product_counter]['variants'][0]['id']
                self.product_id = self.cheapest_products[self.product_counter]['id']
                self.amount = self.cheapest_products[self.product_counter]['variants'][0]['price']
                break
            else:
                log_error(1, "NO_PRODUCTS", self.cc)
                return
        while True:
            if not self.add_to_cart(self.product_id, self.variant_id):
                return
            res = self.update_session_token()
            if res == True:
                break
            elif res == None:
                return
            else:
                self.product_counter += 1
                if self.product_counter == len(self.cheapest_products):
                    log_error(1, "NO_PRODUCTS", self.cc)
                    return
                if self.cheapest_products[self.product_counter]['variants'][0]['available'] == False or self.cheapest_products[self.product_counter]['variants'][0]['price'] == '0.00':
                    continue
                self.shipping = self.cheapest_products[self.product_counter]['variants'][0]['requires_shipping']
                self.variant_id = self.cheapest_products[self.product_counter]['variants'][0]['id']
                self.product_id = self.cheapest_products[self.product_counter]['id']
                self.amount = self.cheapest_products[self.product_counter]['variants'][0]['price']
        if not self.update_values():
            return
        if not self.fetch_cheapest_delivery():
            return
        if not self.fetch_payment_id():
            return
        if not self.fetch_receipt():
            return
        if not self.submit_receipt():
            return

    def get_products(self):
        log_info(1, "FETCHING_PRODUCTS", self.cc)
        try:
            response = self.session.get(f"{self.base_url}/products.json")
            if response.status_code == 200:
                return response.json()
            else:
                log_error(1, f"FETCH_PRODUCTS - {response.status_code}", self.cc)
                return None
        except Exception as e:
            log_error(1, f"FETCH_PRODUCTS - {e}", self.cc)
            return None

    def find_cheapest_product(self):
        products = self.get_products()
        if not products:
            return None
        all_products = products.get("products", [])
        if not all_products:
            log_error(1, "No products found in store.", self.cc)
            return None
        
        cheapest = sorted(all_products, key=lambda p: float(p['variants'][0]['price']))
        return cheapest

    def add_to_cart(self, product_id, variant_id, quantity=1):
        log_info(2, "ADD_TO_CART", self.cc)
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
                return True
            else:
                log_error(2, f"ADD_TO_CART - {response.status_code}", self.cc)
                return False
        except Exception as e:
            log_error(2, f"ADD_TO_CART - {e}", self.cc)
            return False

    def update_session_token(self):
        log_info(3, "FETCH_SESSION", self.cc)
        payload = {
            "updates[]": 1,
            "checkout": ""
        }
        try:
            response = self.session.post(f"{self.cart_url}", data=payload)
            if response.status_code == 302:
                self.sessionToken = self.utils.convert_utf8_json(self.session.cookies['checkout_session_token__cn__' + self.cartToken])['token']
                return True
            else:
                return False
        except Exception as e:
            log_error(3, f"FETCH_SESSION - {e}", self.cc)
            return None

    def update_values(self):
        log_info(4, "FETCH_TOKENS", self.cc)
        try:
            response = self.session.get(f"{self.base_url}/checkouts/cn/{self.cartToken}", follow_redirects=True, cookies=self.session.cookies)
            self.queueToken = self.utils.parse_between(response.text, 'queueToken&quot;:&quot;', '&quot;')
            self.amount = self.utils.parse_between(response.text, 'amount&quot;:&quot;', '&quot;')
            self.currency = self.utils.parse_between(response.text, 'currencyCode&quot;:&quot;', '&quot;')
            self.payment_identifier = self.utils.parse_between(response.text, 'paymentMethodIdentifier&quot;:&quot;', '&quot;')
            self.stableId = self.utils.parse_between(response.text, 'stableId&quot;:&quot;', '&quot;')
            return True
        except Exception as e:
            log_error(4, f"FETCH_TOKENS - {e}", self.cc)
            return False

    def fetch_cheapest_delivery(self):
        log_info(5, "FETCH_DELIVERY", self.cc)
        payload = payloads.proposal_payload(self.sessionToken, self.queueToken, self.variant_id, self.amount, self.currency, self.tax, self.shipping, self.email, self.phone, self.stableId)
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Checkout-Version": "2016-09-26",
            "X-Shopify-Checkout-Id": self.sessionToken
        }
        try:
            response = self.session.post(f"{self.base_url}/checkouts/unstable/graphql?operationName=Proposal", headers=headers, json=payload)
            if response.status_code == 200:
                if "TAX_NEW_TAX_MUST_BE_ACCEPTED" in  response.text:
                    self.tax = response.json()['data']['session']['negotiate']['result']['sellerProposal']['tax']['totalTaxAndDutyAmount']['value']['amount']
                    return self.fetch_cheapest_delivery()
                elif self.shipping and "Handles" not in response.text:
                    return self.fetch_cheapest_delivery()
                else:
                    self.cheapest_delivery = {"amount": '0', "handle": ''} if not self.shipping else self.utils.get_cheapest_delivery(response.json()['data']['session']['negotiate']['result']['sellerProposal']['delivery'])
                    self.queueToken = response.json()['data']['session']['negotiate']['result']['queueToken']
                    return True
            else:
                log_error(5, f"FETCH_DELIVERY - {response.status_code}", self.cc)
                return False
        except Exception as e:
            log_error(5, f"FETCH_DELIVERY - {e}", self.cc)
            return False

    def fetch_payment_id(self):
        log_info(6, "CREATE_PAYMENT", self.cc)
        payload = {
            "credit_card": {
                "number": self.cc[0],
                "month": self.cc[1],
                "year": self.cc[2],
                "verification_value": self.cc[3],
                "issue_number": "",
                "name": "Lonewolf"
            },
            "payment_session_scope": self.store_url
        }
        try:
            response = self.session.post("https://deposit.shopifycs.com/sessions", json=payload)
            if response.status_code == 200:
                self.payment_id = response.json()['id']
                return True
            else:
                log_error(6, f"CREATE_PAYMENT - {response.status_code}", self.cc)
                return False
        except Exception as e:
            log_error(6, f"CREATE_PAYMENT - {e}", self.cc)
            return False

    def fetch_receipt(self):
        log_info(7, "FETCH_RECEIPT", self.cc)
        payload = payloads.submission_payload(self.sessionToken, self.queueToken, self.variant_id, self.amount, self.currency, self.payment_id, self.payment_identifier, self.cartToken, self.stableId, self.tax, self.shipping, self.email, self.phone, self.store_url, self.cheapest_delivery['amount'], self.cheapest_delivery['handle'])
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Checkout-Version": "2016-09-26",
            "x-checkout-one-session-token": self.sessionToken,
            "x-checkout-web-source-id": self.cartToken
        }
        response = self.session.post(f"{self.base_url}/checkouts/unstable/graphql?operationName=SubmitForCompletion", headers=headers, json=payload)
        try:
            if response.status_code == 200:
                if 'TAX_NEW_TAX_MUST_BE_ACCEPTED' in response.text:
                    self.tax = response.json()['data']['submitForCompletion']['sellerProposal']['tax']['totalTaxAndDutyAmount']['value']['amount']
                    return self.fetch_receipt()
                else:
                    self.receipt_id = response.json()['data']['submitForCompletion']['receipt']['id']
                    return True
            else:
                log_error(7, f"FETCH_RECEIPT - {response.status_code}", self.cc)
                return False
        except Exception as e:
            log_error(7, f"FETCH_RECEIPT - {e}", self.cc)
            return False

    def submit_receipt(self):
        log_info(8, "SUBMIT_RECEIPT", self.cc)
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
                    log_error(8, f"{self.currency} {float(self.amount) + float(self.cheapest_delivery['amount']) + float(self.tax)} {response.json()['data']['receipt']['processingError']['code']}", self.cc, end='\n')
                    return False
                elif 'confirmationPage' in response.text:
                    log_success(8, f"{self.currency} {float(self.amount) + float(self.cheapest_delivery['amount']) + float(self.tax)} CHARGED", self.cc, end='\n')
                    return True
            else:
                log_error(8, f"SUBMIT_RECEIPT - {response.status_code}", self.cc)
                return False
        except Exception as e:
            log_error(8, f"SUBMIT_RECEIPT - {e}", self.cc)
            return False

if __name__ == "__main__":
    store = ShopifyAuto(input('Enter store url: '))
    ccs = open('cc.txt')
    for cc in ccs:
        store.start(cc)