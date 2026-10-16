import json
import sys

from playwright.sync_api import sync_playwright

tag = sys.argv[1]
OUT = "/tmp/claude-shots/11480"
BASE = "http://localhost:8269"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1400, "height": 900})
    page.goto(f"{BASE}/web/login")
    page.fill("input[name=login]", "admin")
    page.fill("input[name=password]", "admin")
    page.click("button[type=submit]")
    page.wait_for_selector(".o_navbar", timeout=60000)

    def rpc(model, method, args, kwargs=None):
        return page.evaluate(
            """async ([model, method, args, kwargs]) => {
                const r = await fetch('/web/dataset/call_kw/' + model + '/' + method, {method: 'POST',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {model, method, args, kwargs: kwargs || {}}})});
                return (await r.json()).result;
            }""", [model, method, args, kwargs])

    partner = rpc("res.partner", "search", [[["name", "=", "Camille Martin"]]], {"limit": 1})[0]
    product = rpc("product.product", "search", [[["name", "ilike", "Vin blanc"]]], {"limit": 1})[0]
    so = rpc("sale.order", "create", [{"partner_id": partner, "order_line": [[0, 0, {"product_id": product, "product_uom_qty": 2}]]}])
    page.goto(f"{BASE}/odoo/action-sale.action_quotations_with_onboarding/{so}")
    page.wait_for_selector(".o_form_view", timeout=30000)
    page.wait_for_timeout(1500)
    page.locator("button[name=action_open_delivery_wizard]").first.click()
    page.wait_for_selector(".modal-dialog", timeout=20000)
    inp = page.locator(".modal-dialog div[name=carrier_id] input")
    inp.click()
    inp.fill("Colissimo Domicile")
    page.wait_for_timeout(1200)
    page.locator(".o-autocomplete--dropdown-item", has_text="Colissimo Domicile (FR").first.click()
    page.wait_for_timeout(1500)
    page.locator(".modal-dialog button[name=update_price]").click()
    page.wait_for_timeout(2500)
    page.screenshot(path=f"{OUT}/devis-livraison-{tag}.png")
    if tag == "apres":
        page.locator(".modal-dialog button[name=button_confirm]").click()
        page.wait_for_timeout(3000)
        lines = rpc("sale.order.line", "search_read", [[["order_id", "=", so]]], {"fields": ["name", "is_delivery", "price_unit"]})
        print("lines:", [(l["name"][:40], l["is_delivery"], l["price_unit"]) for l in lines])
        assert any(l["is_delivery"] for l in lines), "no delivery line"
        rpc("sale.order", "action_confirm", [[so]])
        o = rpc("sale.order", "read", [[so], ["state", "carrier_id", "picking_ids"]])[0]
        print("order:", o)
        pk = rpc("stock.picking", "read", [o["picking_ids"], ["name", "state", "carrier_id"]])
        print("pickings:", pk)
        assert o["state"] == "sale" and pk and pk[0]["carrier_id"], "order not confirmed or no carrier"
    b.close()
