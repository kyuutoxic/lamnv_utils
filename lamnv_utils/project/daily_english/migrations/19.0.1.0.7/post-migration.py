from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for topic in ('daily', 'developer'):
        for level in ('starter', 'beginner'):
            for start in (1, 6):
                lessons = [env.ref(
                    f'daily_english.practice_{level}_{topic}_{n}',
                    raise_if_not_found=False,
                ) for n in range(start, start + 5)]
                for index, lesson in enumerate(lessons):
                    other = lessons[(index + 1) % 5]
                    if not lesson or not other:
                        continue
                    old = f'{lesson.answer} — {lesson.name}.'
                    if lesson.sample_answers == old:
                        lesson.sample_answers = (
                            f'{other.answer} — {other.name}.'
                        )
    # Legacy queued jobs lack cancellation identity; do not replay them.
    jobs = env['english.job'].search([
        ('state', '=', 'pending'), ('request_level', '=', False),
    ])
    for job in jobs:
        job._release_question()
    jobs.write({'state': 'skipped', 'error_code': 'upgrade_legacy_job'})
