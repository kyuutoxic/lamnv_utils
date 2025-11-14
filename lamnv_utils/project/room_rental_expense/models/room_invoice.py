# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RoomInvoice(models.Model):
    _name = 'room.invoice'
    _description = 'Hóa Đơn Phòng Trọ'
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
        default=0,
        compute='_compute_paid_amount',
        store=True
    )
    remaining_amount = fields.Float(
        string='Số Tiền Còn Lại (VND)',
        compute='_compute_remaining_amount',
        store=True
    )
    notes = fields.Text(string='Ghi Chú')

    # Relationships
    payment_ids = fields.One2many(
        'room.payment',
        'invoice_id',
        string='Thanh Toán'
    )

    @api.model
    def create(self, vals):
        if not vals.get('invoice_number'):
            vals['invoice_number'] = self.env['ir.sequence'].next_by_code(
                'room.invoice'
            ) or 'INV-2024-001'
        return super().create(vals)

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

    @api.depends('payment_ids.payment_amount')
    def _compute_paid_amount(self):
        for invoice in self:
            invoice.paid_amount = sum(
                payment.payment_amount
                for payment in invoice.payment_ids
            )

    @api.depends('total_amount', 'paid_amount')
    def _compute_remaining_amount(self):
        for invoice in self:
            invoice.remaining_amount = (
                invoice.total_amount - invoice.paid_amount
            )

    def action_confirm(self):
        self.status = 'pending'

    def action_paid(self):
        self.status = 'paid'

    def action_cancel(self):
        self.status = 'canceled'
