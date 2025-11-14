# -*- coding: utf-8 -*-
from odoo import models, fields


class RoomIssue(models.Model):
    _name = 'room.issue'
    _description = 'Sự Cố Phòng Trọ'
    _order = 'issue_date desc'

    room_id = fields.Many2one(
        'rental.room',
        string='Phòng Trọ',
        required=True,
        ondelete='cascade'
    )
    issue_date = fields.Date(
        string='Ngày Phát Hiện Sự Cố',
        required=True
    )
    category = fields.Selection(
        [('water_leak', 'Rò Nước'),
         ('electric_problem', 'Vấn Đề Điện'),
         ('broken_furniture', 'Đồ Đạc Hỏng'),
         ('pest', 'Sâu Bọ'),
         ('noise', 'Ồn Ào'),
         ('temperature', 'Lạnh/Nóng'),
         ('other', 'Khác')],
        string='Loại Sự Cố',
        required=True
    )
    description = fields.Text(
        string='Mô Tả Chi Tiết',
        required=True
    )
    severity = fields.Selection(
        [('low', 'Thấp'),
         ('medium', 'Trung Bình'),
         ('high', 'Cao'),
         ('critical', 'Rất Nghiêm Trọng')],
        string='Mức Độ',
        default='medium'
    )
    status = fields.Selection(
        [('reported', 'Đã Báo Cáo'),
         ('acknowledged', 'Chủ Trọ Xác Nhận'),
         ('in_progress', 'Đang Xử Lý'),
         ('resolved', 'Đã Khắc Phục')],
        string='Trạng Thái',
        default='reported'
    )
    reported_date = fields.Date(string='Ngày Báo Cáo')
    resolved_date = fields.Date(string='Ngày Khắc Phục')
    issue_image = fields.Binary(
        string='Ảnh Sự Cố',
        attachment=True
    )
    notes = fields.Text(string='Ghi Chú')
