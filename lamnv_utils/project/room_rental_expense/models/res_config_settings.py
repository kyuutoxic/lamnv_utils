import json
from urllib import error, request as urlrequest

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    telegram_bot_token = fields.Char(
        string='Telegram Bot Token',
        config_parameter='room_rental_expense.telegram_bot_token',
    )
    telegram_webhook_secret = fields.Char(
        string='Telegram Webhook Secret',
        help=(
            'Bắt buộc để nhận webhook. '
            'Phải khớp secret_token khi setWebhook.'
        ),
        config_parameter='room_rental_expense.telegram_webhook_secret',
    )
    telegram_allowed_chat_ids = fields.Char(
        string='Telegram Allowed Chat IDs',
        help='Bắt buộc. Danh sách chat ID được phép, ngăn cách bằng dấu phẩy.',
        config_parameter='room_rental_expense.telegram_allowed_chat_ids',
    )

    def action_register_telegram_commands(self):
        self.ensure_one()
        token = self.telegram_bot_token or self.env[
            'ir.config_parameter'
        ].sudo().get_param('room_rental_expense.telegram_bot_token')
        if not token:
            raise UserError(
                _(
                    'Vui lòng cấu hình Telegram Bot Token trước khi đăng ký '
                    'lệnh.'
                )
            )

        endpoint = f'https://api.telegram.org/bot{token}/setMyCommands'
        payload = json.dumps(
            {
                'commands': self._get_telegram_commands_payload(),
            }
        ).encode('utf-8')
        req = urlrequest.Request(
            endpoint,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urlrequest.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode('utf-8'))
        except error.URLError as exc:
            raise UserError(
                _('Không thể kết nối Telegram Bot API để đăng ký lệnh: %s')
                % exc
            ) from exc

        if not result.get('ok'):
            raise UserError(
                _('Telegram từ chối đăng ký lệnh: %s')
                % (result.get('description') or _('Lỗi không xác định'))
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': _('Đã đăng ký danh sách lệnh Telegram cho bot.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def _get_telegram_commands_payload(self):
        return [
            {
                'command': 'help',
                'description': 'Xem hướng dẫn',
            },
            {
                'command': 'reading',
                'description': 'Nhập chỉ số điện nước',
            },
            {
                'command': 'inv',
                'description': 'Tạo hóa đơn từ chỉ số',
            },
            {
                'command': 'show',
                'description': 'Xem hóa đơn',
            },
            {
                'command': 'invoices',
                'description': 'Xem danh sách hóa đơn',
            },
            {
                'command': 'readings',
                'description': 'Xem danh sách chỉ số',
            },
            {
                'command': 'paid',
                'description': 'Đánh dấu đã thanh toán',
            },
            {
                'command': 'pay',
                'description': 'Thanh toán một phần',
            },
            {
                'command': 'unpaid',
                'description': 'Đặt lại chưa thanh toán',
            },
        ]
