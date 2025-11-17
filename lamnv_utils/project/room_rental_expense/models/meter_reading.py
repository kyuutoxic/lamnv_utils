# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MeterReading(models.Model):
    _name = 'meter.reading'
    _description = 'Chỉ Số Công Tơ'
    _rec_name = 'name'
    _order = 'reading_date desc'

    name = fields.Char(
        string='Tên',
        compute='_compute_name',
        store=True
    )
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
    electric_replacement_last = fields.Float(
        string='Chỉ Số Cuối Công Tơ Cũ (kWh)',
        help='Nhập chỉ số cuối cùng trước khi thay công tơ'
    )
    electric_usage = fields.Float(
        string='Lượng Điện Sử Dụng (kWh)',
        compute='_compute_electric_usage',
        inverse='_inverse_electric_usage',
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
    electric_usage_manual_override = fields.Boolean(
        string='Nhập Tay Điện Sử Dụng',
        default=False
    )
    electric_usage_manual_value = fields.Float(
        string='Điện Sử Dụng (Nhập Tay)'
    )

    # Nước
    water_previous = fields.Float(
        string='Số Nước Tháng Trước (m³)'
    )
    water_current = fields.Float(
        string='Số Nước Hiện Tại (m³)',
        required=True
    )
    water_replacement_last = fields.Float(
        string='Chỉ Số Cuối Công Tơ Cũ (m³)',
        help='Nhập chỉ số cuối cùng của công tơ nước trước khi thay'
    )
    water_usage = fields.Float(
        string='Lượng Nước Sử Dụng (m³)',
        compute='_compute_water_usage',
        inverse='_inverse_water_usage',
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
    water_usage_manual_override = fields.Boolean(
        string='Nhập Tay Nước Sử Dụng',
        default=False
    )
    water_usage_manual_value = fields.Float(
        string='Nước Sử Dụng (Nhập Tay)'
    )

    invoice_id = fields.Many2one(
        'room.invoice',
        string='Hóa Đơn',
        copy=False,
        ondelete='set null'
    )
    notes = fields.Text(string='Ghi Chú')

    @api.depends('room_id', 'reading_month', 'reading_date')
    def _compute_name(self):
        for reading in self:
            parts = []
            if reading.room_id:
                parts.append(reading.room_id.name)
            if reading.reading_month:
                parts.append(reading.reading_month)
            elif reading.reading_date:
                parts.append(reading.reading_date.strftime('%d/%m/%Y'))
            reading.name = ' - '.join(parts) if parts else 'Chỉ Số'

    @api.depends('reading_date')
    def _compute_reading_month(self):
        for reading in self:
            if reading.reading_date:
                reading.reading_month = reading.reading_date.strftime(
                    '%m/%Y'
                )

    @api.depends('electric_current', 'electric_previous',
                 'electric_meter_replaced', 'electric_replacement_last',
                 'electric_usage_manual_override',
                 'electric_usage_manual_value')
    def _compute_electric_usage(self):
        for reading in self:
            if reading.electric_usage_manual_override:
                reading.electric_usage = reading.electric_usage_manual_value
            else:
                reading.electric_usage = reading._get_auto_electric_usage()

    def _inverse_electric_usage(self):
        for reading in self:
            if not reading.electric_usage_manual_override:
                reading.electric_usage_manual_override = True
            reading.electric_usage_manual_value = reading.electric_usage

    def _get_auto_electric_usage(self):
        self.ensure_one()
        previous = self.electric_previous or 0.0
        current = self.electric_current or 0.0
        if self.electric_meter_replaced:
            old_delta = 0.0
            if self.electric_replacement_last:
                old_delta = max(self.electric_replacement_last - previous, 0.0)
            return old_delta + current
        return current - previous

    @api.depends('water_current', 'water_previous',
                 'water_meter_replaced', 'water_replacement_last',
                 'water_usage_manual_override',
                 'water_usage_manual_value')
    def _compute_water_usage(self):
        for reading in self:
            if reading.water_usage_manual_override:
                reading.water_usage = reading.water_usage_manual_value
            else:
                reading.water_usage = reading._get_auto_water_usage()

    def _inverse_water_usage(self):
        for reading in self:
            if not reading.water_usage_manual_override:
                reading.water_usage_manual_override = True
            reading.water_usage_manual_value = reading.water_usage

    def _get_auto_water_usage(self):
        self.ensure_one()
        previous = self.water_previous or 0.0
        current = self.water_current or 0.0
        if self.water_meter_replaced:
            old_delta = 0.0
            if self.water_replacement_last:
                old_delta = max(self.water_replacement_last - previous, 0.0)
            return old_delta + current
        return current - previous

    @api.constrains('electric_current', 'electric_previous',
                    'electric_meter_replaced')
    def _check_electric_reading(self):
        for reading in self:
            if (not reading.electric_meter_replaced and
                    reading.electric_previous is not None and
                    reading.electric_current < reading.electric_previous):
                raise ValidationError(
                    'Số điện hiện tại không thể nhỏ hơn số tháng trước! '
                    'Hãy tick "Đã thay công tơ?" '
                    'nếu công tơ đã được thay.'
                )

    @api.constrains('water_current', 'water_previous',
                    'water_meter_replaced')
    def _check_water_reading(self):
        for reading in self:
            if (not reading.water_meter_replaced and
                    reading.water_previous is not None and
                    reading.water_current < reading.water_previous):
                raise ValidationError(
                    'Số nước hiện tại không thể nhỏ hơn số tháng trước! '
                    'Hãy tick "Đã thay công tơ?" '
                    'nếu công tơ đã được thay.'
                )

    @api.onchange('electric_meter_replaced', 'electric_current',
                  'electric_previous')
    def _onchange_electric_inputs(self):
        for reading in self:
            if (reading.electric_usage_manual_override and
                    not reading.env.context.get('keep_manual_electric')):
                continue
            if not reading.electric_usage_manual_override:
                reading.electric_usage = reading._get_auto_electric_usage()

    @api.onchange('electric_usage_manual_override')
    def _onchange_electric_usage_override(self):
        for reading in self:
            if not reading.electric_usage_manual_override:
                reading.electric_usage_manual_value = 0.0
                reading.electric_usage = reading._get_auto_electric_usage()

    @api.onchange('water_meter_replaced', 'water_current', 'water_previous')
    def _onchange_water_inputs(self):
        for reading in self:
            if (reading.water_usage_manual_override and
                    not reading.env.context.get('keep_manual_water')):
                continue
            if not reading.water_usage_manual_override:
                reading.water_usage = reading._get_auto_water_usage()

    @api.onchange('water_usage_manual_override')
    def _onchange_water_usage_override(self):
        for reading in self:
            if not reading.water_usage_manual_override:
                reading.water_usage_manual_value = 0.0
                reading.water_usage = reading._get_auto_water_usage()

    @api.onchange('room_id', 'reading_date')
    def _onchange_room_or_date(self):
        for reading in self:
            if not reading.room_id or not reading.reading_date:
                continue
            previous_reading = self._get_previous_reading(
                reading.room_id,
                reading.reading_date,
                exclude_id=reading.id
            )
            if previous_reading:
                reading.electric_previous = previous_reading.electric_current
                reading.water_previous = previous_reading.water_current
            else:
                reading.electric_previous = 0.0
                reading.water_previous = 0.0

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        room_id = self.env.context.get('default_room_id')
        reading_date = defaults.get('reading_date') or fields.Date.context_today(self)
        if room_id and ('electric_previous' in fields_list or
                        'water_previous' in fields_list):
            if isinstance(reading_date, str):
                reading_date = fields.Date.from_string(reading_date)
            room = self.env['rental.room'].browse(room_id)
            previous = self._get_previous_reading(room, reading_date)
            if previous:
                defaults.setdefault('electric_previous', previous.electric_current)
                defaults.setdefault('water_previous', previous.water_current)
            else:
                defaults.setdefault('electric_previous', 0.0)
                defaults.setdefault('water_previous', 0.0)
        return defaults

    @api.model
    def _get_previous_reading(self, room, reading_date, exclude_id=None):
        if not room:
            return self.env['meter.reading']
        readings = room.meter_reading_ids
        if exclude_id:
            readings = readings.filtered(lambda r: r.id != exclude_id)
        if reading_date:
            readings = readings.filtered(
                lambda r: r.reading_date and r.reading_date < reading_date
            )
        if not readings:
            return readings
        sorted_readings = readings.sorted(
            key=lambda r: r.reading_date or fields.Date.from_string('1970-01-01'),
            reverse=True
        )
        return sorted_readings[0]

    @api.constrains('invoice_id', 'room_id')
    def _check_invoice_room(self):
        for reading in self:
            if (reading.invoice_id and
                    reading.invoice_id.room_id != reading.room_id):
                raise ValidationError(
                    'Hóa đơn phải thuộc cùng phòng với chỉ số công tơ.'
                )

    def unlink(self):
        linked = self.filtered('invoice_id')
        if linked:
            raise ValidationError(
                'Không thể xóa chỉ số công tơ đã được gắn với hóa đơn. '
                'Hãy xóa hoặc điều chỉnh hóa đơn trước.'
            )
        return super().unlink()
