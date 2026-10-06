from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RoomConfig(models.Model):
    _name = 'room.config'
    _description = 'Cấu Hình Giá Phòng Trọ'
    _rec_name = 'name'
    _order = 'effective_date desc'
    _room_config_unique_effective_date = models.Constraint(
        'unique(room_id, effective_date)',
        'Mỗi phòng chỉ nên có một cấu hình cho cùng ngày hiệu lực.',
    )

    name = fields.Char(string='Tên', compute='_compute_name', store=True)
    room_id = fields.Many2one(
        'rental.room', string='Phòng Trọ', required=True, ondelete='cascade'
    )
    effective_date = fields.Date(string='Ngày Có Hiệu Lực', required=True)
    electric_price = fields.Float(string='Giá Điện (VND/kWh)', required=True)
    water_price = fields.Float(string='Giá Nước (VND/m³)', required=True)
    wifi_price = fields.Float(string='Giá Wifi/Tháng (VND)', default=0)
    trash_fee = fields.Float(string='Phí Rác/Tháng (VND)', default=0)
    parking_fee = fields.Float(string='Phí Gửi Xe/Tháng (VND)', default=0)
    other_utilities_price = fields.Float(
        string='Giá Tiện Ích Khác/Tháng (VND)', default=0
    )
    notes = fields.Text(string='Ghi Chú')

    @api.depends('room_id', 'effective_date')
    def _compute_name(self):
        for config in self:
            parts = []
            if config.room_id:
                parts.append(config.room_id.name)
            if config.effective_date:
                parts.append(config.effective_date.strftime('%d/%m/%Y'))
            config.name = ' - '.join(parts) if parts else 'Cấu Hình'

    @api.constrains(
        'electric_price',
        'water_price',
        'wifi_price',
        'trash_fee',
        'parking_fee',
        'other_utilities_price',
    )
    def _check_non_negative_prices(self):
        for config in self:
            values = (
                config.electric_price,
                config.water_price,
                config.wifi_price,
                config.trash_fee,
                config.parking_fee,
                config.other_utilities_price,
            )
            if any(value < 0 for value in values):
                raise ValidationError(
                    'Các giá trị cấu hình tiện ích không được âm.'
                )
