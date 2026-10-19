# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json

from roulier import roulier

from odoo import models


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    def send_shipping(self, pickings):
        self.ensure_one()
        if self._is_roulier():
            return pickings._roulier_generate_labels()
        return super().send_shipping(pickings)

    def _is_roulier(self):
        self.ensure_one()
        available_carrier_actions = roulier.get_carriers_action_available() or {}
        return "get_label" in available_carrier_actions.get(self.delivery_type, [])

    def cancel_shipment(self, pickings):
        if self._is_roulier():
            pickings._cancel_shipment()
        else:
            return super().cancel_shipment(pickings)

    def get_tracking_link(self, picking):
        if not self._is_roulier():
            return super().get_tracking_link(picking)
        packages = picking.move_line_ids.result_package_id
        if not packages:
            return ""
        tracking_urls = []
        for package in packages:
            tracking_link = package._get_tracking_link()
            if tracking_link and tracking_link not in tracking_urls:
                tracking_urls.append(tracking_link)
        if not tracking_urls:
            return ""
        else:
            return (
                tracking_urls[0]
                if len(tracking_urls) == 1
                else json.dumps(tracking_urls)
            )

    def rate_shipment(self, order):
        self.ensure_one()
        # The webservice of a roulier carrier usually returns no price. The base
        # delivery then answers "this delivery method is not available", which
        # makes the method unusable on a quotation: answer a null price instead.
        # Unless a price method (delivery_price_method) computes the price itself.
        if (
            self._is_roulier()
            and not hasattr(self, "%s_rate_shipment" % self.delivery_type)
            and getattr(self, "price_method", "carrier") == "carrier"
        ):
            return {
                "success": True,
                "price": 0.0,
                "carrier_price": 0.0,
                "error_message": False,
                "warning_message": False,
            }
        return super().rate_shipment(order)
