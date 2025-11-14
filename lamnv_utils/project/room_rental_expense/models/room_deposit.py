# -*- coding: utf-8 -*-
from odoo import models, fields


class RoomDeposit(models.Model):
    _name = 'room.deposit'
    _description = 'Tiền Cọc Phòng Trọ'
    _order = 'deposit_date desc'

    room_id = fields.Many2one(
        'rental.room',
        string='Phòng Trọ',
        required=True,
        ondelete='cascade'
    )
    deposit_amount = fields.Float(
        string='Số Tiền Cọc (VND)',
        required=True
    )
    deposit_date = fields.Date(
        string='Ngày Nộp Tiền Cọc',
        required=True
    )
    expected_return_date = fields.Date(
        string='Dự Kiến Hoàn Tiền'
    )
    status = fields.Selection(
        [('pending', 'Chờ Xác Nhận'),
         ('confirmed', 'Đã Xác Nhận'),
         ('partial_return', 'Hoàn Một Phần'),
         ('fully_returned', 'Đã Hoàn Đủ'),
         ('disputed', 'Có Tranh Chấp')],
        string='Trạng Thái',
        default='pending'
    )
    return_date = fields.Date(string='Ngày Hoàn Tiền')
    return_amount = fields.Float(
        string='Số Tiền Hoàn (VND)'
    )
    notes = fields.Text(string='Ghi Chú')
    receipt_image = fields.Binary(
        string='Ảnh Biên Lai Nộp Cọc',
        attachment=True
    )
