from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('daily_english.cron_english_jobs').code = (
        'model._cron_process(interactive=False)'
    )
