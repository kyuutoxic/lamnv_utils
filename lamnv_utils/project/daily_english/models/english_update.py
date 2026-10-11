import hashlib
import secrets

from odoo import api, fields, models


class EnglishUpdate(models.Model):
    _name = 'english.update'
    _description = 'English Telegram Receipt'
    _rec_name = 'update_id'

    update_id = fields.Integer(required=True, index=True)
    bot_hash = fields.Char(required=True)

    _update_unique = models.Constraint(
        'UNIQUE(bot_hash, update_id)', 'Update already processed.'
    )

    @api.model
    def _process(self, payload):
        config = self.env['english.configuration']._get_config()
        bot_hash = hashlib.sha256(
            (config.telegram_token or '').encode()
        ).hexdigest()
        update_id = payload['update_id']
        message = payload['message']
        chat_id = str(message['chat']['id'])
        text = message['text'].strip()
        self.env.cr.execute(
            'SELECT pg_advisory_xact_lock(hashtext(%s))',
            [f'daily_english.update:{bot_hash}:{update_id}'],
        )
        if self.search_count([
            ('bot_hash', '=', bot_hash), ('update_id', '=', update_id),
        ]):
            return
        self.create({'bot_hash': bot_hash, 'update_id': update_id})
        learners = self.env['english.learner']
        if text.split()[0].split('@')[0].lower() == '/connect':
            code = text.partition(' ')[2].strip()
            if not code:
                return
            digest = hashlib.sha256(code.encode()).hexdigest()
            learner = learners.search([
                ('pairing_hash', '=', digest),
                ('pairing_bot_hash', '=', bot_hash),
                ('pairing_expiry', '>', fields.Datetime.now()),
            ], limit=1)
            if not learner:
                return
            learner._lock()
            if (
                not learner.pairing_hash
                or not secrets.compare_digest(learner.pairing_hash, digest)
                or learner.pairing_expiry <= fields.Datetime.now()
            ):
                return
            self.env.cr.execute(
                'SELECT pg_advisory_xact_lock(hashtext(%s))',
                [f'daily_english.chat:{chat_id}'],
            )
            owner = learners.with_context(active_test=False).search([
                ('chat_id', '=', chat_id),
            ], limit=1)
            if owner and owner != learner:
                return
            learner.write({
                'chat_id': chat_id, 'bot_hash': bot_hash,
                'pairing_hash': False, 'pairing_bot_hash': False,
                'pairing_expiry': False, 'pairing_command': False,
            })
            learner._reply('Đã kết nối! Gửi /lesson để học bài đầu tiên.')
            return
        learner = learners.search([
            ('chat_id', '=', chat_id), ('bot_hash', '=', bot_hash),
        ], limit=1)
        if learner:
            learner._lock()
            learner._handle_text(text)
