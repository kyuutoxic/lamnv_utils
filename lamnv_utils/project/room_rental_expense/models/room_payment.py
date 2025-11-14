# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RoomPayment(models.Model):
    _name = 'room.payment'
    _description = 'Thanh Toán Phòng Trọ'
    _order = 'payment_date desc'

    invoice_id = fields.Many2one(
        'room.invoice',
        string='Hóa Đơn',
        required=True,
        ondelete='cascade'
    )
    room_id = fields.Many2one(
        'rental.room',
        string='Phòng Trọ',
        related='invoice_id.room_id',
        readonly=True
    )
    payment_date = fields.Date(
        string='Ngày Thanh Toán',
        required=True
    )
    payment_amount = fields.Float(
        string='Số Tiền Thanh Toán (VND)',
        required=True
    )
    payment_method = fields.Selection(
        [('cash', 'Tiền Mặt'),
         ('bank_transfer', 'Chuyển Khoản'),
         ('e_wallet', 'Ví Điện Tử'),
         ('check', 'Séc'),
         ('other', 'Khác')],
        string='Phương Thức Thanh Toán'
    )
    transaction_id = fields.Char(string='Mã Giao Dịch')
    payment_proof_image = fields.Binary(
        string='Ảnh Chứng Minh Thanh Toán',
        attachment=True
    )
    notes = fields.Text(string='Ghi Chú')

    @api.onchange('payment_amount')
    def _onchange_payment_amount(self):
        if self.invoice_id:
            remaining = (
                self.invoice_id.total_amount -
                self.invoice_id.paid_amount
            )
            if self.payment_amount > remaining:
                self.payment_amount = remaining
