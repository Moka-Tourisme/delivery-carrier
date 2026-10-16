# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class LaposteRateShipmentCase(TransactionCase):
    def test_rate_shipment_does_not_fail(self):
        """Adding a Colissimo delivery method to a quotation must not fail.

        La Poste returns no price: the connector answers a null price instead of
        the "delivery method is not available" error of the base delivery.
        """
        carrier = self.env.ref("delivery_roulier_laposte_fr.delivery_carrier_DOM")
        partner = self.env["res.partner"].create(
            {"name": "Rate shipment test", "country_id": self.env.ref("base.fr").id}
        )
        order = self.env["sale.order"].create({"partner_id": partner.id})
        wizard = self.env["choose.delivery.carrier"].create(
            {"order_id": order.id, "carrier_id": carrier.id}
        )
        # the "Get rate" button of the "Add shipping" window of the quotation
        wizard.update_price()
        self.assertEqual(wizard.display_price, 0.0)
        self.assertFalse(wizard.delivery_message)
