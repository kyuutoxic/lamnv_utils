# -*- coding: utf-8 -*-
from odoo import models, fields


class RoomExpense(models.Model):
    _name = 'room.expense'
    _description = 'Chi Phí Phòng Trọ'
    _order = 'expense_date desc'

    room_id = fields.Many2one(
        'rental.room',
        string='Phòng Trọ',
        required=True,
        ondelete='cascade'
    )
    expense_date = fields.Date(
        string='Ngày Chi Phí',
        required=True
    )
    category = fields.Selection(
        [('repair', 'Sửa Chữa'),
         ('cleaning', 'Vệ Sinh'),
         ('supplies', 'Mua Đồ'),
         ('maintenance', 'Bảo Trì'),
         ('damage_fee', 'Phí Hư Hỏng'),
         ('other', 'Khác')],
        string='Danh Mục',
        required=True
    )
    description = fields.Text(
        string='Mô Tả Chi Tiết',
        required=True
    )
    amount = fields.Float(
        string='Số Tiền (VND)',
        required=True
    )
    notes = fields.Text(string='Ghi Chú')
    receipt_image = fields.Binary(
        string='Ảnh Hóa Đơn/Biên Lai',
        attachment=True
    )
