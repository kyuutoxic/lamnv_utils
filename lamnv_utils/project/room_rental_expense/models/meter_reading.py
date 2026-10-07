import re

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MeterReading(models.Model):
    _name = 'meter.reading'
    _description = 'Chỉ Số Công Tơ'
    _rec_name = 'name'
    _order = 'reading_date desc, id desc'

    name = fields.Char(string='Tên', compute='_compute_name', store=True)
    room_id = fields.Many2one(
        'rental.room', string='Phòng Trọ', required=True, ondelete='cascade'
    )
    reading_date = fields.Date(string='Ngày Ghi Chỉ Số', required=True)
    reading_month = fields.Char(
        string='Tháng Ghi Chỉ Số', compute='_compute_reading_month', store=True
    )

    # Điện
    electric_previous = fields.Float(string='Số Điện Tháng Trước (kWh)')
    electric_current = fields.Float(
        string='Số Điện Hiện Tại (kWh)', required=True
    )
    electric_replacement_last = fields.Float(
        string='Chỉ Số Cuối Công Tơ Cũ (kWh)',
        help='Nhập chỉ số cuối cùng trước khi thay công tơ',
    )
    electric_usage = fields.Float(
        string='Lượng Điện Sử Dụng (kWh)',
        compute='_compute_electric_usage',
        inverse='_inverse_electric_usage',
        store=True,
    )
    electric_meter_replaced = fields.Boolean(
        string='Đã Thay Công Tơ Điện?', default=False
    )
    electric_image = fields.Binary(string='Ảnh Công Tơ Điện', attachment=True)
    electric_replacement_note = fields.Text(string='Ghi Chú Thay Công Tơ Điện')
    electric_usage_manual_override = fields.Boolean(
        string='Nhập Tay Điện Sử Dụng', default=False
    )
    electric_usage_manual_value = fields.Float(
        string='Điện Sử Dụng (Nhập Tay)'
    )

    # Nước
    water_previous = fields.Float(string='Số Nước Tháng Trước (m³)')
    water_current = fields.Float(string='Số Nước Hiện Tại (m³)', required=True)
    water_replacement_last = fields.Float(
        string='Chỉ Số Cuối Công Tơ Cũ (m³)',
        help='Nhập chỉ số cuối cùng của công tơ nước trước khi thay',
    )
    water_usage = fields.Float(
        string='Lượng Nước Sử Dụng (m³)',
        compute='_compute_water_usage',
        inverse='_inverse_water_usage',
        store=True,
    )
    water_meter_replaced = fields.Boolean(
        string='Đã Thay Công Tơ Nước?', default=False
    )
    water_image = fields.Binary(string='Ảnh Công Tơ Nước', attachment=True)
    water_replacement_note = fields.Text(string='Ghi Chú Thay Công Tơ Nước')
    water_usage_manual_override = fields.Boolean(
        string='Nhập Tay Nước Sử Dụng', default=False
    )
    water_usage_manual_value = fields.Float(string='Nước Sử Dụng (Nhập Tay)')

    invoice_id = fields.Many2one(
        'room.invoice', string='Hóa Đơn', copy=False, ondelete='set null'
    )
    notes = fields.Text(string='Ghi Chú')
    _locked_fields_after_invoice = {
        'room_id',
        'reading_date',
        'electric_previous',
        'electric_current',
        'electric_replacement_last',
        'electric_usage',
        'electric_meter_replaced',
        'electric_usage_manual_override',
        'electric_usage_manual_value',
        'water_previous',
        'water_current',
        'water_replacement_last',
        'water_usage',
        'water_meter_replaced',
        'water_usage_manual_override',
        'water_usage_manual_value',
    }

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
                reading.reading_month = reading.reading_date.strftime('%m/%Y')

    @api.depends(
        'electric_current',
        'electric_previous',
        'electric_meter_replaced',
        'electric_replacement_last',
        'electric_usage_manual_override',
        'electric_usage_manual_value',
    )
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

    @api.depends(
        'water_current',
        'water_previous',
        'water_meter_replaced',
        'water_replacement_last',
        'water_usage_manual_override',
        'water_usage_manual_value',
    )
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

    @api.constrains(
        'electric_current', 'electric_previous', 'electric_meter_replaced'
    )
    def _check_electric_reading(self):
        for reading in self:
            messages = reading._get_counter_regression_messages()
            electric_message = next(
                (msg for msg in messages if msg.startswith('Số điện')),
                False,
            )
            if electric_message:
                raise ValidationError(electric_message)

    @api.constrains(
        'electric_meter_replaced',
        'electric_replacement_last',
        'electric_previous',
    )
    def _check_electric_replacement(self):
        for reading in self:
            if (
                reading.electric_meter_replaced
                and reading.electric_replacement_last
                and reading.electric_replacement_last
                < (reading.electric_previous or 0.0)
            ):
                raise ValidationError(
                    'Chỉ số cuối của công tơ điện cũ không thể nhỏ hơn '
                    'chỉ số điện tháng trước.'
                )

    @api.constrains('water_current', 'water_previous', 'water_meter_replaced')
    def _check_water_reading(self):
        for reading in self:
            messages = reading._get_counter_regression_messages()
            water_message = next(
                (msg for msg in messages if msg.startswith('Số nước')),
                False,
            )
            if water_message:
                raise ValidationError(water_message)

    @api.constrains(
        'water_meter_replaced', 'water_replacement_last', 'water_previous'
    )
    def _check_water_replacement(self):
        for reading in self:
            if (
                reading.water_meter_replaced
                and reading.water_replacement_last
                and reading.water_replacement_last
                < (reading.water_previous or 0.0)
            ):
                raise ValidationError(
                    'Chỉ số cuối của công tơ nước cũ không thể nhỏ hơn '
                    'chỉ số nước tháng trước.'
                )

    @api.onchange(
        'electric_meter_replaced', 'electric_current', 'electric_previous'
    )
    def _onchange_electric_inputs(self):
        for reading in self:
            if (
                reading.electric_usage_manual_override
                and not reading.env.context.get('keep_manual_electric')
            ):
                continue
            if not reading.electric_usage_manual_override:
                reading.electric_usage = reading._get_auto_electric_usage()
            warning = reading._build_counter_regression_warning(
                target='electric'
            )
            if warning:
                return warning

    @api.onchange('electric_usage_manual_override')
    def _onchange_electric_usage_override(self):
        for reading in self:
            if not reading.electric_usage_manual_override:
                reading.electric_usage_manual_value = 0.0
                reading.electric_usage = reading._get_auto_electric_usage()

    @api.onchange('water_meter_replaced', 'water_current', 'water_previous')
    def _onchange_water_inputs(self):
        for reading in self:
            if (
                reading.water_usage_manual_override
                and not reading.env.context.get('keep_manual_water')
            ):
                continue
            if not reading.water_usage_manual_override:
                reading.water_usage = reading._get_auto_water_usage()
            warning = reading._build_counter_regression_warning(target='water')
            if warning:
                return warning

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
                reading.room_id, reading.reading_date, exclude_id=reading.id
            )
            if previous_reading:
                reading.electric_previous = previous_reading.electric_current
                reading.water_previous = previous_reading.water_current
            else:
                reading.electric_previous = 0.0
                reading.water_previous = 0.0
            warning = reading._build_counter_regression_warning()
            if warning:
                return warning

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        room_id = self.env.context.get('default_room_id')
        reading_date = defaults.get('reading_date') or self.env.context.get(
            'default_reading_date'
        )
        if room_id and (
            'electric_previous' in fields_list
            or 'water_previous' in fields_list
        ):
            if isinstance(reading_date, str):
                reading_date = fields.Date.from_string(reading_date)
            room = self.env['rental.room'].browse(room_id)
            previous = self._get_previous_reading(room, reading_date)
            if previous:
                defaults.setdefault(
                    'electric_previous', previous.electric_current
                )
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
            key=lambda r: (
                r.reading_date or fields.Date.from_string('1970-01-01'),
                r.id,
            ),
            reverse=True,
        )
        return sorted_readings[0]

    @api.model
    def _prepare_previous_counter_vals(
        self, room, reading_date, exclude_id=None
    ):
        previous_reading = self._get_previous_reading(
            room,
            reading_date,
            exclude_id=exclude_id,
        )
        if not previous_reading:
            return {
                'electric_previous': 0.0,
                'water_previous': 0.0,
            }
        return {
            'electric_previous': previous_reading.electric_current,
            'water_previous': previous_reading.water_current,
        }

    def _get_counter_regression_messages(self):
        self.ensure_one()
        messages = []
        if (
            not self.electric_meter_replaced
            and self.electric_previous is not None
            and self.electric_current < self.electric_previous
        ):
            messages.append(
                'Số điện hiện tại không thể nhỏ hơn số tháng trước. '
                'Hãy bật "Đã thay công tơ điện?" nếu công tơ đã được thay.'
            )
        if (
            not self.water_meter_replaced
            and self.water_previous is not None
            and self.water_current < self.water_previous
        ):
            messages.append(
                'Số nước hiện tại không thể nhỏ hơn số tháng trước. '
                'Hãy bật "Đã thay công tơ nước?" nếu công tơ đã được thay.'
            )
        return messages

    def _build_counter_regression_warning(self, target=False):
        self.ensure_one()
        messages = self._get_counter_regression_messages()
        if target == 'electric':
            messages = [msg for msg in messages if msg.startswith('Số điện')]
        elif target == 'water':
            messages = [msg for msg in messages if msg.startswith('Số nước')]
        if not messages:
            return False
        return {
            'warning': {
                'title': 'Chỉ số công tơ không hợp lệ',
                'message': '\n'.join(messages),
            }
        }

    @api.constrains('invoice_id', 'room_id')
    def _check_invoice_room(self):
        for reading in self:
            if (
                reading.invoice_id
                and reading.invoice_id.room_id != reading.room_id
            ):
                raise ValidationError(
                    'Hóa đơn phải thuộc cùng phòng với chỉ số công tơ.'
                )

    def write(self, vals):
        if self._locked_fields_after_invoice.intersection(vals):
            locked = self.filtered('invoice_id')
            if locked:
                raise ValidationError(
                    'Không thể sửa chỉ số công tơ đã được gắn với hóa đơn.'
                )
        return super().write(vals)

    def action_create_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            return self.action_open_invoice()

        invoice = self.env['room.invoice'].create(
            {
                'room_id': self.room_id.id,
                'invoice_month': self.reading_month,
                'invoice_date': self.reading_date
                or fields.Date.context_today(self),
                'meter_reading_id': self.id,
            }
        )
        self.invoice_id = invoice
        return {
            'type': 'ir.actions.act_window',
            'name': f'Hóa Đơn - {invoice.invoice_number}',
            'res_model': 'room.invoice',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise ValidationError(
                'Chỉ số công tơ này chưa có hóa đơn liên kết.'
            )
        return {
            'type': 'ir.actions.act_window',
            'name': f'Hóa Đơn - {self.invoice_id.invoice_number}',
            'res_model': 'room.invoice',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def unlink(self):
        linked = self.filtered('invoice_id')
        if linked:
            raise ValidationError(
                'Không thể xóa chỉ số công tơ đã được gắn với hóa đơn. '
                'Hãy xóa hoặc điều chỉnh hóa đơn trước.'
            )
        return super().unlink()

    @api.model
    def parse_telegram_message(self, text):
        text = (text or '').strip()
        if not text:
            raise ValidationError(
                'Tin nhắn trống. Mẫu đúng: /reading P101 350 28'
            )

        compact_match = re.fullmatch(
            r'(?P<room>\S+)\s+'
            r'(?P<electric>\d+(?:[.,]\d+)?)\s+'
            r'(?P<water>\d+(?:[.,]\d+)?)'
            r'(?:\s+(?P<date>\d{4}-\d{2}-\d{2}))?',
            text,
            flags=re.IGNORECASE,
        )
        verbose_match = re.fullmatch(
            r'room:(?P<room>\S+)\s+'
            r'elec:(?P<electric>\d+(?:[.,]\d+)?)\s+'
            r'water:(?P<water>\d+(?:[.,]\d+)?)'
            r'(?:\s+date:(?P<date>\d{4}-\d{2}-\d{2}))?',
            text,
            flags=re.IGNORECASE,
        )
        match = compact_match or verbose_match
        if not match:
            raise ValidationError(
                'Sai định dạng. Dùng: /reading P101 350 28 hoặc '
                '/reading room:P101 elec:350 water:28'
            )

        try:
            reading_date = (
                fields.Date.to_date(match.group('date'))
                if match.group('date')
                else fields.Date.context_today(self)
            )
        except (TypeError, ValueError):
            raise ValidationError(
                'Ngày ghi chỉ số phải theo định dạng YYYY-MM-DD.'
            )
        return {
            'room_key': match.group('room').strip(),
            'electric_current': float(
                match.group('electric').replace(',', '.')
            ),
            'water_current': float(match.group('water').replace(',', '.')),
            'reading_date': reading_date,
            'raw_text': text,
        }

    @api.model
    def process_telegram_message(self, message):
        text = (message or {}).get('text', '')
        text = (text or '').strip()
        if not text:
            return {
                'status': 'error',
                'message': self._get_telegram_help_message(),
            }
        try:
            payload = {
                'telegram_chat_id': (message.get('chat') or {}).get('id'),
                'telegram_user_id': (message.get('from') or {}).get('id'),
                'raw_text': text,
            }
            with self.env.cr.savepoint():
                if text.split()[0].lower() == '/connect':
                    return self.env['room.telegram.update']._pair_chat(
                        message
                    )
                self._check_telegram_sender_allowed(
                    payload['telegram_chat_id']
                )
                result = self._dispatch_telegram_command(text, payload)
        except ValidationError as err:
            return {
                'status': 'error',
                'message': str(err),
            }
        return result

    @api.model
    def _dispatch_telegram_command(self, text, payload):
        normalized = text.strip()
        upper_text = normalized.upper()
        if not normalized.startswith('/'):
            return {
                'status': 'error',
                'message': self._get_telegram_slash_only_message(),
            }
        if upper_text == '/HELP':
            return {
                'status': 'success',
                'message': self._get_telegram_help_message(),
            }
        if upper_text.startswith('/INV '):
            return self._process_telegram_invoice_command(normalized[1:])
        if upper_text.startswith('/SHOW '):
            return self._process_telegram_show_command(normalized[1:])
        if upper_text.startswith('/INVOICES '):
            return self._process_telegram_invoices_command(normalized[1:])
        if upper_text.startswith('/READINGS '):
            return self._process_telegram_readings_command(normalized[1:])
        if upper_text.startswith('/PAID '):
            return self._process_telegram_paid_command(normalized[1:])
        if upper_text.startswith('/PAY '):
            return self._process_telegram_pay_command(normalized[1:])
        if upper_text.startswith('/UNPAID '):
            return self._process_telegram_unpaid_command(normalized[1:])
        if upper_text.startswith('/READING '):
            return self._process_telegram_reading_command(normalized)

        raise ValidationError(self._get_telegram_slash_only_message())

    @api.model
    def _process_telegram_reading_command(self, text):
        reading_payload = self.parse_telegram_message(
            text[len('/reading '):].strip()
        )
        if not reading_payload:
            raise ValidationError(self._get_telegram_help_message())
        return self._upsert_from_telegram_payload(reading_payload)

    @api.model
    def _get_telegram_slash_only_message(self):
        return '\n'.join(
            [
                'Bot chỉ nhận lệnh bắt đầu bằng "/".',
                'Ví dụ:',
                '/reading P101 350 28',
                '/inv P101 2026-04-14',
                '/show INV-2026-001',
                '/invoices P101',
                '/readings P101',
                'Gõ /help để xem hướng dẫn đầy đủ.',
            ]
        )

    @api.model
    def _get_telegram_help_message(self):
        return '\n'.join(
            [
                'Các lệnh hỗ trợ:',
                '/help - Xem hướng dẫn',
                '/reading P101 350 28',
                '/reading P101 350 28 2026-04-14',
                '/reading room:P101 elec:350 water:28',
                '/inv P101 2026-04-14',
                '/show INV-2026-001',
                '/invoices P101',
                '/readings P101',
                '/paid INV-2026-001',
                '/pay INV-2026-001 1000000',
                '/unpaid INV-2026-001',
            ]
        )

    @api.model
    def _check_telegram_sender_allowed(self, chat_id):
        allowed_chats = (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('room_rental_expense.telegram_allowed_chat_ids')
        )
        if not allowed_chats:
            raise ValidationError(
                'Chưa cấu hình chat Telegram được phép sử dụng.'
            )
        allowed_ids = {
            item.strip() for item in allowed_chats.split(',') if item.strip()
        }
        if str(chat_id) not in allowed_ids:
            raise ValidationError(
                'Chat Telegram này không được phép gửi chỉ số.'
            )

    @api.model
    def _find_room_by_telegram_key(self, room_key):
        room_key = (room_key or '').strip()
        if not room_key:
            raise ValidationError('Không tìm thấy mã phòng trong tin nhắn.')
        domain = [
            '|',
            '|',
            ('telegram_code', '=', room_key),
            ('room_number', '=', room_key),
            ('name', '=', room_key),
        ]
        rooms = self.env['rental.room'].search(domain, limit=2)
        if not rooms:
            raise ValidationError(f'Không tìm thấy phòng "{room_key}".')
        if len(rooms) > 1:
            raise ValidationError(
                f'Mã phòng "{room_key}" đang bị trùng. '
                'Hãy dùng telegram_code duy nhất.'
            )
        return rooms

    @api.model
    def _find_telegram_existing_reading(self, room, reading_date):
        return self.search(
            [
                ('room_id', '=', room.id),
                ('reading_date', '=', reading_date),
            ],
            order='reading_date desc, id desc',
            limit=1,
        )

    @api.model
    def _upsert_from_telegram_payload(self, payload):
        room = self._find_room_by_telegram_key(payload['room_key'])
        reading_date = payload['reading_date']
        existing = self._find_telegram_existing_reading(room, reading_date)
        vals = {
            'room_id': room.id,
            'reading_date': reading_date,
            'electric_current': payload['electric_current'],
            'water_current': payload['water_current'],
        }
        if existing:
            vals.update(
                self._prepare_previous_counter_vals(
                    room,
                    reading_date,
                    exclude_id=existing.id,
                )
            )
            if existing.invoice_id:
                raise ValidationError(
                    'Chỉ số tháng này đã gắn với hóa đơn, không thể cập nhật '
                    'qua Telegram.'
                )
            preview = existing.new(vals)
            regression_messages = preview._get_counter_regression_messages()
            if regression_messages:
                raise ValidationError('\n'.join(regression_messages))
            existing.write(vals)
            reading = existing
            action = 'updated'
        else:
            vals.update(
                self._prepare_previous_counter_vals(room, reading_date)
            )
            preview = self.new(vals)
            regression_messages = preview._get_counter_regression_messages()
            if regression_messages:
                raise ValidationError('\n'.join(regression_messages))
            reading = self.create(vals)
            action = 'created'
        return {
            'status': 'success',
            'action': action,
            'reading_id': reading.id,
            'message': self._build_telegram_success_message(
                reading,
                action=action,
            ),
        }

    @api.model
    def _build_telegram_success_message(self, reading, action='created'):
        room_ref = self._get_telegram_room_reference(reading.room_id)
        action_label = 'Đã cập nhật' if action == 'updated' else 'Đã ghi'
        lines = [
            f'{action_label} chỉ số thành công.',
            f'Phòng: {reading.room_id.display_name}',
        ]
        if room_ref:
            lines.append(f'Mã dùng trên Telegram: {room_ref}')
        lines.extend(
            [
                f'Ngày ghi: {reading.reading_date}',
                f'Tháng: {reading.reading_month}',
                (
                    'Điện: %s -> %s | tiêu thụ: %s'
                    % (
                        self._format_telegram_value(reading.electric_previous),
                        self._format_telegram_value(reading.electric_current),
                        self._format_telegram_value(reading.electric_usage),
                    )
                ),
                (
                    'Nước: %s -> %s | tiêu thụ: %s'
                    % (
                        self._format_telegram_value(reading.water_previous),
                        self._format_telegram_value(reading.water_current),
                        self._format_telegram_value(reading.water_usage),
                    )
                ),
            ]
        )
        if room_ref:
            lines.append(
                f'Lệnh tạo hóa đơn: /inv {room_ref} {reading.reading_date}'
            )
        else:
            lines.append(
                'Phòng này chưa có telegram_code hoặc room_number ngắn để '
                'dùng lệnh /inv. Hãy cấu hình thêm mã Telegram.'
            )
        return '\n'.join(lines)

    @api.model
    def _format_telegram_value(self, value):
        if float(value).is_integer():
            return str(int(value))
        return ('%.2f' % value).rstrip('0').rstrip('.')

    @api.model
    def _find_telegram_invoice_by_number(self, invoice_number):
        invoice_number = (invoice_number or '').strip()
        invoice = self.env['room.invoice'].search(
            [('invoice_number', '=', invoice_number)],
            limit=1,
        )
        if not invoice:
            raise ValidationError(
                f'Không tìm thấy hóa đơn "{invoice_number}".'
            )
        return invoice

    @api.model
    def _get_telegram_room_reference(self, room):
        if room.telegram_code:
            return room.telegram_code
        if room.room_number and ' ' not in room.room_number:
            return room.room_number
        if room.name and ' ' not in room.name:
            return room.name
        return False

    @api.model
    def _find_telegram_reading(self, room_key, reading_date):
        room = self._find_room_by_telegram_key(room_key)
        reading = self._find_telegram_existing_reading(room, reading_date)
        if not reading:
            raise ValidationError(
                f'Không tìm thấy chỉ số của phòng "{room_key}" '
                f'ngày {reading_date}.'
            )
        return reading

    @api.model
    def _process_telegram_invoice_command(self, text):
        parts = text.split()
        if len(parts) != 3:
            raise ValidationError('Sai định dạng. Dùng: /inv P101 2026-04-14')
        _, room_key, date_str = parts
        reading_date = self._parse_telegram_date(date_str)
        reading = self._find_telegram_reading(room_key, reading_date)
        if reading.invoice_id:
            invoice = reading.invoice_id
        else:
            invoice = self.env['room.invoice'].create(
                {
                    'room_id': reading.room_id.id,
                    'invoice_month': reading.reading_month,
                    'invoice_date': (
                        reading.reading_date
                        or fields.Date.context_today(reading)
                    ),
                    'meter_reading_id': reading.id,
                }
            )
            if invoice.status == 'draft' and invoice.total_amount > 0:
                invoice.action_confirm()
        return {
            'status': 'success',
            'invoice_id': invoice.id,
            'message': self._build_telegram_invoice_summary(invoice),
        }

    @api.model
    def _process_telegram_show_command(self, text):
        parts = text.split()
        if len(parts) != 2:
            raise ValidationError('Sai định dạng. Dùng: /show INV-2026-001')
        invoice = self._find_telegram_invoice_by_number(parts[1])
        return {
            'status': 'success',
            'invoice_id': invoice.id,
            'message': self._build_telegram_invoice_summary(invoice),
        }

    @api.model
    def _process_telegram_invoices_command(self, text):
        parts = text.split()
        if len(parts) != 2:
            raise ValidationError('Sai định dạng. Dùng: /invoices P101')
        room = self._find_room_by_telegram_key(parts[1])
        invoices = self.env['room.invoice'].search(
            [('room_id', '=', room.id)],
            order='invoice_period_date desc, invoice_date desc, id desc',
            limit=10,
        )
        return {
            'status': 'success',
            'message': self._build_telegram_invoices_list(room, invoices),
        }

    @api.model
    def _process_telegram_readings_command(self, text):
        parts = text.split()
        if len(parts) != 2:
            raise ValidationError('Sai định dạng. Dùng: /readings P101')
        room = self._find_room_by_telegram_key(parts[1])
        readings = self.search(
            [('room_id', '=', room.id)],
            order='reading_date desc, id desc',
            limit=10,
        )
        return {
            'status': 'success',
            'message': self._build_telegram_readings_list(room, readings),
        }

    @api.model
    def _process_telegram_paid_command(self, text):
        parts = text.split()
        if len(parts) != 2:
            raise ValidationError('Sai định dạng. Dùng: /paid INV-2026-001')
        invoice = self._find_telegram_invoice_by_number(parts[1])
        invoice.action_paid()
        return {
            'status': 'success',
            'invoice_id': invoice.id,
            'message': self._build_telegram_payment_summary(invoice),
        }

    @api.model
    def _process_telegram_pay_command(self, text):
        parts = text.split()
        if len(parts) != 3:
            raise ValidationError(
                'Sai định dạng. Dùng: /pay INV-2026-001 1000000'
            )
        invoice = self._find_telegram_invoice_by_number(parts[1])
        amount = self._parse_telegram_amount(parts[2])
        if amount <= 0:
            raise ValidationError('Số tiền thanh toán phải lớn hơn 0.')
        invoice._lock_for_payment()
        invoice.paid_amount += amount
        invoice._auto_update_status(force_pending=True)
        return {
            'status': 'success',
            'invoice_id': invoice.id,
            'message': self._build_telegram_payment_summary(invoice),
        }

    @api.model
    def _process_telegram_unpaid_command(self, text):
        parts = text.split()
        if len(parts) != 2:
            raise ValidationError('Sai định dạng. Dùng: /unpaid INV-2026-001')
        invoice = self._find_telegram_invoice_by_number(parts[1])
        invoice._lock_for_payment()
        invoice.paid_amount = 0.0
        invoice._auto_update_status(force_pending=True)
        return {
            'status': 'success',
            'invoice_id': invoice.id,
            'message': self._build_telegram_payment_summary(invoice),
        }

    @api.model
    def _build_telegram_invoice_summary(self, invoice):
        invoice.ensure_one()
        lines = [
            f'Hóa đơn: {invoice.invoice_number}',
            f'Phòng: {invoice.room_id.display_name}',
            f'Kỳ: {invoice.invoice_month}',
            f'Trạng thái: {invoice.status}',
            f'Tiền phòng: '
            f'{self._format_telegram_amount(invoice.rent_amount)} VND',
            f'Tiền điện: '
            f'{self._format_telegram_amount(invoice.electric_amount)} VND',
            f'Tiền nước: '
            f'{self._format_telegram_amount(invoice.water_amount)} VND',
            f'Tiện ích khác: '
            f'{self._format_telegram_amount(invoice.utilities_amount)} VND',
            f'Phí khác: '
            f'{self._format_telegram_amount(invoice.other_charges)} VND',
            f'Giảm giá: '
            f'{self._format_telegram_amount(invoice.discount_amount)} VND',
            f'Tổng thanh toán: '
            f'{self._format_telegram_amount(invoice.total_amount)} VND',
            f'Đã thanh toán: '
            f'{self._format_telegram_amount(invoice.paid_amount)} VND',
            f'Còn lại: '
            f'{self._format_telegram_amount(invoice.remaining_amount)} VND',
        ]
        if invoice.manual_breakdown:
            lines.extend(
                [
                    '',
                    'Chi tiết:',
                    invoice.manual_breakdown,
                ]
            )
        lines.extend(
            [
                '',
                (
                    f'Gõ: /paid {invoice.invoice_number} hoặc '
                    f'/pay {invoice.invoice_number} 1000000'
                ),
            ]
        )
        return '\n'.join(lines)

    @api.model
    def _build_telegram_invoices_list(self, room, invoices):
        room.ensure_one()
        if not invoices:
            room_ref = (
                self._get_telegram_room_reference(room) or room.display_name
            )
            return f'Không có hóa đơn nào cho phòng {room_ref}.'
        lines = [
            f'Danh sách hóa đơn của phòng {room.display_name} (tối đa 10):',
        ]
        for invoice in invoices:
            lines.append(
                ' - %s | %s | %s | còn %s VND'
                % (
                    invoice.invoice_number or '',
                    invoice.invoice_month or '',
                    invoice.status or '',
                    self._format_telegram_amount(invoice.remaining_amount),
                )
            )
        lines.append('Dùng /show <số_hóa_đơn> để xem chi tiết.')
        return '\n'.join(lines)

    @api.model
    def _build_telegram_readings_list(self, room, readings):
        room.ensure_one()
        if not readings:
            room_ref = (
                self._get_telegram_room_reference(room) or room.display_name
            )
            return f'Không có chỉ số nào cho phòng {room_ref}.'
        lines = [
            f'Danh sách chỉ số của phòng {room.display_name} (tối đa 10):',
        ]
        for reading in readings:
            lines.append(
                ' - %s | điện %s | nước %s'
                % (
                    reading.reading_date or '',
                    self._format_telegram_value(reading.electric_current),
                    self._format_telegram_value(reading.water_current),
                )
            )
        lines.append(
            'Dùng /inv <mã_phòng> <YYYY-MM-DD> để tạo hóa đơn từ một chỉ số.'
        )
        return '\n'.join(lines)

    @api.model
    def _build_telegram_payment_summary(self, invoice):
        invoice.ensure_one()
        lines = [
            f'Đã cập nhật hóa đơn {invoice.invoice_number}.',
            f'Trạng thái: {invoice.status}',
            f'Đã thanh toán: '
            f'{self._format_telegram_amount(invoice.paid_amount)} VND',
            f'Còn lại: '
            f'{self._format_telegram_amount(invoice.remaining_amount)} VND',
        ]
        return '\n'.join(lines)

    @api.model
    def _parse_telegram_date(self, date_str):
        try:
            return fields.Date.to_date(date_str)
        except (TypeError, ValueError):
            raise ValidationError('Ngày phải theo định dạng YYYY-MM-DD.')

    @api.model
    def _parse_telegram_amount(self, amount_str):
        try:
            normalized = amount_str.replace('.', '').replace(',', '')
            return float(normalized)
        except (AttributeError, ValueError):
            raise ValidationError('Số tiền thanh toán không hợp lệ.')

    @api.model
    def _format_telegram_amount(self, value):
        return "{:,.0f}".format(value).replace(',', '.')
