from datetime import timedelta

from odoo import api, fields, models


class EnglishSession(models.Model):
    _name = 'english.session'
    _description = 'English Study Session'
    _order = 'id desc'
    _rec_name = 'study_date'

    learner_id = fields.Many2one(
        'english.learner', required=True, ondelete='cascade', index=True,
    )
    study_date = fields.Date(required=True)
    daily_date = fields.Date(index=True, copy=False)
    state = fields.Selection([
        ('preparing', 'Đang chuẩn bị'), ('ready', 'Sẵn sàng'),
        ('active', 'Đang học'), ('done', 'Hoàn thành'),
        ('stopped', 'Đã dừng'), ('failed', 'Dùng bài dự phòng'),
    ], default='active', required=True, index=True)
    level = fields.Selection([
        ('starter', 'Mất gốc'), ('beginner', 'Cơ bản'),
    ], required=True)
    topic = fields.Selection([
        ('daily', 'Đời sống'), ('developer', 'Công việc dev'),
    ], required=True)
    lesson_ids = fields.Many2many('english.lesson', copy=False)
    completed_ids = fields.Many2many(
        'english.lesson', 'english_session_completed_rel',
        'session_id', 'lesson_id', copy=False,
    )
    count = fields.Integer(default=0)
    correct = fields.Integer(default=0)
    skipped = fields.Integer(default=0)
    errors = fields.Integer(default=0)
    notes = fields.Text()
    generation_done = fields.Boolean(default=False)
    ended_at = fields.Datetime()

    _daily_unique = models.Constraint(
        'UNIQUE(learner_id, daily_date)',
        'Only one daily session per learner and date.',
    )

    @api.model
    def _cron_cleanup(self):
        config = self.env['english.configuration']._get_config()
        days = config.retention_days
        if not days:
            return
        cutoff = fields.Datetime.now() - timedelta(days=days)
        for model, states in (
            ('english.delivery', ['sent', 'skipped', 'failed']),
            ('english.job', ['done', 'skipped', 'failed']),
        ):
            self.env[model].sudo().search([
                ('state', 'in', states), ('write_date', '<', cutoff),
            ], limit=1000).unlink()
        self.env['english.api.usage'].sudo().search([
            ('create_date', '<', cutoff),
        ], limit=1000).unlink()
        attempts = self.env['english.attempt'].sudo().search([
            ('graded', '=', True), ('create_date', '<', cutoff),
            ('progress_id.state', '=', 'done'),
            ('progress_id.review_step', '>=', 4),
        ], limit=1000)
        referenced = self.env['english.job'].sudo().search([
            ('attempt_id', 'in', attempts.ids),
        ]).attempt_id
        (attempts - referenced).unlink()
        # Keep session summaries for one year, and active lessons forever.
        self.sudo().search([
            ('state', 'in', ['done', 'stopped', 'failed']),
            ('study_date', '<', fields.Date.today() - timedelta(days=365)),
        ], limit=1000).unlink()
        lessons = self.env['english.lesson'].sudo().search([
            ('generated', '=', True), ('write_date', '<', cutoff),
        ], limit=1000)
        used = self.env['english.progress'].sudo().search([
            ('lesson_id', 'in', lessons.ids),
        ]).lesson_id
        planned = self.sudo().search([
            ('lesson_ids', 'in', lessons.ids),
        ]).lesson_ids
        (lessons - used - planned).unlink()
