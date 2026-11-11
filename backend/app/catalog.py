from .schemas import Product

PRODUCTS = [
    Product(id="keyboard-001", name="Bluetooth Wireless Keyboard", category="keyboard", price="2500.00", merchant="Demo Store", features={"connectivity": "Bluetooth"}),
    Product(id="keyboard-002", name="Wired USB Keyboard", category="keyboard", price="2200.00", merchant="Demo Store", features={"connectivity": "USB"}),
    Product(id="keyboard-003", name="Premium Bluetooth Keyboard", category="keyboard", price="3500.00", merchant="Demo Store", features={"connectivity": "Bluetooth"}),
]

def get_product(product_id: str) -> Product | None:
    return next((p for p in PRODUCTS if p.id == product_id), None)
