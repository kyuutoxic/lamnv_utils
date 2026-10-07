import hashlib

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    token = env['ir.config_parameter'].get_param(
        'room_rental_expense.telegram_bot_token', ''
    )
    if token:
        key = hashlib.sha256(token.encode()).hexdigest()
        env['room.telegram.reminder'].search(
            [
                ('bot_key', '=', 'legacy'),
            ]
        ).write({'bot_key': key})
