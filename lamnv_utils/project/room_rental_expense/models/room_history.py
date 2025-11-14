# -*- coding: utf-8 -*-
from odoo import models, fields


class RoomHistory(models.Model):
    _name = 'room.history'
    _description = 'Lịch Sử Phòng Trọ'
    _order = 'to_date desc'

    name = fields.Char(
        string='Tên/Địa Chỉ Phòng',
        required=True
    )
    from_date = fields.Date(string='Từ Ngày')
    to_date = fields.Date(string='Đến Ngày')
    landlord_name = fields.Char(string='Tên Chủ Phòng')
    landlord_phone = fields.Char(string='Số Điện Thoại')
    avg_rent = fields.Float(string='Giá Thuê TB/Tháng (VND)')
    notes = fields.Text(string='Nhận Xét')
