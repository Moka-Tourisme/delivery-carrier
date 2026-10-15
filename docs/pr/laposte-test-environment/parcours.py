import json
import sys

from playwright.sync_api import sync_playwright

tag, picking_id, carrier_id = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
OUT = "/tmp/claude-shots/11480"
BASE = "http://localhost:8269"


def rpc(page, model, method, args, kwargs=None):
    return page.evaluate(
        """async ([model, method, args, kwargs]) => {
            const r = await fetch('/web/dataset/call_kw/' + model + '/' + method, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({jsonrpc: '2.0', method: 'call',
                    params: {model, method, args, kwargs: kwargs || {}}})});
            return await r.json();
        }""",
        [model, method, args, kwargs],
    )


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(f"{BASE}/web/login")
    page.fill("input[name=login]", "admin")
    page.fill("input[name=password]", "admin")
    page.click("button[type=submit]")
    page.wait_for_selector(".o_navbar", timeout=60000)

    # 1. delivery method form
    page.goto(f"{BASE}/odoo/action-delivery.action_delivery_carrier_form/{carrier_id}")
    page.wait_for_selector(".o_form_view", timeout=30000)
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{OUT}/formulaire-transporteur-{tag}.png")
    alert = page.locator(".o_form_view .alert-warning").count()
    print("alert count", alert)

    # 2. delivery order, before and after sending the label
    page.goto(f"{BASE}/odoo/action-stock.action_picking_tree_all/{picking_id}")
    page.wait_for_selector(".o_form_view", timeout=30000)
    page.wait_for_timeout(1500)
    page.screenshot(path=f"{OUT}/bon-livraison-{tag}-0-avant-envoi.png")
    page.locator("button[name=button_validate]").first.click()
    page.wait_for_timeout(2000)
    sms = page.locator(".modal-footer button:has-text('Désactiver SMS')")
    if sms.count():
        sms.first.click()
    page.wait_for_timeout(7000)
    page.screenshot(path=f"{OUT}/bon-livraison-{tag}.png", full_page=True)
    res = rpc(
        page,
        "stock.picking",
        "read",
        [[picking_id], ["carrier_tracking_ref"]],
    )
    print("tracking", json.dumps(res.get("result") or res.get("error", {}).get("data", {}).get("message")))
    atts = rpc(
        page,
        "ir.attachment",
        "search_read",
        [[["res_model", "=", "stock.picking"], ["res_id", "=", picking_id]]],
        {"fields": ["name", "mimetype", "file_size"]},
    )
    print("attachments", json.dumps(atts.get("result")))
    dialog = page.locator(".modal-dialog").count()
    print("dialog", dialog, page.locator(".modal-body").first.inner_text()[:400] if dialog else "")
    browser.close()
