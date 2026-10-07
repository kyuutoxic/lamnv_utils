import hashlib
import json
import re
import secrets
from datetime import timedelta
from urllib import error, request as urlrequest
from urllib.parse import urlsplit

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


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
    telegram_public_url = fields.Char(
        string='URL public của Odoo',
        config_parameter='room_rental_expense.telegram_public_url',
        help='URL HTTPS của Odoo hoặc tunnel, ví dụ https://example.com.',
    )
    telegram_pairing_command = fields.Char(readonly=True)
    telegram_connection_info = fields.Text(readonly=True)
    telegram_reminders_enabled = fields.Boolean(
        string='Nhắc hạn Telegram',
        config_parameter='room_rental_expense.telegram_reminders_enabled',
    )
    reminder_days = fields.Integer(
        string='Nhắc trước hạn (ngày)',
        default=3,
        config_parameter='room_rental_expense.reminder_days',
    )
    usage_alert_percent = fields.Float(
        string='Ngưỡng tăng tiêu thụ (%)',
        default=50,
        config_parameter='room_rental_expense.usage_alert_percent',
    )

    @api.constrains('reminder_days', 'usage_alert_percent')
    def _check_alert_settings(self):
        for settings in self:
            if settings.reminder_days < 0 or settings.usage_alert_percent <= 0:
                raise ValidationError(
                    _(
                        'Ngày nhắc phải không âm; '
                        'ngưỡng cảnh báo phải lớn hơn 0.'
                    )
                )

    def _check_telegram_admin(self):
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_('Chỉ quản trị viên được cấu hình Telegram.'))

    def _telegram_api(self, method, payload=None):
        self._check_telegram_admin()
        token = (self.telegram_bot_token or '').strip()
        if not token:
            raise UserError(_('Vui lòng nhập Bot Token.'))
        req = urlrequest.Request(
            f'https://api.telegram.org/bot{token}/{method}',
            data=json.dumps(payload or {}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urlrequest.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode('utf-8'))
        except error.HTTPError as exc:
            raise UserError(
                _(
                    'Telegram từ chối yêu cầu (HTTP %s). Kiểm tra token '
                    'và cấu hình webhook.'
                )
                % exc.code
            ) from None
        except (error.URLError, TimeoutError, ValueError):
            raise UserError(
                _(
                    'Không nhận được phản hồi hợp lệ từ Telegram. '
                    'Kiểm tra mạng và thử lại.'
                )
            ) from None
        if not isinstance(result, dict) or not result.get('ok'):
            raise UserError(_('Telegram từ chối yêu cầu.'))
        return result.get('result')

    def _telegram_notification(self, message, kind='success'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Telegram'),
                'message': message,
                'type': kind,
                'sticky': kind == 'warning',
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'res.config.settings',
                    'res_id': self.id,
                    'views': [(False, 'form')],
                    'target': 'current',
                    'context': dict(
                        self.env.context, module='room_rental_expense'
                    ),
                },
            },
        }

    def _telegram_webhook_url(self):
        public_url = (self.telegram_public_url or '').strip().rstrip('/')
        parsed = urlsplit(public_url)
        if (
            parsed.scheme != 'https'
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise UserError(
                _(
                    'Nhập URL HTTPS public, không có query '
                    'hoặc thông tin đăng nhập.'
                )
            )
        route = '/room_rental_expense/telegram/webhook'
        return public_url if public_url.endswith(route) else public_url + route

    def action_connect_telegram(self):
        self._check_telegram_admin()
        url = self._telegram_webhook_url()
        secret = self.telegram_webhook_secret or secrets.token_urlsafe(32)
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,256}', secret):
            raise UserError(_('Webhook Secret chỉ gồm chữ, số, _ và -.'))
        self._telegram_api(
            'setWebhook',
            {
                'url': url,
                'secret_token': secret,
                'allowed_updates': ['message'],
                'drop_pending_updates': False,
            },
        )
        self.telegram_webhook_secret = secret
        icp = self.env['ir.config_parameter'].sudo()
        for field in (
            'telegram_bot_token',
            'telegram_webhook_secret',
            'telegram_public_url',
        ):
            icp.set_param(f'room_rental_expense.{field}', self[field] or '')
        if self.telegram_allowed_chat_ids:
            icp.set_param(
                'room_rental_expense.telegram_allowed_chat_ids',
                self.telegram_allowed_chat_ids,
            )
        self.telegram_allowed_chat_ids = icp.get_param(
            'room_rental_expense.telegram_allowed_chat_ids', ''
        )
        self._create_telegram_pairing_code()
        message = _('Đã kết nối. Sao chép mã ở phần Ghép nối chat.')
        try:
            self._telegram_api(
                'setMyCommands',
                {
                    'commands': self._get_telegram_commands_payload(),
                },
            )
        except UserError:
            message += _(
                ' Chưa đăng ký được gợi ý lệnh; hãy thử lại '
                'bằng nút Đăng ký lệnh Telegram.'
            )
            return self._telegram_notification(message, 'warning')
        return self._telegram_notification(message)

    def _create_telegram_pairing_code(self):
        self.env.cr.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            ['room.telegram.pairing'],
        )
        code = secrets.token_urlsafe(24)
        icp = self.env['ir.config_parameter'].sudo()
        token = icp.get_param('room_rental_expense.telegram_bot_token', '')
        values = {
            'telegram_pairing_hash': hashlib.sha256(code.encode()).hexdigest(),
            'telegram_pairing_bot': hashlib.sha256(token.encode()).hexdigest(),
            'telegram_pairing_expiry': fields.Datetime.to_string(
                fields.Datetime.now() + timedelta(minutes=10)
            ),
        }
        for key, value in values.items():
            icp.set_param(f'room_rental_expense.{key}', value)
        self.telegram_pairing_command = f'/connect {code}'

    def action_generate_telegram_pairing(self):
        self._check_telegram_admin()
        icp = self.env['ir.config_parameter'].sudo()
        if not icp.get_param('room_rental_expense.telegram_webhook_secret'):
            raise UserError(_('Hãy kết nối Telegram trước.'))
        self._create_telegram_pairing_code()
        return self._telegram_notification(
            _('Đã tạo mã mới. Sao chép mã ở phần Ghép nối chat.')
        )

    def action_check_telegram_connection(self):
        self._check_telegram_admin()
        info = self._telegram_api('getWebhookInfo') or {}
        actual = info.get('url') or ''
        expected = self._telegram_webhook_url()
        matched = actual == expected
        self.telegram_allowed_chat_ids = (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('room_rental_expense.telegram_allowed_chat_ids', '')
        )
        self.telegram_connection_info = _(
            'Webhook: %s\nUpdate đang chờ: %s\nLỗi gần nhất: %s'
        ) % (
            actual or _('Chưa kết nối'),
            info.get('pending_update_count', 0),
            info.get('last_error_message') or _('Không có'),
        )
        if not matched:
            self.telegram_connection_info += _(
                '\nWebhook chưa khớp URL trong Settings. '
                'Bấm Kết nối Telegram để cập nhật.'
            )
        return self._telegram_notification(
            (
                _('Đã cập nhật trạng thái kết nối.')
                if matched and not info.get('last_error_message')
                else _(
                    'Kết nối cần kiểm tra. Xem chi tiết ở Trạng thái kết nối.'
                )
            ),
            (
                'success'
                if matched and not info.get('last_error_message')
                else 'warning'
            ),
        )

    def action_disconnect_telegram(self):
        self._check_telegram_admin()
        icp = self.env['ir.config_parameter'].sudo()
        if (self.telegram_bot_token or '').strip() != icp.get_param(
            'room_rental_expense.telegram_bot_token', ''
        ):
            raise UserError(
                _(
                    'Token khác bot đang cấu hình. '
                    'Dùng token đang kết nối để ngắt webhook.'
                )
            )
        self._telegram_api('deleteWebhook', {'drop_pending_updates': False})
        for key in (
            'telegram_webhook_secret',
            'telegram_pairing_hash',
            'telegram_pairing_expiry',
            'telegram_pairing_bot',
        ):
            icp.set_param(f'room_rental_expense.{key}', '')
        self.telegram_webhook_secret = False
        self.telegram_pairing_command = False
        return self._telegram_notification(_('Đã ngắt webhook Telegram.'))

    def action_register_telegram_commands(self):
        self._telegram_api(
            'setMyCommands',
            {
                'commands': self._get_telegram_commands_payload(),
            },
        )
        return self._telegram_notification(
            _('Đã đăng ký danh sách lệnh Telegram cho bot.')
        )

    def _get_telegram_commands_payload(self):
        return [
            {'command': 'menu', 'description': 'Menu nhập từng bước'},
            {'command': 'cancel', 'description': 'Hủy phiên nhập'},
            {'command': 'summary', 'description': 'Tổng kết chi phí tháng'},
            {'command': 'connect', 'description': 'Ghép nối chat với Odoo'},
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
