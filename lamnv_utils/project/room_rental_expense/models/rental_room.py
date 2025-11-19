# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RentalRoom(models.Model):
    _name = 'rental.room'
    _description = 'Phòng Trọ'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Tên Phòng',
        required=True,
        tracking=True
    )
    room_number = fields.Char(string='Số Phòng')
    building_name = fields.Char(string='Tên Nhà/Khu Trọ')
    address = fields.Text(string='Địa Chỉ Đầy Đủ')
    area = fields.Float(string='Diện Tích (m²)')
    room_type = fields.Selection(
        [('single', 'Phòng Đơn'),
         ('double', 'Phòng Đôi'),
         ('studio', 'Studio'),
         ('shared', 'Phòng Chia Sẻ')],
        string='Loại Phòng',
        default='single'
    )
    start_date = fields.Date(
        string='Ngày Bắt Đầu Thuê',
        tracking=True
    )
    end_date = fields.Date(
        string='Ngày Kết Thúc Thuê',
        tracking=True
    )
    description = fields.Text(string='Mô Tả Phòng')
    utilities_included = fields.Text(string='Tiện Ích Bao Gồm')
    note = fields.Text(string='Ghi Chú')
    image = fields.Binary(
        string='Ảnh Phòng',
        attachment=True
    )

    # Thông tin chủ phòng
    landlord_name = fields.Char(
        string='Tên Chủ Phòng',
        tracking=True
    )
    landlord_phone = fields.Char(string='Số Điện Thoại Chủ Phòng')
    landlord_email = fields.Char(string='Email Chủ Phòng')
    landlord_bank_account = fields.Char(string='Tài Khoản Ngân Hàng')
    landlord_bank_name = fields.Char(string='Tên Ngân Hàng')
    landlord_favorite = fields.Boolean(
        string='Đánh Dấu',
        default=False
    )
    default_rent = fields.Float(
        string='Tiền Thuê Mặc Định (VND)',
        tracking=True
    )

    # Relationships
    invoice_ids = fields.One2many(
        'room.invoice',
        'room_id',
        string='Hóa Đơn'
    )
    meter_reading_ids = fields.One2many(
        'meter.reading',
        'room_id',
        string='Chỉ Số Công Tơ'
    )
    expense_ids = fields.One2many(
        'room.expense',
        'room_id',
        string='Chi Phí'
    )
    config_ids = fields.One2many(
        'room.config',
        'room_id',
        string='Cấu Hình Giá'
    )
    deposit_ids = fields.One2many(
        'room.deposit',
        'room_id',
        string='Tiền Cọc'
    )
    issue_ids = fields.One2many(
        'room.issue',
        'room_id',
        string='Sự Cố'
    )

    # Computed fields
    total_invoiced = fields.Float(
        string='Tổng Tiền Hóa Đơn',
        compute='_compute_total_invoiced',
        store=True
    )
    total_paid = fields.Float(
        string='Tổng Tiền Thanh Toán',
        compute='_compute_total_paid',
        store=True
    )
    total_remaining = fields.Float(
        string='Tổng Tiền Còn Lại',
        compute='_compute_total_remaining',
        store=True
    )
    total_expenses = fields.Float(
        string='Tổng Chi Phí',
        compute='_compute_total_expenses',
        store=True
    )
    
    # Display fields for Kanban (không store, chỉ để hiển thị)
    total_invoiced_fmt = fields.Char(
        string='Tổng Hóa Đơn Formatted',
        compute='_compute_formatted_totals'
    )
    total_remaining_fmt = fields.Char(
        string='Tổng Còn Lại Formatted', 
        compute='_compute_formatted_totals'
    )
    default_rent_fmt = fields.Char(
        string='Tiền Thuê Formatted',
        compute='_compute_formatted_totals'
    )

    def format_vnd_amount(self, amount):
        """Format amount with Vietnamese style (dots as thousand separators)"""
        if not amount:
            return "0"
        return "{:,.0f}".format(amount).replace(',', '.')
    
    @api.depends('total_invoiced', 'total_remaining', 'default_rent')
    def _compute_formatted_totals(self):
        """Compute formatted amounts for display only"""
        for room in self:
            room.total_invoiced_fmt = room.format_vnd_amount(room.total_invoiced)
            room.total_remaining_fmt = room.format_vnd_amount(room.total_remaining)
            room.default_rent_fmt = room.format_vnd_amount(room.default_rent)

    @api.depends('invoice_ids.total_amount')
    def _compute_total_invoiced(self):
        for room in self:
            room.total_invoiced = sum(
                inv.total_amount for inv in room.invoice_ids
            )

    @api.depends('invoice_ids.paid_amount')
    def _compute_total_paid(self):
        for room in self:
            room.total_paid = sum(
                inv.paid_amount for inv in room.invoice_ids
            )

    @api.depends('invoice_ids.remaining_amount')
    def _compute_total_remaining(self):
        for room in self:
            room.total_remaining = sum(
                inv.remaining_amount for inv in room.invoice_ids
            )

    @api.depends('expense_ids.amount')
    def _compute_total_expenses(self):
        for room in self:
            room.total_expenses = sum(
                exp.amount for exp in room.expense_ids
            )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for room in self:
            if (room.start_date and room.end_date and
                    room.start_date > room.end_date):
                raise ValueError(
                    'Ngày kết thúc phải lớn hơn ngày bắt đầu!'
                )

    def action_view_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Hóa Đơn - {self.name}',
            'res_model': 'room.invoice',
            'view_mode': 'tree,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id}
        }

    def action_view_meter_readings(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Chỉ Số Công Tơ - {self.name}',
            'res_model': 'meter.reading',
            'view_mode': 'tree,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id}
        }

    def _get_active_config(self, reference_date=None):
        self.ensure_one()
        domain = [('room_id', '=', self.id)]
        if reference_date:
            domain.append(('effective_date', '<=', reference_date))
        return self.env['room.config'].search(
            domain,
            order='effective_date desc',
            limit=1
        )
