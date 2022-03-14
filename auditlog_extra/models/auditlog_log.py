# -*- coding: utf-8 -*-
from odoo import fields, models, api
import copy


class AuditlogLog(models.Model):
    _inherit = "auditlog.log"

    log_type = fields.Selection(
        selection_add=[('specific_fields', 'Specific fields')]
    )

    def action_open_record(self):
        return {
            "view_mode": "form",
            "res_model": self.model_id.model,
            "res_id": self.res_id,
            "type": "ir.actions.act_window",
            "target": "self",
        }