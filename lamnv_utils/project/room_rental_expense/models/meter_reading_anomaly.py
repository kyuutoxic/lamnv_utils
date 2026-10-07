from odoo import api, fields, models


class MeterReadingAnomaly(models.Model):
    _inherit = 'meter.reading'

    anomaly_warning = fields.Text(
        string='Cảnh báo tiêu thụ', compute='_compute_anomaly_warning'
    )

    @api.depends(
        'room_id',
        'reading_date',
        'electric_usage',
        'water_usage',
        'electric_meter_replaced',
        'water_meter_replaced',
        'electric_usage_manual_override',
        'water_usage_manual_override',
    )
    def _compute_anomaly_warning(self):
        try:
            threshold = float(
                self.env['ir.config_parameter']
                .sudo()
                .get_param('room_rental_expense.usage_alert_percent', '50')
            )
        except (ValueError, TypeError):
            threshold = 50
        threshold = threshold if threshold > 0 else 50
        for reading in self:
            messages = []
            if not reading.room_id or not reading.reading_date:
                reading.anomaly_warning = False
                continue
            history = self.search(
                [
                    ('room_id', '=', reading.room_id.id),
                    ('reading_date', '<', reading.reading_date),
                ],
                order='reading_date desc, id desc',
                limit=4,
            )
            if not history:
                reading.anomaly_warning = False
                continue
            duration = (reading.reading_date - history[0].reading_date).days
            for counter, label in (('electric', 'Điện'), ('water', 'Nước')):
                if (
                    reading[f'{counter}_meter_replaced']
                    or reading[f'{counter}_usage_manual_override']
                ):
                    continue
                rates = []
                for index, item in enumerate(history[:-1]):
                    days = (
                        item.reading_date - history[index + 1].reading_date
                    ).days
                    if (
                        days > 0
                        and not item[f'{counter}_meter_replaced']
                        and not item[f'{counter}_usage_manual_override']
                    ):
                        rates.append(item[f'{counter}_usage'] / days)
                if len(rates) < 2:
                    continue
                baseline = sum(rates) / len(rates)
                daily = reading[f'{counter}_usage'] / duration
                if baseline > 0 and daily > baseline * (1 + threshold / 100):
                    increase = (daily / baseline - 1) * 100
                    messages.append(
                        f'{label} tăng {increase:.0f}% so với trung bình '
                        f'{len(rates)} kỳ trước (đã quy đổi theo ngày). '
                        'Kiểm tra chỉ số hoặc rò rỉ; đây là cảnh báo, '
                        'không chặn lưu.'
                    )
            reading.anomaly_warning = '\n'.join(messages) or False
