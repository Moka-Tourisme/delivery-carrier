# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResPartnerWithdrawal(models.Model):
    _inherit = 'res.partner'
    @api.model
    def _withdrawal_search_or_create(self, data):
        print("data create", data)
        partner = self.search([
            ('id', 'child_of', self.commercial_partner_id.ids),
            ('city', '=', data['city']),
            ('street', '=', data['street']),
            ('zip', '=', data['zip']),
        ])
        if not partner:
            partner = self.create({
                'name': data['name'],
                'street': data['street'],
                'street2': data['street2'],
                'zip': data['zip'],
                'city': data['city'],
                'country_id': self.env['res.country'].search([('id', '=', data['country_id'])]).id,
                'type': 'delivery',
                'parent_id': self.id,
            })
        else:
            partner.street2 = data['street2']
        return partner
