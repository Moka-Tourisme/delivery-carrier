# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from vcr_unittest import VCRMixin

from odoo import tools

from odoo.tests import common

from . import carrier_label_case


class LaposteLabelDomCase(VCRMixin, carrier_label_case.TestCarrierLabel):
    # the label is asked for when the picking is validated: keep that out of
    # setUp, where VCRMixin has not started the cassette yet
    transfer_in_setup = False

    @classmethod
    def _request_handler(cls, s, r, /, **kw):
        # Since 18.0 BaseCase patches requests.Session.send and blocks every
        # external call, which fires before VCR can serve the cassette. Hand
        # the request back to the real sender so VCR intercepts it lower down;
        # with record_mode "once" and an existing cassette nothing can reach
        # the network.
        return common._super_send(s, r, **kw)

    def setUp(self, *args, **kwargs):
        # need it to be defined before super to avoid failure in _hide_sensitive_data
        self.account = False
        # the cassettes for this case contain some big requests
        # that are causing travis build to fail when logged
        with tools.mute_logger("vcr.cassette"):
            super().setUp(*args, **kwargs)

    def _hide_sensitive_data(self, request):
        password = self.account and self.account.password or "dummy"
        account = self.account and self.account.account or "dummy"
        body = request.body
        body = body.replace(password.encode(), b"password")
        body = body.replace(account.encode(), b"000000")
        request.body = body
        return request

    def _get_vcr_kwargs(self, **kwargs):
        return {
            "record_mode": "once",
            "match_on": ["method", "path"],
            "decode_compressed_response": True,
            "before_record_request": self._hide_sensitive_data,
        }

    def _product_data(self):
        data = super()._product_data()
        data.update(
            {
                "weight": 1.2,
                "hs_code_id": self.env.ref("product_harmonized_system.84715000").id,
                "origin_country_id": self.env.ref("base.tw").id,
            }
        )
        return data

    def _create_order_picking(self):
        # both must exist before the picking is validated, since validating it
        # asks La Poste for the label right away
        # french carrier sender need to be from France, and roulier validates
        # the sender address locally before calling the web service
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
                # fill real account information if you want to re-generate cassette
                "account": "dummy",
                "password": "dummy",
            }
        )
        self._get_carrier().carrier_account_id = self.account
        return super()._create_order_picking()

    def _get_carrier(self):
        return self.env.ref("delivery_roulier_laposte_fr.delivery_carrier_COM")

    def _partner_data(self):
        data = super()._partner_data()
        data.update(
            {
                "street": "RUE THERNISIEN LEUGINER",
                "zip": "97120",
                "city": "SAINT-CLAUDE",
                "country_id": self.env.ref("base.gp").id,
            }
        )
        return data
