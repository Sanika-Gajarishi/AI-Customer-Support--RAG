
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS_DIR = PROJECT_ROOT / "backend" / "data" / "documents"

POLICIES = {
    "return_policy.txt": """
ShopEase Return Policy

Eligible products can be returned within 30 days of delivery.
Products must be unused and returned in their original packaging.
Products damaged through misuse may be ineligible for return.
Customers should provide their order number when requesting a return.
Return eligibility must be confirmed before a return is approved.
""",
    "refund_policy.txt": """
ShopEase Refund Policy

Refunds are initiated after the returned product is received and inspected.
Approved refunds are processed within 5 to 7 business days.
Refunds are issued to the original payment method whenever supported.
The time taken for funds to appear may depend on the payment provider.
If a refund has not arrived after the processing period, contact support with the order number.
""",
    "shipping_policy.txt": """
ShopEase Shipping Policy

Standard delivery usually takes 3 to 7 business days.
Delivery estimates may vary by destination and product availability.
Customers receive tracking information when it becomes available.
Weather, operational issues, and courier delays may affect delivery.
Contact support if tracking information indicates an unexpected delay.
""",
    "cancellation_policy.txt": """
ShopEase Order Cancellation Policy

Customers may request cancellation before an order is shipped.
Shipped orders cannot be cancelled through the standard cancellation process.
Contact support for help with an order that has already shipped.
An accepted cancellation may qualify for a refund according to the refund policy.
A cancellation request is not approved until confirmation is provided.
""",
    "warranty_policy.txt": """
ShopEase Warranty Policy

Warranty coverage depends on the product and its manufacturer.
Customers should check the warranty information supplied with their product.
Damage caused by misuse is not automatically covered by warranty.
Customers should retain proof of purchase when requesting warranty assistance.
ShopEase support can help customers understand the next steps for a warranty claim.
""",
    "customer_faq.txt": """
ShopEase Customer Support FAQ

Q: How can I contact customer support?
A: Contact options are not specified in the initial demo policies. Contact the support team for assistance.

Q: What information should I provide about an order?
A: Provide your order number and a description of the issue.

Q: Can I return a product after 20 days?
A: Eligible products can be returned within 30 days of delivery, subject to the return conditions.

Q: How long does a refund take?
A: Approved refunds are processed within 5 to 7 business days after the returned product is received and inspected.

Q: Can I cancel an order that has shipped?
A: Shipped orders cannot be cancelled through the standard cancellation process. Contact support for assistance.

Q: Is international shipping free?
A: The policies do not specify whether international shipping is free. This must be confirmed by support.
""",
}


def main():
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    for filename, content in POLICIES.items():
        file_path = DOCUMENTS_DIR / filename
        file_path.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"Cleaned: {filename}")

    print(f"\nUpdated {len(POLICIES)} policy documents.")


if __name__ == "__main__":
    main()
