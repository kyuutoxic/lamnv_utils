from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Refresh stored totals and statuses created with
    the previous behavior.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['room.invoice'].search([])._auto_update_status()
    rooms = env['rental.room'].search([])
    rooms._compute_total_invoiced()
    rooms._compute_total_paid()
    rooms._compute_total_remaining()
