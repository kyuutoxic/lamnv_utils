# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MeterReading(models.Model):
    _name = 'meter.reading'
    _description = 'Chỉ Số Công Tơ'
    _order = 'reading_date desc'

    room_id = fields.Many2one(
        'rental.room',
        string='Phòng Trọ',
        required=True,
        ondelete='cascade'
    )
    reading_date = fields.Date(
        string='Ngày Ghi Chỉ Số',
        required=True
    )
    reading_month = fields.Char(
        string='Tháng Ghi Chỉ Số',
        compute='_compute_reading_month',
        store=True
    )

    # Điện
    electric_previous = fields.Float(
        string='Số Điện Tháng Trước (kWh)'
    )
    electric_current = fields.Float(
        string='Số Điện Hiện Tại (kWh)',
        required=True
    )
    electric_usage = fields.Float(
        string='Lượng Điện Sử Dụng (kWh)',
        compute='_compute_electric_usage',
        store=True
    )
    electric_meter_replaced = fields.Boolean(
        string='Đã Thay Công Tơ Điện?',
        default=False
    )
    electric_image = fields.Binary(
        string='Ảnh Công Tơ Điện',
        attachment=True
    )
    electric_replacement_note = fields.Text(
        string='Ghi Chú Thay Công Tơ Điện'
    )

    # Nước
    water_previous = fields.Float(
        string='Số Nước Tháng Trước (m³)'
    )
    water_current = fields.Float(
        string='Số Nước Hiện Tại (m³)',
        required=True
    )
    water_usage = fields.Float(
        string='Lượng Nước Sử Dụng (m³)',
        compute='_compute_water_usage',
        store=True
    )
    water_meter_replaced = fields.Boolean(
        string='Đã Thay Công Tơ Nước?',
        default=False
    )
    water_image = fields.Binary(
        string='Ảnh Công Tơ Nước',
        attachment=True
    )
    water_replacement_note = fields.Text(
        string='Ghi Chú Thay Công Tơ Nước'
    )

    notes = fields.Text(string='Ghi Chú')

    @api.depends('reading_date')
    def _compute_reading_month(self):
        for reading in self:
            if reading.reading_date:
                reading.reading_month = reading.reading_date.strftime(
                    '%m/%Y'
                )

    @api.depends('electric_current', 'electric_previous',
                 'electric_meter_replaced')
    def _compute_electric_usage(self):
        for reading in self:
            if reading.electric_meter_replaced:
                reading.electric_usage = (
                    (99999 - reading.electric_previous) +
                    reading.electric_current
                )
            else:
                reading.electric_usage = (
                    reading.electric_current -
                    reading.electric_previous
                )

    @api.depends('water_current', 'water_previous',
                 'water_meter_replaced')
    def _compute_water_usage(self):
        for reading in self:
            if reading.water_meter_replaced:
                reading.water_usage = (
                    (99999 - reading.water_previous) +
                    reading.water_current
                )
            else:
                reading.water_usage = (
                    reading.water_current - reading.water_previous
                )

    @api.constrains('electric_current', 'electric_previous',
                    'electric_meter_replaced')
    def _check_electric_reading(self):
        for reading in self:
            if (not reading.electric_meter_replaced and
                    reading.electric_current < reading.electric_previous):
                raise ValueError(
                    'Số điện hiện tại không thể nhỏ hơn số tháng trước! '
                    'Hãy tick "Đã thay công tơ?" '
                    'nếu công tơ đã được thay.'
                )

    @api.constrains('water_current', 'water_previous',
                    'water_meter_replaced')
    def _check_water_reading(self):
        for reading in self:
            if (not reading.water_meter_replaced and
                    reading.water_current < reading.water_previous):
                raise ValueError(
                    'Số nước hiện tại không thể nhỏ hơn số tháng trước! '
                    'Hãy tick "Đã thay công tơ?" '
                    'nếu công tơ đã được thay.'
                )
