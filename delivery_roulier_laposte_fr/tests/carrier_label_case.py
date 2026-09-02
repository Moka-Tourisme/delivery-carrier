# Copyright 2020 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

# Ported from base_delivery_carrier_label, which was split in 18.0 and no
# longer provides a reusable carrier label test case.

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class CarrierLabelCase(TransactionCase):
    """Base class for carrier label tests. Inherit and override _get_carrier
    to return the carrier you want to test"""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self._create_order_picking()

    @property
    def transfer_in_setup(self):
        return True

    def _create_order_picking(self):
        """Create a sale order and deliver the picking"""
        self.order = self.env["sale.order"].create(self._sale_order_data())
        for product in self.order.mapped("order_line.product_id"):
            self.env["stock.quant"].with_context(inventory_mode=True).create(
                {
                    "product_id": product.id,
                    "location_id": self.order.warehouse_id.lot_stock_id.id,
                    "inventory_quantity": sum(
                        self.order.mapped("order_line.product_uom_qty")
                    ),
                }
            ).action_apply_inventory()
        self.order.action_confirm()
        self.picking = self.order.picking_ids
        self.picking.write(self._picking_data())
        self._pack_order_picking()
        if self.transfer_in_setup:
            self._transfer_order_picking()

    def _pack_order_picking(self):
        """Put every product in a destination package.

        roulier refuses to ask for a label otherwise. action_put_in_pack()
        cannot be used here: with a carrier set, stock_delivery makes it
        return the package type wizard instead of packing.
        """
        self.picking.move_ids.picked = True
        self.picking._put_in_pack(self.picking._package_move_lines())

    def _transfer_order_picking(self):
        # stock.immediate.transfer was dropped in 17.0: validating the picking
        # directly picks the quantities already flagged as picked.
        self.picking.button_validate()

    def _get_carrier(self):
        """Return the carrier to test"""
        raise NotImplementedError()

    def _sale_order_data(self):
        """Return a values dict to create a sale order"""
        return {
            "partner_id": self.env["res.partner"].create(self._partner_data()).id,
            "order_line": [(0, 0, data) for data in self._order_line_data()],
            "carrier_id": self._get_carrier().id,
        }

    def _partner_data(self):
        """Return a values dict to create a partner"""
        return {
            "name": "Carrier label test customer",
        }

    def _order_line_data(self):
        """Return a list of value dicts to create order lines"""
        return [
            {
                "product_id": self.env["product.product"]
                .create(self._product_data())
                .id,
                "product_uom_qty": 1,
            }
        ]

    def _product_data(self):
        """Return a values dict to create a product"""
        return {
            "name": "Carrier test product",
            "type": "consu",
            "is_storable": True,
        }

    def _picking_data(self):
        """Return a values dict to be written to the picking in order to set
        carrier options"""
        return {}

    def _assert_labels(self):
        """Fail if there are no labels for the current picking"""
        try:
            self.picking._check_existing_shipping_label()
        except UserError:
            return
        self.fail("No labels found")


class TestCarrierLabel(CarrierLabelCase):
    # Since 18.0 odoo.tests.loader only collects test methods declared in the
    # class __dict__, so carrier subclasses would inherit test_labels without
    # ever running it.
    allow_inherited_tests_method = True

    def test_labels(self):
        """Test if labels are created by the button"""
        self.picking.send_to_shipper()
        self._assert_labels()
