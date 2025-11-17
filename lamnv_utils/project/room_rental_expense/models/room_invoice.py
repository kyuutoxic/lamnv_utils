# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RoomInvoice(models.Model):
    _name = 'room.invoice'
    _description = 'Hóa Đơn Phòng Trọ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'invoice_number'
    _order = 'invoice_month desc'

    room_id = fields.Many2one(
        'rental.room',
        string='Phòng Trọ',
        required=True,
        ondelete='cascade'
    )
    invoice_number = fields.Char(
        string='Số Hóa Đơn',
        readonly=True,
        copy=False
    )
    invoice_month = fields.Char(
        string='Tháng Hóa Đơn (MM/YYYY)',
        required=True
    )
    invoice_date = fields.Date(string='Ngày Lập Hóa Đơn')
    due_date = fields.Date(string='Hạn Thanh Toán')
    status = fields.Selection(
        [('draft', 'Nháp'),
         ('pending', 'Chờ Thanh Toán'),
         ('paid', 'Đã Thanh Toán'),
         ('partially_paid', 'Thanh Toán Một Phần'),
         ('overdue', 'Quá Hạn'),
         ('canceled', 'Hủy')],
        string='Trạng Thái',
        default='draft'
    )

    # Chi tiết hóa đơn
    rent_amount = fields.Float(
        string='Tiền Thuê (VND)',
        required=True
    )
    electric_price_per_unit = fields.Float(
        string='Giá Điện (VND/kWh)'
    )
    electric_usage = fields.Float(string='Lượng Điện (kWh)')
    electric_amount = fields.Float(
        string='Tiền Điện (VND)',
        compute='_compute_electric_amount',
        store=True
    )

    water_price_per_unit = fields.Float(
        string='Giá Nước (VND/m³)'
    )
    water_usage = fields.Float(string='Lượng Nước (m³)')
    water_amount = fields.Float(
        string='Tiền Nước (VND)',
        compute='_compute_water_amount',
        store=True
    )

    utilities_amount = fields.Float(
        string='Tiền Tiện Ích Khác (VND)',
        default=0
    )
    other_charges = fields.Float(
        string='Phí Khác (VND)',
        default=0
    )
    subtotal = fields.Float(
        string='Tổng Cộng (VND)',
        compute='_compute_subtotal',
        store=True
    )
    discount_amount = fields.Float(
        string='Chiết Khấu (VND)',
        default=0
    )
    total_amount = fields.Float(
        string='Tổng Thanh Toán (VND)',
        compute='_compute_total_amount',
        store=True
    )
    paid_amount = fields.Float(
        string='Số Tiền Đã Thanh Toán (VND)',
        default=0
    )
    remaining_amount = fields.Float(
        string='Số Tiền Còn Lại (VND)',
        compute='_compute_remaining_amount',
        store=True
    )
    notes = fields.Text(string='Ghi Chú')
    manual_breakdown = fields.Text(
        string='Tóm Tắt Chi Tiết',
        compute='_compute_manual_breakdown',
        readonly=True
    )
    meter_reading_id = fields.Many2one(
        'meter.reading',
        string='Chỉ Số Công Tơ',
        domain="[('room_id', '=', room_id)]",
        ondelete='set null'
    )
    applied_config_id = fields.Many2one(
        'room.config',
        string='Cấu Hình Được Áp Dụng',
        readonly=True
    )

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            new_vals = [self._inject_default_values(val.copy())
                        for val in vals]
        else:
            new_vals = self._inject_default_values(vals.copy())
        records = super().create(new_vals)
        records._apply_config_prices(force=True)
        records._sync_meter_readings()
        records._auto_update_status(force_pending=True)
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in
               ('room_id', 'invoice_month', 'invoice_date')):
            self._apply_config_prices(force=True)
        if 'meter_reading_id' in vals:
            self._sync_meter_readings()
        self._auto_update_status()
        return res

    @api.depends('electric_usage', 'electric_price_per_unit')
    def _compute_electric_amount(self):
        for invoice in self:
            if (invoice.electric_usage and
                    invoice.electric_price_per_unit):
                invoice.electric_amount = (
                    invoice.electric_usage *
                    invoice.electric_price_per_unit
                )
            else:
                invoice.electric_amount = 0

    @api.depends('water_usage', 'water_price_per_unit')
    def _compute_water_amount(self):
        for invoice in self:
            if invoice.water_usage and invoice.water_price_per_unit:
                invoice.water_amount = (
                    invoice.water_usage * invoice.water_price_per_unit
                )
            else:
                invoice.water_amount = 0

    @api.depends('rent_amount', 'electric_amount', 'water_amount',
                 'utilities_amount', 'other_charges')
    def _compute_subtotal(self):
        for invoice in self:
            invoice.subtotal = (
                invoice.rent_amount +
                invoice.electric_amount +
                invoice.water_amount +
                invoice.utilities_amount +
                invoice.other_charges
            )

    @api.depends('subtotal', 'discount_amount')
    def _compute_total_amount(self):
        for invoice in self:
            invoice.total_amount = (
                invoice.subtotal - invoice.discount_amount
            )

    @api.depends('total_amount', 'paid_amount')
    def _compute_remaining_amount(self):
        for invoice in self:
            invoice.remaining_amount = (
                invoice.total_amount - invoice.paid_amount
            )
        self._auto_update_status()

    @api.depends(
        'meter_reading_id.electric_previous',
        'meter_reading_id.electric_current',
        'meter_reading_id.water_previous',
        'meter_reading_id.water_current',
        'electric_usage',
        'electric_price_per_unit',
        'electric_amount',
        'water_usage',
        'water_price_per_unit',
        'water_amount',
        'rent_amount',
        'utilities_amount',
        'other_charges',
        'discount_amount'
    )
    def _compute_manual_breakdown(self):
        for invoice in self:
            lines = []

            def fmt(value):
                if value is None:
                    return '0'
                if isinstance(value, float) and value.is_integer():
                    return str(int(value))
                return ('%.2f' % value).rstrip('0').rstrip('.')

            def fmt_amount(value):
                if value is None:
                    return '0'
                return "{:,.0f}".format(value).replace(',', '.')

            reading = invoice.meter_reading_id
            if invoice.water_usage or invoice.water_amount:
                parts = ['Nước:']
                if reading and reading.water_current is not None and reading.water_previous is not None:
                    parts.append(f"{fmt(reading.water_current)} - {fmt(reading.water_previous)} = {fmt(invoice.water_usage)}")
                else:
                    parts.append(f"{fmt(invoice.water_usage)}")
                if invoice.water_price_per_unit:
                    parts.append(f"x {fmt(invoice.water_price_per_unit)}")
                parts.append(f"= {fmt_amount(invoice.water_amount)}")
                lines.append(' '.join(parts))

            if invoice.electric_usage or invoice.electric_amount:
                parts = ['Điện:']
                if reading and reading.electric_current is not None and reading.electric_previous is not None:
                    parts.append(f"{fmt(reading.electric_current)} - {fmt(reading.electric_previous)} = {fmt(invoice.electric_usage)}")
                else:
                    parts.append(f"{fmt(invoice.electric_usage)}")
                if invoice.electric_price_per_unit:
                    parts.append(f"x {fmt(invoice.electric_price_per_unit)}")
                parts.append(f"= {fmt_amount(invoice.electric_amount)}")
                lines.append(' '.join(parts))

            if invoice.utilities_amount:
                lines.append(f"Tiện ích khác: {fmt_amount(invoice.utilities_amount)}")

            if invoice.other_charges:
                lines.append(f"Phí khác: {fmt_amount(invoice.other_charges)}")

            if invoice.discount_amount:
                lines.append(f"Giảm giá: -{fmt_amount(invoice.discount_amount)}")

            if invoice.rent_amount:
                lines.append(f"Tiền phòng: {fmt_amount(invoice.rent_amount)}")

            if invoice.total_amount:
                lines.append(f"Tổng: {fmt_amount(invoice.total_amount)}")

            invoice.manual_breakdown = '\n'.join(lines) if lines else False

    def action_confirm(self):
        self.status = 'pending'

    def action_paid(self):
        for invoice in self:
            invoice.paid_amount = invoice.total_amount
        self._auto_update_status()

    def action_cancel(self):
        self.status = 'canceled'

    def action_print_invoice(self):
        self.ensure_one()
        report = self.env.ref('room_rental_expense.report_room_invoice_pdf', raise_if_not_found=False)
        if not report:
            return False
        return report.report_action(self)

    @api.onchange('meter_reading_id')
    def _onchange_meter_reading_id(self):
        for invoice in self:
            invoice._apply_meter_usage_from_reading()

    @api.onchange('room_id', 'invoice_month', 'invoice_date')
    def _onchange_room_or_dates(self):
        for invoice in self:
            # Tự động lấy tiền thuê mặc định từ phòng nếu chưa nhập
            if invoice.room_id and not invoice.rent_amount and invoice.room_id.default_rent:
                invoice.rent_amount = invoice.room_id.default_rent
            invoice._apply_config_prices(force=True)

    @api.constrains('meter_reading_id', 'room_id')
    def _check_meter_same_room(self):
        for invoice in self:
            if (invoice.meter_reading_id and
                    invoice.meter_reading_id.room_id != invoice.room_id):
                raise ValidationError(
                    _('Chỉ số công tơ phải thuộc cùng phòng với hóa đơn.')
                )

    @api.constrains('invoice_date', 'due_date')
    def _check_due_date(self):
        for invoice in self:
            if (invoice.invoice_date and invoice.due_date and
                    invoice.due_date < invoice.invoice_date):
                raise ValidationError(
                    _('Hạn thanh toán phải sau ngày lập hóa đơn.')
                )

    def _inject_default_values(self, vals):
        room_id = vals.get('room_id') or self.env.context.get('default_room_id')
        room = (room_id and self.env['rental.room'].browse(room_id)) or None
        if isinstance(vals, dict):
            working_vals = vals
        else:
            working_vals = {}
        if room and not working_vals.get('room_id'):
            working_vals['room_id'] = room.id
        if room and not working_vals.get('rent_amount') and room.default_rent:
            working_vals['rent_amount'] = room.default_rent
        invoice_date_value = working_vals.get('invoice_date')
        if (room and not working_vals.get('due_date') and
                invoice_date_value):
            date_obj = fields.Date.to_date(invoice_date_value)
            working_vals['due_date'] = date_obj + timedelta(days=7)
        if not working_vals.get('invoice_number'):
            working_vals['invoice_number'] = self.env[
                'ir.sequence'
            ].next_by_code('room.invoice') or 'INV-2024-001'
        return working_vals

    def _apply_meter_usage_from_reading(self):
        for invoice in self.filtered('meter_reading_id'):
            invoice.electric_usage = invoice.meter_reading_id.electric_usage
            invoice.water_usage = invoice.meter_reading_id.water_usage
            if not invoice.invoice_month and invoice.meter_reading_id:
                invoice.invoice_month = invoice.meter_reading_id.reading_month

    def _apply_config_prices(self, force=False):
        for invoice in self:
            room = invoice.room_id
            if not room:
                continue
            # When editing invoices from the room form, room_id can be a NewId.
            # Use the underlying record (origin) if available so that we can
            # still resolve the proper room.config for onchanges.
            if hasattr(room, '_origin') and room._origin:
                room = room._origin
            reference_date = invoice.invoice_date or self._parse_month_to_date(
                invoice.invoice_month
            ) or fields.Date.context_today(invoice)
            config = room._get_active_config(reference_date)
            if config:
                if force or not invoice.electric_price_per_unit:
                    invoice.electric_price_per_unit = config.electric_price
                if force or not invoice.water_price_per_unit:
                    invoice.water_price_per_unit = config.water_price
                if force or not invoice.utilities_amount:
                    invoice.utilities_amount = (
                        config.wifi_price +
                        config.trash_fee +
                        config.parking_fee +
                        config.other_utilities_price
                    )
                invoice.applied_config_id = config
            else:
                if force or not invoice.electric_price_per_unit:
                    invoice.electric_price_per_unit = self._get_default_price(
                        'room_rental_expense.default_electric_price'
                    )
                if force or not invoice.water_price_per_unit:
                    invoice.water_price_per_unit = self._get_default_price(
                        'room_rental_expense.default_water_price'
                    )
                if force and not invoice.utilities_amount:
                    invoice.utilities_amount = self._get_default_price(
                        'room_rental_expense.default_wifi_price'
                    )
                if force:
                    invoice.applied_config_id = False

    def _sync_meter_readings(self):
        MeterReading = self.env['meter.reading']
        for invoice in self:
            linked_readings = MeterReading.search([
                ('invoice_id', '=', invoice.id)
            ])
            if invoice.meter_reading_id:
                (linked_readings - invoice.meter_reading_id).write(
                    {'invoice_id': False}
                )
                invoice.meter_reading_id.invoice_id = invoice
                invoice._apply_meter_usage_from_reading()
            else:
                linked_readings.write({'invoice_id': False})

    def _auto_update_status(self, force_pending=False):
        today = fields.Date.context_today(self)
        for invoice in self:
            if invoice.status == 'canceled':
                continue
            new_status = invoice.status
            if invoice.total_amount <= 0 and not invoice.paid_amount:
                new_status = 'draft'
            elif invoice.remaining_amount <= 0 and invoice.total_amount:
                new_status = 'paid'
            elif invoice.paid_amount > 0 and invoice.remaining_amount > 0:
                new_status = 'partially_paid'
            elif (invoice.due_date and invoice.due_date < today and
                  invoice.status not in ('overdue', 'paid')):
                new_status = 'overdue'
            elif force_pending or invoice.status == 'draft':
                new_status = 'pending'
            if new_status != invoice.status:
                invoice.status = new_status

    def _parse_month_to_date(self, month_str):
        if not month_str:
            return None
        try:
            return datetime.strptime(f'01/{month_str}', '%d/%m/%Y').date()
        except (ValueError, TypeError):
            return None

    @api.model
    def cron_update_overdue_status(self):
        today = fields.Date.context_today(self)
        reminder_param = self.env['ir.config_parameter'].sudo().get_param(
            'room_rental_expense.reminder_days', '3'
        )
        try:
            reminder_days = int(reminder_param)
        except ValueError:
            reminder_days = 3
        overdue = self.search([
            ('status', 'not in', ('paid', 'canceled')),
            ('due_date', '<', today),
            ('due_date', '!=', False),
        ])
        overdue._auto_update_status()
        upcoming = self.search([
            ('status', 'in', ('draft', 'pending', 'partially_paid')),
            ('due_date', '>=', today),
            ('due_date', '<=', today + relativedelta(days=reminder_days)),
        ])
        for invoice in upcoming:
            invoice._schedule_reminder_activity()

    def _schedule_reminder_activity(self):
        self.ensure_one()
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        existing = self.activity_ids.filtered(
            lambda act: act.activity_type_id == activity_type and
            act.summary == _('Nhắc thanh toán hóa đơn')
        )
        if existing:
            return
        note = _(
            'Hóa đơn %s đến hạn vào %s.\nSố tiền còn lại: %s VND.'
        ) % (
            self.invoice_number or '',
            self.due_date or '',
            self.remaining_amount
        )
        self.activity_schedule(
            activity_type.id,
            date_deadline=self.due_date or fields.Date.context_today(self),
            summary=_('Nhắc thanh toán hóa đơn'),
            note=note
        )

    def _get_default_price(self, key, default=0.0):
        value = self.env['ir.config_parameter'].sudo().get_param(
            key, default
        )
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
