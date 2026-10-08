CANCEL_WINDOW_HOURS = 24
REFUND_DAYS = 7
DELIVERY_DAYS = 3


class OrderService:
    def place_order(self, cart):
        return {"items": cart, "status": "placed"}

    def cancel_order(self, order, hours_since_placed):
        if hours_since_placed > CANCEL_WINDOW_HOURS:
            return False
        order["status"] = "cancelled"
        return True

    def refund_order(self, order, days_since_delivery):
        if days_since_delivery > REFUND_DAYS:
            return False
        order["status"] = "refunded"
        return True

    def delivery_estimate(self):
        return f"Delivery in {DELIVERY_DAYS} days"