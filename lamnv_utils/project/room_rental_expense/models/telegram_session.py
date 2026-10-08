import copy
import hashlib
import math
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

MENU_ICONS = {
    'Ghi chỉ số': '🔢',
    'Hóa đơn': '🧾',
    'Thanh toán': '💳',
    'Tổng kết tháng': '📊',
    'Đổi kỳ hóa đơn': '🗓️',
    'Sửa ngày chỉ số': '✏️',
    'Tạo hóa đơn': '➕',
    'Trả hết': '💰',
    'Xác nhận': '✅',
    'Hủy': '❌',
    'Quay lại': '⬅️',
    'Hôm nay': '📅',
    'Chưa trả': '🟠',
    'Quá hạn': '🔴',
    'Đã trả': '🟢',
    'Tất cả': '📋',
    'Trang trước': '◀️',
    'Trang sau': '▶️',
}


class RoomTelegramSession(models.Model):
    _name = 'room.telegram.session'
    _description = 'Phiên Nhập Telegram'

    bot_key = fields.Char(required=True)
    chat_id = fields.Char(required=True)
    user_id = fields.Char(required=True)
    step = fields.Char(default='menu')
    values = fields.Json(default=dict)
    navigation = fields.Json(default=list)
    last_reply = fields.Json(default=dict)
    expires_at = fields.Datetime(required=True)
    _session_unique = models.Constraint(
        'unique(bot_key, chat_id, user_id)', 'Phiên Telegram đã tồn tại.'
    )

    @api.model
    def _button_label(self, text):
        icon = MENU_ICONS.get(text)
        if text.startswith('Kỳ hiện tại ('):
            icon = '📅'
        return f'{icon} {text}' if icon else text

    @api.model
    def _menu_text(self, text):
        for command in MENU_ICONS:
            if text == self._button_label(command):
                return command
        if text.startswith('📅 Kỳ hiện tại ('):
            return text.removeprefix('📅 ')
        return text

    @api.model
    def _reply(self, text, buttons=None):
        buttons = buttons or [
            ['Ghi chỉ số', 'Hóa đơn'],
            ['Thanh toán', 'Tổng kết tháng'],
            ['Đổi kỳ hóa đơn', 'Sửa ngày chỉ số'],
            ['Hủy'],
        ]
        return {
            'status': 'success',
            'message': text,
            'reply_markup': {
                'keyboard': [
                    [self._button_label(button) for button in row]
                    for row in buttons
                ],
                'resize_keyboard': True,
                'one_time_keyboard': False,
                'input_field_placeholder': 'Chọn nút hoặc nhập nội dung…',
            },
        }

    @api.model
    def _handle_message(self, message):
        text = self._menu_text((message.get('text') or '').strip())
        commands = {
            '/start',
            '/menu',
            'Ghi chỉ số',
            'Hóa đơn',
            'Thanh toán',
            'Tổng kết tháng',
            'Đổi kỳ hóa đơn',
            'Sửa ngày chỉ số',
            'Hủy',
            '/cancel',
        }
        if text.lower().startswith('/connect'):
            return None
        chat = (message.get('chat') or {}).get('id')
        user = (message.get('from') or {}).get('id')
        if type(chat) is not int or type(user) is not int:
            return None
        self.env['meter.reading']._check_telegram_sender_allowed(chat)
        token = (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('room_rental_expense.telegram_bot_token', '')
        )
        key = hashlib.sha256(token.encode()).hexdigest()
        self.env.cr.execute(
            'SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
            [f'room.telegram.session:{key}:{chat}:{user}'],
        )
        session = self.search(
            [
                ('bot_key', '=', key),
                ('chat_id', '=', str(chat)),
                ('user_id', '=', str(user)),
            ],
            limit=1,
        )
        if session and session.expires_at <= fields.Datetime.now():
            session.unlink()
            session = self.browse()
            if text not in commands and not text.startswith('/'):
                return self._reply(
                    'Phiên hết hạn. Chọn thao tác để bắt đầu lại.'
                )
        if text.startswith('/') and text not in commands:
            if session:
                session.unlink()
            return None
        if not session and text not in commands:
            return None
        if not session:
            session = self.create(
                {
                    'bot_key': key,
                    'chat_id': str(chat),
                    'user_id': str(user),
                    'expires_at': fields.Datetime.now()
                    + timedelta(minutes=30),
                }
            )
        session.expires_at = fields.Datetime.now() + timedelta(minutes=30)
        if text in commands:
            session.navigation = []
        if text in ('Đổi kỳ hóa đơn', 'Sửa ngày chỉ số'):
            session.write({'step': 'change_invoice', 'values': {}})
            domain = [('status', '!=', 'canceled')]
            if text == 'Sửa ngày chỉ số':
                domain.append(('meter_reading_id', '!=', False))
            invoices = self.env['room.invoice'].search(
                domain,
                limit=20,
            )
            choices = {
                f'🧾 {inv.invoice_number} | {inv.room_id.name} | '
                f'{inv.invoice_month}': inv.invoice_number
                for inv in invoices
            }
            session.values = {
                'invoice_choices': choices,
                'action': text,
            }
            if not choices:
                return self._reply(
                    f'Không có hóa đơn phù hợp cho {text}. '
                    'Hóa đơn đã hủy không được chọn.'
                )
            return session._present(self._reply(
                f'{text} (tối đa 20 hóa đơn phù hợp mới nhất):\n'
                + '\n'.join(choices)
                + '\nBấm nút hóa đơn bên dưới hoặc nhập số hóa đơn.',
                [[label] for label in choices] + [['Hủy']],
            ))
        if text in ('/start', '/menu', 'Hủy', '/cancel'):
            session.write({'step': 'menu', 'values': {}})
            return session._present(self._reply(
                '🏠 PHÒNG TRỌ\n\n'
                '🔢 Ghi điện nước • 🧾 Xem hóa đơn\n'
                '💳 Thanh toán • 📊 Tổng kết chi phí\n'
                '🗓️ Đổi kỳ • ✏️ Sửa ngày chỉ số\n\n'
                '👇 Chọn thao tác bên dưới.\n'
                'Gõ /menu để về menu, /cancel để hủy.'
            ))
        if text in ('Ghi chỉ số', 'Hóa đơn', 'Thanh toán', 'Tổng kết tháng'):
            if text == 'Thanh toán':
                session.write(
                    {'step': 'invoice', 'values': {'filter': 'Chưa trả'}}
                )
                return session._present(session._invoice_list())
            session.write({'step': 'room', 'values': {'action': text}})
            rooms = self.env['rental.room'].search([], limit=30)
            return session._present(self._reply(
                'Chọn phòng (hoặc nhập mã phòng).',
                [[f'🏠 #{room.id} - {room.name}'] for room in rooms]
                + [['Hủy']],
            ))
        return session._navigate(text)

    def _present(self, result):
        result = copy.deepcopy(result)
        if self.navigation:
            keyboard = result.get('reply_markup', {}).get('keyboard', [])
            rows = [
                [button for button in row
                 if self._menu_text(button) not in ('Quay lại', 'Hủy')]
                for row in keyboard
            ]
            result['reply_markup']['keyboard'] = [row for row in rows if row]
            result['reply_markup']['keyboard'].append(
                [self._button_label('Quay lại'), self._button_label('Hủy')]
            )
        self.last_reply = result
        return result

    def _navigate(self, text):
        history = list(self.navigation or [])
        if text == 'Quay lại':
            if not history:
                return self._present(self._reply('Chọn thao tác từ menu.'))
            previous = history.pop()
            self.write(
                {
                    'step': previous['step'],
                    'values': previous['values'],
                    'navigation': history,
                }
            )
            if self.step in ('invoice', 'show_invoice'):
                return self._present(self._invoice_list())
            result = previous['reply']
            keyboard = result.get('reply_markup', {}).get('keyboard', [])
            result['reply_markup']['keyboard'] = [
                [button for button in row
                 if self._menu_text(button) != 'Quay lại']
                for row in keyboard
                if any(self._menu_text(button) != 'Quay lại' for button in row)
            ]
            return self._present(result)
        previous = {
            'step': self.step,
            'values': copy.deepcopy(self.values or {}),
            'reply': copy.deepcopy(self.last_reply or self._reply('')),
        }
        result = self._advance(text)
        if self.step in ('menu', 'reading_saved'):
            history = []
        elif self.step != previous['step']:
            history.append(previous)
        self.navigation = history
        return self._present(result)

    def _invoice_list(self):
        values = dict(self.values or {})
        selected = values.get('filter', 'Tất cả')
        domain = [('status', '!=', 'canceled')]
        if values.get('room_id'):
            domain.append(('room_id', '=', values['room_id']))
        if (
            self.step == 'invoice' or selected in ('Chưa trả', 'Quá hạn')
        ):
            domain += [
                ('status', 'not in', ['draft', 'paid']),
                ('remaining_amount', '>', 0),
            ]
        if selected == 'Đã trả':
            domain.append(('status', '=', 'paid'))
        elif selected == 'Quá hạn':
            domain.append(
                ('due_date', '<', fields.Date.context_today(self))
            )
        invoices = self.env['room.invoice']
        count = invoices.search_count(domain)
        pages = max(1, (count + 7) // 8)
        page = max(0, min(values.get('page', 0), pages - 1))
        records = invoices.search(
            domain, offset=page * 8, limit=8,
            order='invoice_date desc, id desc',
        )
        choices = {
            f'🧾 {inv.invoice_number} | {inv.room_id.name} | '
            f'{inv.invoice_month} | Còn '
            f'{inv.room_id.format_vnd_amount(inv.remaining_amount)}đ':
            inv.invoice_number
            for inv in records
        }
        values.update({'invoice_choices': choices, 'page': page})
        self.values = values
        buttons = [[label] for label in choices]
        filters = ['Chưa trả', 'Quá hạn']
        if self.step == 'show_invoice':
            filters += ['Đã trả', 'Tất cả']
        buttons += [filters[index:index + 2]
                    for index in range(0, len(filters), 2)]
        paging = []
        if page:
            paging.append('Trang trước')
        if page + 1 < pages:
            paging.append('Trang sau')
        if paging:
            buttons.append(paging)
        buttons.append(['Hủy'])
        return self._reply(
            f'🧾 Hóa đơn — {selected}\n'
            f'📄 Trang {page + 1}/{pages} • {count} hóa đơn\n\n'
            + ('\n'.join(choices) if choices else 'Không có hóa đơn phù hợp.')
            + '\nChọn hóa đơn hoặc nhập số hóa đơn.',
            buttons,
        )

    def _period_buttons(self):
        period = fields.Date.context_today(self).strftime('%m/%Y')
        values = dict(self.values or {})
        values['current_period'] = period
        self.values = values
        return [[f'Kỳ hiện tại ({period})'], ['Hủy']]

    def _advance(self, text):
        self.ensure_one()
        readings = self.env['meter.reading']
        values = dict(self.values or {})
        if self.step in ('invoice_month', 'change_month', 'month'):
            period = values.get('current_period')
            if period and text == f'Kỳ hiện tại ({period})':
                text = period
        if self.step in ('invoice', 'show_invoice'):
            filters = ('Chưa trả', 'Quá hạn', 'Đã trả', 'Tất cả')
            if text in filters:
                if self.step == 'invoice' and text in ('Đã trả', 'Tất cả'):
                    raise ValidationError('Chọn Chưa trả hoặc Quá hạn.')
                values.update({'filter': text, 'page': 0})
                self.values = values
                return self._invoice_list()
            if text in ('Trang trước', 'Trang sau'):
                values['page'] = values.get('page', 0) + (
                    1 if text == 'Trang sau' else -1
                )
                self.values = values
                return self._invoice_list()
        if self.step == 'change_invoice':
            number = values.get('invoice_choices', {}).get(text, text)
            invoice = readings._find_telegram_invoice_by_number(number)
            if invoice.status == 'canceled':
                raise ValidationError('Hóa đơn đã hủy không được đổi kỳ.')
            if values.get('action') == 'Sửa ngày chỉ số':
                reading = invoice.meter_reading_id
                if not reading:
                    raise ValidationError('Hóa đơn không có chỉ số.')
                self.write(
                    {
                        'step': 'correct_date',
                        'values': {
                            'reading_id': reading.id,
                            'old_date': str(reading.reading_date),
                        },
                    }
                )
                return self._reply(
                    f'Ngày đang lưu: {reading.reading_date}. '
                    'Nhập ngày đo thực tế YYYY-MM-DD, '
                    'không phải ngày nhập dữ liệu.',
                    [['Hủy']],
                )
            self.write(
                {
                    'step': 'change_month',
                    'values': {
                        'invoice_id': invoice.id,
                        'old_month': invoice.invoice_month,
                    },
                }
            )
            return self._reply(
                f'Kỳ đang lưu: {invoice.invoice_month}. Nhập kỳ MM/YYYY '
                'hoặc chọn kỳ hiện tại bên dưới.',
                self._period_buttons(),
            )
        if self.step in ('correct_date', 'date_reason', 'confirm_date'):
            reading = readings.browse(values['reading_id']).exists()
            if not reading:
                raise ValidationError('Chỉ số đã bị xóa.')
            if self.step == 'correct_date':
                date = readings._parse_telegram_date(text)
                if date > fields.Date.context_today(self):
                    raise ValidationError('Ngày đo không được ở tương lai.')
                values['date'] = str(date)
                self.write({'step': 'date_reason', 'values': values})
                return self._reply('Nhập lý do sửa ngày.', [['Hủy']])
            if self.step == 'date_reason':
                if not text or len(text) > 500:
                    raise ValidationError('Lý do phải có 1–500 ký tự.')
                values['reason'] = text
                note = reading._get_corrected_date_notes(
                    fields.Date.to_date(values['date'])
                )
                self.write({'step': 'confirm_date', 'values': values})
                return self._reply(
                    f'Ngày đo: {values["old_date"]} → {values["date"]}.\n'
                    f'Lý do: {text}\n'
                    'Giữ nguyên chỉ số, tiêu thụ và tiền hóa đơn. '
                    'Thứ tự lịch sử và số cũ gợi ý cho lần mới sẽ đổi. '
                    'Xác nhận?' + ('\n' + note if note else ''),
                    [['Xác nhận', 'Hủy']],
                )
            if text != 'Xác nhận':
                raise ValidationError('Bấm Xác nhận hoặc Hủy.')
            reading._correct_reading_date(
                values['date'], values['old_date'], values['reason']
            )
            self.write({'step': 'menu', 'values': {}})
            return self._reply(
                f'Đã sửa ngày đo thành {reading.reading_date}. '
                'Bạn có thể chọn Ghi chỉ số để ghi lần đo mới.'
            )
        if self.step in (
            'change_month',
            'change_reason',
            'confirm_change_month',
        ):
            invoice = (
                self.env['room.invoice'].browse(values['invoice_id']).exists()
            )
            if not invoice:
                raise ValidationError('Hóa đơn đã bị xóa.')
            if self.step == 'change_month':
                values['month'] = invoice._check_available_period(
                    text, invoice.room_id
                )
                self.write(
                    {
                        'step': 'change_reason',
                        'values': values,
                    }
                )
                return self._reply(
                    'Nhập lý do sửa kỳ (1–500 ký tự).', [['Hủy']]
                )
            if self.step == 'change_reason':
                if not text or len(text) > 500:
                    raise ValidationError('Lý do phải có 1–500 ký tự.')
                values['reason'] = text
                self.write(
                    {
                        'step': 'confirm_change_month',
                        'values': values,
                    }
                )
                return self._reply(
                    f'{invoice.invoice_number}: {values["old_month"]} → '
                    f'{values["month"]}.\nLý do: {text}\n'
                    'Giữ nguyên tiền, trạng thái thanh toán và các ngày. '
                    'Tổng kết tháng sẽ thay đổi. Xác nhận sửa kỳ?',
                    [['Xác nhận', 'Hủy']],
                )
            if text != 'Xác nhận':
                raise ValidationError('Bấm Xác nhận hoặc Hủy.')
            invoice._change_billing_period(
                values['month'], values['old_month'], values['reason']
            )
            self.write({'step': 'menu', 'values': {}})
            return self._reply(
                readings._build_telegram_invoice_summary(invoice)
            )
        if self.step == 'room':
            if text.startswith('🏠 #'):
                text = text.removeprefix('🏠 ')
            if text.startswith('#'):
                try:
                    room = (
                        self.env['rental.room']
                        .browse(int(text.split()[0][1:]))
                        .exists()
                    )
                except ValueError:
                    room = self.env['rental.room']
                if not room:
                    raise ValidationError('Không tìm thấy phòng.')
            else:
                room = readings._find_room_by_telegram_key(text)
            values['room_id'] = room.id
            action = values['action']
            if action == 'Hóa đơn':
                self.step = 'show_invoice'
                self.values = values
                return self._invoice_list()
            self.write(
                {
                    'step': (
                        'month' if action == 'Tổng kết tháng' else 'electric'
                    ),
                    'values': values,
                }
            )
            return self._reply(
                (
                    'Nhập tháng MM/YYYY.'
                    if self.step == 'month'
                    else 'Nhập chỉ số điện hiện tại.'
                ),
                (
                    self._period_buttons()
                    if self.step == 'month' else [['Hủy']]
                ),
            )
        if self.step == 'month':
            room = self.env['rental.room'].browse(values['room_id']).exists()
            if not room:
                raise ValidationError(
                    'Phòng đã bị xóa. Gõ /menu để bắt đầu lại.'
                )
            text = self.env['room.monthly.summary']._build_summary(text, room)
            self.step = 'menu'
            return self._reply(text)
        if self.step in ('electric', 'water'):
            try:
                number = float(text.replace(',', '.'))
            except ValueError:
                raise ValidationError(
                    'Nhập số không âm, ví dụ 350 hoặc 350.5.'
                )
            if not math.isfinite(number) or number < 0:
                raise ValidationError('Chỉ số phải là số hữu hạn không âm.')
            values[self.step + '_current'] = number
            next_step = 'water' if self.step == 'electric' else 'date'
            self.write({'step': next_step, 'values': values})
            return self._reply(
                (
                    'Nhập chỉ số nước hiện tại.'
                    if next_step == 'water'
                    else 'Nhập ngày YYYY-MM-DD hoặc chọn Hôm nay.'
                ),
                [['Hôm nay'], ['Hủy']] if next_step == 'date' else [['Hủy']],
            )
        if self.step == 'date':
            try:
                date = (
                    fields.Date.context_today(self)
                    if text == 'Hôm nay'
                    else fields.Date.to_date(text)
                )
                if not date:
                    raise ValueError()
            except (TypeError, ValueError):
                raise ValidationError('Nhập ngày YYYY-MM-DD.') from None
            room = self.env['rental.room'].browse(values['room_id']).exists()
            if not room:
                raise ValidationError(
                    'Phòng đã bị xóa. Gõ /menu để bắt đầu lại.'
                )
            values['reading_date'] = str(date)
            preview_vals = {
                key: values[key]
                for key in (
                    'room_id',
                    'electric_current',
                    'water_current',
                    'reading_date',
                )
            }
            preview_vals.update(
                readings._prepare_previous_counter_vals(room, date)
            )
            preview = readings.new(preview_vals)
            errors = preview._get_counter_regression_messages()
            if errors:
                raise ValidationError('\n'.join(errors))
            self.write({'step': 'confirm_reading', 'values': values})
            summary = (
                f'{room.name} - {date}\n'
                f'Điện: {values["electric_current"]}; '
                f'nước: {values["water_current"]}\n'
                'Bấm Xác nhận để ghi/cập nhật chỉ số ngày này.'
            )
            if preview.anomaly_warning:
                summary += '\n' + preview.anomaly_warning
            return self._reply(summary, [['Xác nhận', 'Hủy']])
        if self.step == 'confirm_reading':
            if text != 'Xác nhận':
                raise ValidationError('Bấm Xác nhận hoặc Hủy.')
            room = self.env['rental.room'].browse(values['room_id']).exists()
            if not room:
                raise ValidationError('Phòng đã bị xóa.')
            values['reading_date'] = fields.Date.to_date(
                values['reading_date']
            )
            result = readings._upsert_from_telegram_payload(
                dict(
                    values,
                    room_key=room.telegram_code or room.name,
                    telegram_chat_id=int(self.chat_id),
                    telegram_user_id=int(self.user_id),
                    raw_text='Menu Telegram',
                )
            )
            self.write(
                {
                    'step': 'reading_saved',
                    'values': {'reading_id': result['reading_id']},
                }
            )
            result['reply_markup'] = self._reply(
                '', [['Tạo hóa đơn'], ['Ghi chỉ số', 'Hủy']]
            )['reply_markup']
            return result
        if self.step in ('reading_saved', 'invoice_month', 'confirm_invoice'):
            reading = readings.browse(values['reading_id']).exists()
            if not reading:
                raise ValidationError('Chỉ số đã bị xóa. Gõ /menu.')
            if self.step == 'reading_saved':
                if text != 'Tạo hóa đơn':
                    raise ValidationError('Chọn Tạo hóa đơn hoặc Hủy.')
                self.step = 'invoice_month'
                return self._reply(
                    'Nhập kỳ tính tiền MM/YYYY (ví dụ 09/2026). '
                    'Kỳ có thể khác tháng ghi chỉ số.',
                    self._period_buttons(),
                )
            if self.step == 'invoice_month':
                values['month'] = (
                    self.env['room.invoice']
                    .browse(reading.invoice_id.id)
                    ._check_available_period(text, reading.room_id)
                )
                self.write({'step': 'confirm_invoice', 'values': values})
                return self._reply(
                    f'Tạo hóa đơn cho {reading.room_id.name}, '
                    f'kỳ {values["month"]}, ghi ngày {reading.reading_date}? '
                    'Hóa đơn mới có tổng tiền lớn hơn 0 sẽ được xác nhận.',
                    [['Xác nhận', 'Hủy']],
                )
            if text != 'Xác nhận':
                raise ValidationError('Bấm Xác nhận hoặc Hủy.')
            invoice = reading.invoice_id
            if invoice and invoice.invoice_month != values['month']:
                raise ValidationError(
                    'Chỉ số đã có hóa đơn kỳ khác. '
                    'Dùng menu Đổi kỳ hóa đơn để sửa kỳ.'
                )
            if not invoice:
                month = self.env['room.invoice']._check_available_period(
                    values['month'], reading.room_id
                )
                invoice = self.env['room.invoice'].create(
                    {
                        'room_id': reading.room_id.id,
                        'invoice_month': month,
                        'invoice_date': fields.Date.context_today(self),
                        'meter_reading_id': reading.id,
                    }
                )
                if invoice.status == 'draft' and invoice.total_amount > 0:
                    invoice.action_confirm()
            self.write({'step': 'menu', 'values': {}})
            result = self._reply(
                readings._build_telegram_invoice_summary(invoice)
            )
            result['invoice_id'] = invoice.id
            return result
        if self.step in ('invoice', 'show_invoice'):
            number = values.get('invoice_choices', {}).get(text, text)
            invoice = readings._find_telegram_invoice_by_number(number)
            if self.step == 'show_invoice':
                if invoice.room_id.id != values['room_id']:
                    raise ValidationError('Hóa đơn không thuộc phòng đã chọn.')
                self.step = 'invoice_detail'
                return self._reply(
                    readings._build_telegram_invoice_summary(invoice),
                    [['Hủy']],
                )
            if invoice.status in ('draft', 'paid', 'canceled'):
                raise ValidationError('Chọn hóa đơn còn phải thanh toán.')
            self.write(
                {'step': 'amount', 'values': {'invoice_number': number}}
            )
            return self._reply(
                readings._build_telegram_invoice_summary(invoice)
                + '\nChọn Trả hết hoặc nhập số tiền trả (VND).',
                [['Trả hết'], ['Hủy']],
            )
        if self.step == 'amount':
            if text == 'Trả hết':
                invoice = readings._find_telegram_invoice_by_number(
                    values['invoice_number']
                )
                if invoice.status in ('draft', 'paid', 'canceled'):
                    raise ValidationError('Chọn hóa đơn còn phải thanh toán.')
                amount = invoice.remaining_amount
                values['pay_full'] = True
            else:
                amount = readings._parse_telegram_amount(text)
            if not math.isfinite(amount) or amount <= 0:
                raise ValidationError('Số tiền phải lớn hơn 0.')
            values['amount'] = amount
            self.write({'step': 'confirm_payment', 'values': values})
            return self._reply(
                f'Thanh toán {amount:,.0f} VND cho '
                f'{values["invoice_number"]}?',
                [['Xác nhận', 'Hủy']],
            )
        if self.step == 'confirm_payment':
            if text != 'Xác nhận':
                raise ValidationError('Bấm Xác nhận hoặc Hủy.')
            if values.get('pay_full'):
                invoice = readings._find_telegram_invoice_by_number(
                    values['invoice_number']
                )
                invoice._lock_for_payment()
                if (
                    invoice.status in ('draft', 'paid')
                    or invoice.remaining_amount != values['amount']
                ):
                    raise ValidationError(
                        'Số dư hoặc trạng thái hóa đơn đã thay đổi. '
                        'Chọn Thanh toán để kiểm tra và xác nhận lại.'
                    )
                result = readings._process_telegram_paid_command(
                    f'paid {values["invoice_number"]}'
                )
            else:
                result = readings._process_telegram_pay_command(
                    f'pay {values["invoice_number"]} {values["amount"]:.0f}'
                )
            self.step = 'menu'
            result['reply_markup'] = self._reply('')['reply_markup']
            return result
        return self._reply('Chọn thao tác từ menu.')
