from __future__ import annotations

from .tools import money


def product_line(p: dict) -> str:
    state = "in stock" if p["available"] else {"discontinued": "discontinued", "coming_soon": "coming soon"}.get(p["status"], "out of stock")
    price = money(p["sale_cents"])
    if p["discount_percent"]:
        price = f"{money(p['price_cents'])} → {price} ({p['discount_percent']}% off; no extra PIX discount)"
    return f"{p['name']} — {price} · {state}"


def render(result: dict) -> str:
    kind = result["kind"]
    if kind == "catalog":
        products = result["products"]
        if not products:
            return "I checked the supplied catalog and found no matching products under those conditions. I cannot confirm an item that is not listed. Would you like another model or a different budget?"
        text = "Here is what I found in the current supplied catalog:\n\n" + "\n".join(f"• {product_line(p)}" for p in products)
        if result.get("alternatives"):
            text += "\n\nAvailable alternatives:\n" + "\n".join(f"• {product_line(p)}" for p in result["alternatives"])
        if result["total_matches"] > len(products):
            text += f"\n\nShowing {len(products)} of {result['total_matches']} matches. Tell me a brand or model to narrow the search."
        return text + "\n\nStock and prices reflect the case's data snapshot; the team should confirm before checkout."
    if kind == "policy":
        if not result["found"]:
            return "I could not find a supported policy for that question. Please ask the human team to confirm."
        return "\n\n".join(card["title"] + "\n" + card["summary"] for card in result["cards"])
    if kind == "order":
        if result["status"] == "verification_required":
            return "Before I share order information, please use Verify order with your order number and purchase email. Verification stays in this local application and is not sent to a language model."
        if result["status"] == "unavailable":
            return "I cannot access that order for the currently verified customer. Please check the number or verify the correct purchase email."
        order = result["order"]
        text = f"Order #{order['id']} is {order['status']}. Recorded total: {money(order['total_cents'])}."
        text += "\n\n" + "\n".join(f"• {i['quantity']} × {i['name']}" for i in result["items"])
        if order["tracking_code"]:
            text += f"\n\nTracking code: {order['tracking_code']}."
        else:
            text += "\n\nNo tracking code is recorded yet."
        if order["estimated_delivery"]:
            text += f" The recorded delivery estimate is {order['estimated_delivery']}; this is not confirmation of actual receipt or a refreshed carrier estimate."
        else:
            text += " There is no confirmed delivery estimate in the supplied record."
        return text + "\n\nThis is the supplied order snapshot, not a live carrier lookup."
    if kind == "payment":
        if result["status"] != "quoted":
            return "I cannot quote payment for that item or quantity because it is unavailable in the supplied catalog. Please choose an available model."
        text = f"For {result['quantity']} × {result['product']}, the list total is {money(result['list_total_cents'])}. "
        if result["discount_percent"]:
            text += f"With {result['discount_percent']}% off, the total is {money(result['total_cents'])}. "
        else:
            text += f"The total is {money(result['total_cents'])}. "
        if result["promotion_applied"]:
            text += "The active promotion applies; the 5% PIX discount cannot be added. "
        if result["method"] == "credit":
            if result["allowed"]:
                text += f"{result['installments']} interest-free payment(s) are permitted. "
                base, remainder = result["installment_floor_cents"], result["installment_remainder_cents"]
                if remainder:
                    text += f"Rounding: {remainder} payment(s) of {money(base+1)} and {result['installments']-remainder} of {money(base)}."
                else:
                    text += f"Each payment is {money(base)}."
            else:
                text += f"{result['installments']} payments do not meet the policy's minimum installment. Allowed counts: " + ", ".join(map(str, result["allowed_installments"])) + "."
        elif not result["allowed"]:
            text += "This method requires a single payment."
        else:
            text += "This quote uses a single payment."
        return text + "\n\nThis is a quote only; no payment or reservation has been created."
    if kind == "return":
        status = result["status"]
        if status == "needs_information":
            return "I can check the return policy. Please tell me " + "; ".join(result["missing"]) + ". Estimated delivery is not the actual receipt date."
        if status == "invalid_date":
            return "That receipt date is in the future. Please confirm the actual date you received the instrument."
        if status == "human_review":
            return f"Based on the details given ({result['days_since_receipt']} calendar days since receipt), this request needs human review. I cannot approve or deny it automatically. The manual has separate exchange and warranty rules; the team can review your rights and the instrument's condition. No refund request has been sent."
        return f"Based on the information you provided, you are within the manual's 7-calendar-day online change-of-mind window ({result['days_since_receipt']} days since actual receipt). The manual requests original packaging, no use and all included materials. Personalized or final-sale items need staff review. It states that the store pays return freight and refunds the original payment method within 10 business days. This is preliminary guidance; the human team must review the request. No return or refund has been created."
    if kind == "shipping":
        if result["status"] == "boundary_review":
            return "For an order of exactly BRL 500.00 in metropolitan Campo Grande, the manual does not define the shipping fee: it only says above or below BRL 500. Please ask the team to confirm; I will not invent a charge."
        if result["status"] == "carrier_quote_required":
            return "For another city, the freight charge requires the destination, weight and dimensions. The supplied data cannot generate a carrier quote. Please ask the team."
        return f"For metropolitan Campo Grande, the policy shipping fee is {money(result['fee_cents'])}. The policy estimate is 1-3 business days; this is not a confirmed delivery date."
    raise ValueError("Unsupported result type")
