# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RoomHistory(models.Model):
    _name = 'room.history'
    _description = 'Lịch Sử Phòng Trọ'
    _order = 'to_date desc'

    name = fields.Char(
        string='Tên/Địa Chỉ Phòng',
        required=True
    )
    room_id = fields.Many2one(
        'rental.room',
        string='Phòng Trọ Liên Quan'
    )
    from_date = fields.Date(string='Từ Ngày')
    to_date = fields.Date(string='Đến Ngày')
    landlord_name = fields.Char(string='Tên Chủ Phòng')
    landlord_phone = fields.Char(string='Số Điện Thoại')
    avg_rent = fields.Float(string='Giá Thuê TB/Tháng (VND)')
    notes = fields.Text(string='Nhận Xét')
    total_spent = fields.Float(
        string='Tổng Chi Phí (VND)',
        compute='_compute_total_spent',
        store=False
    )

    @api.depends('room_id')
    def _compute_total_spent(self):
        for record in self:
            if record.room_id:
                invoices_total = sum(record.room_id.invoice_ids.mapped(
                    'total_amount'
                ))
                expenses_total = sum(record.room_id.expense_ids.mapped(
                    'amount'
                ))
                record.total_spent = invoices_total + expenses_total
            else:
                record.total_spent = 0.0
