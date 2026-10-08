GST_RATE = 18  # percent
MIN_ORDER_AMOUNT = 499


def calculate_total(items):
    subtotal = sum(i["price"] * i["qty"] for i in items)
    tax = subtotal * GST_RATE / 100
    return subtotal + tax


def apply_discount(total, code):
    if code == "WELCOME10":
        return total * 0.9
    return total


def process_payment(total):
    if total < MIN_ORDER_AMOUNT:
        raise ValueError("Order below minimum amount")
    return {"paid": total}