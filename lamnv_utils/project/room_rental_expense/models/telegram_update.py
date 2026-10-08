import hashlib
import secrets

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class RoomTelegramUpdate(models.Model):
    _name = 'room.telegram.update'
    _description = 'Telegram Update Receipt'

    bot_key = fields.Char(required=True)
    update_id = fields.Integer(required=True)
    _bot_update_unique = models.Constraint(
        'unique(bot_key, update_id)',
        'Telegram update đã được xử lý.',
    )

    @api.model
    def _process_update(self, payload):
        """Receipt and business changes commit together;
        retries do not reapply.
        """
        token = (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('room_rental_expense.telegram_bot_token', '')
        )
        bot_key = hashlib.sha256(token.encode()).hexdigest()
        update_id = payload['update_id']
        # Serialize the same update even before a receipt exists.
        self.env.cr.execute(
            'SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
            [f'room.telegram.update:{bot_key}:{update_id}'],
        )
        if self.search_count(
            [('bot_key', '=', bot_key), ('update_id', '=', update_id)]
        ):
            return {'ok': True, 'ignored': True, 'duplicate': True}
        result = self.env['meter.reading'].process_telegram_message(
            payload['message']
        )
        receipt = self.create({'bot_key': bot_key, 'update_id': update_id})
        self.env['room.telegram.outbox']._enqueue(
            receipt, payload['message'], result
        )
        return result

    @api.model
    def _pair_chat(self, message):
        parts = (message.get('text') or '').strip().split()
        chat = message.get('chat') or {}
        sender = message.get('from') or {}
        if (
            len(parts) != 2
            or chat.get('type') != 'private'
            or type(chat.get('id')) is not int
            or chat['id'] <= 0
            or sender.get('id') != chat['id']
        ):
            raise ValidationError(
                'Gửi /connect <mã> trong chat riêng với bot.'
            )
        self.env.cr.execute(
            'SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))',
            ['room.telegram.pairing'],
        )
        icp = self.env['ir.config_parameter'].sudo()
        # Clear parameter caches after waiting for another pairing
        # request.
        self.env.registry.clear_cache()
        digest = icp.get_param('room_rental_expense.telegram_pairing_hash', '')
        expiry = icp.get_param('room_rental_expense.telegram_pairing_expiry')
        token = icp.get_param('room_rental_expense.telegram_bot_token', '')
        bot_key = icp.get_param('room_rental_expense.telegram_pairing_bot', '')
        supplied = hashlib.sha256(parts[1].encode()).hexdigest()
        if (
            not digest
            or not expiry
            or fields.Datetime.to_datetime(expiry) <= fields.Datetime.now()
            or not secrets.compare_digest(digest, supplied)
            or bot_key != hashlib.sha256(token.encode()).hexdigest()
        ):
            raise ValidationError(
                'Mã ghép nối sai hoặc hết hạn. '
                'Tạo mã mới trong Settings Odoo.'
            )
        allowed = icp.get_param(
            'room_rental_expense.telegram_allowed_chat_ids', ''
        )
        ids = [item.strip() for item in allowed.split(',') if item.strip()]
        if str(chat['id']) not in ids:
            ids.append(str(chat['id']))
        icp.set_param(
            'room_rental_expense.telegram_allowed_chat_ids', ','.join(ids)
        )
        for key in (
            'telegram_pairing_hash',
            'telegram_pairing_expiry',
            'telegram_pairing_bot',
        ):
            icp.set_param(f'room_rental_expense.{key}', '')
        return {
            'status': 'success',
            'message': 'Đã ghép nối chat với Odoo. Gửi /help để bắt đầu.',
        }
