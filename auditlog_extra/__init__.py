# -*- coding: utf-8 -*-
from . import models
from odoo import api, SUPERUSER_ID


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Unlink all view created by this module
    env['auditlog.rule'].search([]).smart_button_view_id.unlink()
