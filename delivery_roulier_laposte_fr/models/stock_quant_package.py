#  @author Raphael Reverdy <raphael.reverdy@akretion.com>
#          David BEAL <david.beal@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import io
import logging

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from roulier import roulier
from roulier.exception import InvalidApiInput

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


CUSTOMS_MAP = {
    "gift": 1,
    "sample": 2,
    "commercial": 3,
    "document": 4,
    "other": 5,
    "return": 6,
}


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    def _call_roulier_api(self, picking):
        # Colissimo has no test service: roulier would send the request to the
        # production web service whatever "isTest" says. The test environment
        # of the carrier is therefore simulated locally.
        if (
            picking.delivery_type == "laposte_fr"
            and not picking.carrier_id.prod_environment
        ):
            return self._laposte_fr_simulate_response(picking)
        return super()._call_roulier_api(picking)

    def _laposte_fr_simulate_response(self, picking):
        """Answer like roulier would, without any call to Colissimo."""
        account = picking._get_account(self)
        label_format = picking._get_label_format(account)
        self.write({"carrier_id": picking.carrier_id.id})
        self._laposte_fr_check_request(picking, account)
        parcels = []
        for index, package in enumerate(self, start=1):
            number = "TEST-%s-%s" % (picking.id, index)
            parcels.append(
                {
                    "id": index,
                    "reference": package.name,
                    "tracking": {"number": number, "url": "", "partner": ""},
                    "label": {
                        "data": base64.b64encode(
                            self._laposte_fr_simulated_label(
                                label_format, number, package.name
                            )
                        ),
                        "name": "label_%s" % index,
                        "type": label_format,
                    },
                }
            )
        picking.message_post(
            body=_(
                "Test environment: no request was sent to Colissimo, the label and "
                "the tracking number are simulated. Do not stick this label on a "
                "parcel."
            )
        )
        return {"parcels": parcels, "annexes": []}

    def _laposte_fr_check_request(self, picking, account):
        """Build and validate the request, as in production, but do not send it."""
        payload = {
            "auth": picking._get_auth(account, package=self),
            "from_address": picking._get_from_address(package=self),
            "to_address": picking._get_to_address(package=self),
            "service": picking._get_service(account, package=self),
            "parcels": self._get_parcels(picking),
        }
        payload = self._before_call(picking, payload)
        action = roulier.factory.get("laposte_fr", "get_label")
        try:
            for parcel in payload["parcels"]:
                action.encoder(action).encode(dict(payload, parcels=[parcel]))
        except InvalidApiInput as e:
            raise UserError(self._invalid_api_input_handling(payload, e)) from e

    @api.model
    def _laposte_fr_simulated_label(self, label_format, number, reference):
        """Return the bytes of a label mentioning that it is a test."""
        lines = ["TEST - COLISSIMO", number, reference]
        if label_format.startswith("ZPL"):
            fields = "".join(
                "^FO40,%d^A0N,40,40^FD%s^FS" % (40 + 60 * i, line)
                for i, line in enumerate(lines)
            )
            return ("^XA%s^XZ" % fields).encode()
        if label_format.startswith("DPL"):
            fields = "".join(
                "1911A0800%04d0040%s\r\n" % (40 + 60 * i, line)
                for i, line in enumerate(lines)
            )
            return ("\x02L\r\nD11\r\n%sE\r\n" % fields).encode()
        stream = io.BytesIO()
        size = A4 if "A4" in label_format else (100 * mm, 150 * mm)
        pdf = canvas.Canvas(stream, pagesize=size)
        pdf.setFont("Helvetica-Bold", 18)
        height = size[1]
        for i, line in enumerate(lines):
            pdf.drawString(10 * mm, height - (20 + 12 * i) * mm, line)
        pdf.save()
        return stream.getvalue()

    def _laposte_fr_get_parcel(self, picking):
        vals = self._roulier_get_parcel(picking)

        def calc_package_price():
            return sum(
                op.product_id.lst_price * op.quantity
                for op in self._get_move_lines(picking)
            )

        vals["totalAmount"] = "%.f" % (  # truncate to string
            calc_package_price() * 100  # totalAmount is in centimes
        )
        vals.update(picking._laposte_fr_get_options(self))
        if vals.get("COD"):
            vals["codAmount"] = self._get_cash_on_delivery(picking)

        if self._should_include_customs(picking):
            vals["customs"] = self._get_customs(picking)
        return vals

    def _laposte_fr_get_customs(self, picking):
        """see _roulier_get_customs() docstring"""
        customs = self._roulier_get_customs(picking)
        customs["category"] = CUSTOMS_MAP.get(picking.customs_category)
        return customs

    def _laposte_fr_should_include_customs(self, picking):
        """Choose if customs infos should be included in the WS call.

        Return bool
        """
        # Customs declaration (cn23) is needed when :
        # dest is not in UE
        # dest is attached territory (like Groenland, Canaries)
        # dest is is Outre-mer
        #
        # If origin is not France metropole, this implementation may be wrong.
        # see https://boutique.laposte.fr/_ui/doc/formalites_douane.pdf
        europe_group = self.env.ref("base.europe")
        eu_country_ids = europe_group.country_ids.ids
        sender_is_intrastat = picking._get_sender(self).country_id.id in eu_country_ids
        receiver_is_intrastat = (
            picking._get_receiver(self).country_id.id in eu_country_ids
        )
        if sender_is_intrastat:
            if receiver_is_intrastat:
                return False  # national or within UE
            else:
                return True  # internationnal shipping
        else:
            _logger.warning("Customs may be not needed for picking %s" % picking.id)
            return True

    @api.model
    def _laposte_fr_invalid_api_input_handling(self, payload, exception):
        payload["auth"]["password"] = "****"
        response = str(exception)
        suffix = (
            "\nSignification des clés dans le contexte Odoo:\n"
            "- 'to_address' : adresse du destinataire (votre client)\n"
            "- 'from_address' : adresse de l'expéditeur (vous)"
        )
        message = "Données transmises:\n{}\n\nExceptions levées{}\n{}".format(
            payload,
            response,
            suffix,
        )
        return message

    def _laposte_fr_carrier_error_handling(self, payload, exception):
        response = exception.response
        request = response.request.body.decode("utf-8")

        if self._uid > 2:
            # rm pwd from dict and xml
            payload["auth"]["password"] = "****"
            request = "{}<password>****{}".format(
                request[: request.index("<password>")],
                request[request.index("</password>") :],
            )

        # Webservice error
        # on contextualise les réponses ws aux objets Odoo
        map_responses = {
            30204: "La 2eme ligne d'adresse du client partenaire "
            "est vide ou invalide",
            30221: "Le telephone du client ne doit comporter que des "
            "chiffres ou le symbole +: convertissez tous vos N° de "
            "telephone au format standard a partir du menu suivant:\n"
            "Configuration > Technique > Telephonie > Reformate "
            "les numeros de telephone ",
            30100: "La seconde ligne d'adresse de l'expéditeur est "
            "vide ou invalide.",
        }

        def format_one_exception(message, map_responses):
            param_message = {
                "ws_exception": "%s\n" % message["message"],
                "resolution": "",
            }
            if message and message.get("id") in map_responses.keys():
                param_message["resolution"] = _(
                    "Résolution\n-------------\n%s" % map_responses[message["id"]]
                )
            return _(
                "Réponse de Laposte:\n"
                "%(ws_exception)s\n%(resolution)s" % param_message
            )

        parts = []
        for messages in exception.args:
            for message in messages:
                parts.append(format_one_exception(message, map_responses))

        ret_mess = _(
            "Incident\n-----------\n%(displ_exception_message)s\n"
            "Données transmises:\n"
            "-----------------------------\n%(displ_data_transmitted)s"
        ) % {
            "displ_exception_message": "\n".join(parts),
            "displ_data_transmitted": request,
        }
        return ret_mess

    def _laposte_fr_get_tracking_link(self):
        return (
            "https://www.colissimo.fr/"
            "portail_colissimo/suivreResultat.do?"
            "parcelnumber=%s" % self.parcel_tracking
        )
