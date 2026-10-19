# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import mock

from roulier import roulier
from roulier.exception import InvalidApiInput

from odoo.exceptions import UserError

from . import carrier_label_case


class LaposteTestEnvironmentCase(carrier_label_case.CarrierLabelCase):
    """La Poste has no test service: the test environment must stay local."""

    transfer_in_setup = False

    def _create_order_picking(self):
        self.env.company.partner_id.write(
            {
                "country_id": self.env.ref("base.fr").id,
                "street": "35 Rue de la Republique",
                "zip": "69002",
                "city": "LYON",
                "phone": "0400000000",
                "email": "sender@example.org",
            }
        )
        self.account = self.env["carrier.account"].create(
            {
                "name": "Laposte",
                "delivery_type": "laposte_fr",
                "account": "dummy",
                "password": "dummy",
                "laposte_fr_file_format": "PDF_10x15_300dpi",
            }
        )
        self._get_carrier().carrier_account_id = self.account
        return super()._create_order_picking()

    def _get_carrier(self):
        return self.env.ref("delivery_roulier_laposte_fr.delivery_carrier_DOM")

    def _partner_data(self):
        data = super()._partner_data()
        data.update(
            {
                "street": "27 Rue Henri Rolland",
                "zip": "69100",
                "city": "VILLEURBANNE",
                "country_id": self.env.ref("base.fr").id,
            }
        )
        return data

    def _product_data(self):
        data = super()._product_data()
        data.update({"weight": 1.2})
        return data

    def test_test_environment_is_simulated(self):
        """No call reaches Colissimo, yet the label and tracking are created."""
        self._get_carrier().prod_environment = False
        with mock.patch.object(roulier, "get") as roulier_get:
            self.picking.send_to_shipper()
        roulier_get.assert_not_called()
        self._assert_labels()
        self.assertTrue(self.picking.carrier_tracking_ref.startswith("TEST-"))
        self.assertTrue(
            any("simulated" in message.body for message in self.picking.message_ids)
        )

    def test_price_method_sets_the_price_of_the_label(self):
        """The price of the rules is the cost of the shipping, not the null one."""
        carrier = self._get_carrier()
        if "price_method" not in carrier._fields:
            self.skipTest("delivery_price_method is not installed")
        self.env["delivery.price.rule"].create(
            {
                "carrier_id": carrier.id,
                "variable": "weight",
                "operator": ">=",
                "max_value": 0.0,
                "list_base_price": 10.0,
            }
        )
        carrier.write({"price_method": "base_on_rule", "prod_environment": False})
        self.picking.send_to_shipper()
        self.assertEqual(self.picking.carrier_price, 10.0)

    def test_production_environment_calls_colissimo(self):
        """In production the request still goes through roulier."""
        self._get_carrier().prod_environment = True
        with mock.patch.object(
            roulier, "get", side_effect=InvalidApiInput({"stub": "no network"})
        ) as roulier_get:
            with self.assertRaises(UserError):
                self.picking.send_to_shipper()
        roulier_get.assert_called_once()

    def test_test_environment_validates_the_request(self):
        """An invalid request is refused in test as it would be in production."""
        self._get_carrier().prod_environment = False
        self.picking.partner_id.street = False
        with mock.patch.object(roulier, "get") as roulier_get:
            with self.assertRaises(UserError):
                self.picking.send_to_shipper()
        roulier_get.assert_not_called()


class LaposteTestEnvironmentMultiPackageCase(LaposteTestEnvironmentCase):
    """One simulated label and tracking number per package."""

    def _order_line_data(self):
        return [
            {
                "product_id": self.env["product.product"]
                .create(dict(self._product_data(), name="Carrier test product %s" % i))
                .id,
                "product_uom_qty": 1,
            }
            for i in (1, 2)
        ]

    def _pack_order_picking(self):
        self.picking.move_ids.picked = True
        for move_line in self.picking.move_line_ids:
            self.picking._put_in_pack(move_line)

    def test_one_label_per_package(self):
        self._get_carrier().prod_environment = False
        self.picking.send_to_shipper()
        packages = self.picking.move_line_ids.result_package_id
        self.assertEqual(len(packages), 2)
        self.assertEqual(
            self.picking.carrier_tracking_ref,
            ";".join("TEST-%s-%s" % (self.picking.id, i) for i in (1, 2)),
        )
        self.assertEqual(len(set(packages.mapped("parcel_tracking"))), 2)
        labels = self.env["ir.attachment"].search(
            [("res_model", "=", "stock.picking"), ("res_id", "=", self.picking.id)]
        )
        self.assertEqual(len(labels), 2)
