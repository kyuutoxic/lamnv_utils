import hashlib

from odoo import api, fields, models


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
        self.create({'bot_key': bot_key, 'update_id': update_id})
        return result
