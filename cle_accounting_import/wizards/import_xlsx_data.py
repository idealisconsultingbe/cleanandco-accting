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

from odoo import api, fields, models, _
import xlrd
import tempfile
import binascii
from _datetime import datetime


def float_hour_to_time(fh):
    h, r = divmod(fh, 1)
    m, r = divmod(r * 60, 1)
    return (
        int(h),
        int(m),
        int(r * 60),
    )


def get_partner_name(name):
    """
    This method return a date or a name depending on the given name.
    If name is a float (e.g 43488), it will return the date 1/18/19
    Otherwise, return the regular name
    """
    try:
        float(name)
        partner_name = datetime(*xlrd.xldate_as_tuple(name, 0))
    except:
        partner_name = name

    return partner_name


def get_product_default_code(code):
    try:
        product_code = int(code)
    except:
        product_code = code

    return product_code


class ImportJournalEntriesXlsxDataWizard(models.TransientModel):
    _name = 'import.journal.entries.xlsx.data.wizard'
    _description = 'Import journal entries xlsx data Wizard'

    xlsx_file = fields.Binary(string="Your xlsx file")

    def import_journal_entries_xlsx_data(self):
        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.xlsx_file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)

        # Avoid to create before import is finished
        self._cr.autocommit(False)
        try:
            for i in range(1, sheet.nrows):
                row = sheet.row_values(i)

                partner = self.env['res.partner'].search([('ref', '=', row[0])])
                if not partner:
                    print("Creating res.partner...")
                    partner = self.env['res.partner'].create({
                        'ref': row[0],
                        'name': get_partner_name(row[1]),
                        'vat': row[3],
                        'customer_rank': 1,
                    })
                else:
                    partner.write({'vat': row[3]})

                product_default_code = get_product_default_code(row[9])
                product = self.env['product.product'].search(
                    [('default_code', '=', product_default_code), ('name', '=', row[10])])
                if not product:
                    print("Creating product...")
                    product = self.env['product.product'].create({
                        'default_code': product_default_code,
                        'name': row[10],
                    })

                print("Creating fiscal position")
                fiscal_position = self.env['account.fiscal.position'].search([('name', '=', row[7])])
                if not fiscal_position:
                    fiscal_position = self.env['account.fiscal.position'].create({
                        'name': row[7]
                    })

                move = self.env['account.move'].search([('ref', '=', row[4])])
                if not move:
                    print("Creating Move...")
                    move = self.env['account.move'].create({
                        'partner_id': partner.id,
                        'ref': row[4],
                        'document_name': row[5],
                        'invoice_date': datetime(*xlrd.xldate_as_tuple(row[6], 0)),
                        'fiscal_position_id': fiscal_position.id,
                        'invoice_payment_ref': row[8],
                    })

                taxes = self.env['account.tax'].search([
                    ('name', '=', str(float(row[14])) + '%'), ('amount', '=', float(row[14]))
                ])
                if not taxes:
                    print("Creating taxes...")
                    taxes = self.env['account.tax'].create({
                        'name': str(float(row[14])) + '%',
                        'amount': float(row[14]),
                        'description': row[14] + '%'
                    })

                client_account = partner.property_account_receivable_id.id
                l_acc_client = self.env['account.move.line'].search([('account_id', '=', client_account), ('move_id', '=', move.id)])
                l_acc_client_debit = l_acc_client.debit
                l_acc_client.unlink()

                credit = row[15] if row[15] > 0 else 0
                debit = l_acc_client_debit + (row[15] if row[15] > 0 else 0)
                print("Creating move line...")
                self.env['account.move.line'].create([{
                    'account_id': product.categ_id.property_account_income_categ_id.id,
                    'move_id': move.id,
                    'product_id': product.id,
                    'price_unit': row[11],
                    'quantity': row[12],
                    'tax_ids': taxes.ids,
                    'price_subtotal': row[15],
                    'credit': credit,
                }, {
                    'account_id': client_account,
                    'move_id': move.id,
                    'debit': debit,
                }])

                print("Posting move...")
                move.post()

            self._cr.commit()

        except Exception as e:
            print(e)
            self._cr.rollback()


class ImportProductXlsxDataWizard(models.TransientModel):
    _name = 'import.products.xlsx.data.wizard'
    _description = 'Import products xlsx data Wizard'

    xlsx_file = fields.Binary(string="Your xlsx file")

    def import_products_xlsx_data(self):
        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.xlsx_file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        # Avoid to create before import is finished
        self._cr.autocommit(False)
        try:
            for i in range(1, sheet.nrows):
                row = sheet.row_values(i)

                product = self.env['product.product'].search([('default_code', '=', row[0])])
                if not product:
                    category_name = row[6]
                    sub_category_name = row[11]
                    category = self.env['product.category'].search([('name', '=', category_name)])
                    sub_category = self.env['product.category'].search([('name', '=', sub_category_name)])
                    if not category and category_name != "":
                        category = self.env['product.category'].create({'name': category_name})
                    if not sub_category and sub_category_name != "":
                        sub_category = self.env['product.category'].create({
                            'name': sub_category_name,
                            'parent_id': category.id if category else False
                        })

                    taxes = self.env['account.tax'].search([
                        ('name', '=', str(float(row[10])) + '%'), ('amount', '=', float(row[10]))
                    ])
                    if not taxes:
                        taxes = self.env['account.tax'].create({
                            'name': str(float(row[10])) + '%',
                            'amount': float(row[10]),
                            'description': row[10] + '%'
                        })

                    categ_id = category.id if category else sub_category.id if sub_category else self.env['product.category'].create({'name': 'Nil'}).id

                    self.env['product.product'].create({
                        'default_code': get_product_default_code(row[0]),
                        'name': row[1],
                        'categ_id': categ_id,
                        'list_price': row[7],
                        'taxes_id': taxes.ids,
                        'supplier_taxes_id': taxes.ids,
                    })

            self._cr.commit()

        except Exception as e:
            print(e)
            self._cr.rollback()
