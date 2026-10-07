from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class RoomMonthlySummary(models.TransientModel):
    _name = 'room.monthly.summary'
    _description = 'Tổng Kết Chi Phí Tháng'

    room_id = fields.Many2one('rental.room', string='Phòng')
    month = fields.Char(
        string='Tháng (MM/YYYY)',
        required=True,
        default=lambda self: fields.Date.context_today(self).strftime('%m/%Y'),
    )
    summary = fields.Text(compute='_compute_summary', string='Tổng kết')

    @api.model
    def _month_start(self, month):
        try:
            return datetime.strptime('01/' + month, '%d/%m/%Y').date()
        except (ValueError, TypeError):
            raise ValidationError('Nhập tháng theo MM/YYYY.') from None

    @api.model
    def _totals(self, month, room=None):
        start = self._month_start(month)
        end = start + relativedelta(months=1)
        domain = [
            ('invoice_period_date', '>=', start),
            ('invoice_period_date', '<', end),
            ('status', 'not in', ['draft', 'canceled']),
        ]
        expense_domain = [
            ('expense_date', '>=', start),
            ('expense_date', '<', end),
        ]
        if room:
            domain.append(('room_id', '=', room.id))
            expense_domain.append(('room_id', '=', room.id))
        invoices = self.env['room.invoice'].search(domain)
        expenses = self.env['room.expense'].search(expense_domain)
        totals = {
            key: sum(invoices.mapped(key))
            for key in (
                'rent_amount',
                'electric_amount',
                'water_amount',
                'utilities_amount',
                'other_charges',
                'discount_amount',
                'total_amount',
                'paid_amount',
                'remaining_amount',
            )
        }
        totals['expenses'] = sum(expenses.mapped('amount'))
        totals['cost'] = totals['total_amount'] + totals['expenses']
        totals['invoice_count'] = len(invoices)
        return totals

    @api.model
    def _build_summary(self, month, room=None):
        start = self._month_start(month)
        totals = self._totals(month, room)
        previous_month = (start - relativedelta(months=1)).strftime('%m/%Y')
        previous = self._totals(previous_month, room)
        fmt = self.env['rental.room'].format_vnd_amount
        lines = [f'Tổng kết {month} - {room.name if room else "Tất cả phòng"}']
        for label, key in (
            ('Tiền thuê', 'rent_amount'),
            ('Điện', 'electric_amount'),
            ('Nước', 'water_amount'),
            ('Tiện ích', 'utilities_amount'),
            ('Phí khác', 'other_charges'),
            ('Giảm giá', 'discount_amount'),
            ('Chi phí phát sinh', 'expenses'),
            ('Tổng chi phí', 'cost'),
            ('Đã trả trên hóa đơn kỳ này', 'paid_amount'),
            ('Còn lại trên hóa đơn kỳ này', 'remaining_amount'),
        ):
            lines.append(f'{label}: {fmt(totals[key])} VND')
        difference = totals['cost'] - previous['cost']
        lines.append(f'So với {previous_month}: {fmt(difference)} VND')
        lines.append(
            'Không gồm hóa đơn nháp/hủy hoặc tiền cọc. '
            'Đã trả là tổng hiện tại, không theo ngày chuyển tiền.'
        )
        return '\n'.join(lines)

    @api.depends('month', 'room_id')
    def _compute_summary(self):
        for record in self:
            record.summary = (
                record._build_summary(record.month, record.room_id)
                if record.month
                else ''
            )
