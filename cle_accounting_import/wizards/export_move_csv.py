# -*- coding: utf-8 -*-
##############################################################################
#
# This module is developed by Idealis Consulting SPRL
# Copyright (C) 2019 Idealis Consulting SPRL (<https://idealisconsulting.com>).
# All Rights Reserved
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, models, fields, _
from odoo.tools import pycompat
import base64
import io


class CleExportMoveCsv(models.TransientModel):
    _name = 'cle.export.move.csv'

    @api.model
    def default_file(self):
        active_ids = self.env.context.get('active_ids', False)

        if active_ids:
            moves = self.env['account.move'].browse(active_ids)
            csvfile = io.BytesIO()
            writer = pycompat.csv_writer(csvfile, delimiter=';')
            writer.writerow([
                ' Réf client ',
                ' Nom(name) ',
                ' Journal(jnl) ',
                ' Document(docnr) ',
                ' Date(date) ',
                ' Echéance(dued) ',
                ' Période ',
                ' Mt.devise ',
                ' Code ',
                ' Débit(debN) ',
                ' Crédit(credN) ',
                ' Lettrage(match) ',
                ' Commentaire(comment) '
            ])

            for move in moves:
                for l in move.line_ids:
                    writer.writerow([
                        move.partner_id.ref or '',
                        move.partner_id.ref or '',
                        move.journal_id.name,
                        move.document_name,
                        move.date,
                        move.invoice_date_due or '',
                        move.fiscal_position_id.name,
                        move.amount_total,
                        '',
                        l.debit,
                        l.credit,
                        l.full_reconcile_id.name,
                        move.name,
                    ])

            csvvalue = csvfile.getvalue()
            csvfile.close()
            return base64.encodebytes(csvvalue)

        return False

    def action_generate(self):
        self.state = 'step2'
        if '.csv' not in self.filename:
            self.filename += '.csv'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cle.export.move.csv',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
             }

    def action_back(self):
        self.state = 'step1'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cle.export.move.csv',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    file = fields.Binary('File', default=default_file)
    filename = fields.Char('File Name', default='move.csv')
    state = fields.Selection([
        ('step1', 'Step 1'),
        ('step2', 'Step 2'),
    ], string='Step', default="step1", readonly=True)
