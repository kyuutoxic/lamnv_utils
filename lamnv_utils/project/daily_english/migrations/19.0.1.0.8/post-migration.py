from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Preserve existing answers; old generation has no curriculum snapshot.
    env['english.job'].search([
        ('kind', 'in', ['generate', 'prepare']),
        ('state', 'in', ['pending', 'running']),
        ('unit_id', '=', False),
        ('learner_id.curriculum_enabled', '=', True),
    ]).write({'state': 'skipped', 'error_code': 'curriculum_upgrade'})
