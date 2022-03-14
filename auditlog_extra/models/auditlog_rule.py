# -*- coding: utf-8 -*-
from odoo import fields, models, api

EMPTY_DICT = {}


class DictDiffer(object):
    """Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """

    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current = set(current_dict)
        self.set_past = set(past_dict)
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return {o for o in self.intersect if self.past_dict[o] != self.current_dict[o]}

    def unchanged(self):
        return {o for o in self.intersect if self.past_dict[o] == self.current_dict[o]}


class AuditlogRule(models.Model):
    _inherit = "auditlog.rule"

    log_type = fields.Selection(
        selection_add=[('specific_fields', 'Specific fields')],
        ondelete={'specific_fields': 'set default'}
    )

    field_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        domain="[('model_id', '=', model_id), ('store', '=', True)]",
        string='Fields'
    )

    smart_button_view_id = fields.Many2one(
        comodel_name='ir.ui.view',
        string='Smart button view'
    )

    def action_add_smartbutton_on_forms(self):
        if not self.model_id or not self.action_id:
            return
        # Search for an existing view for the model that has the button_box
        model_view = self.env['ir.ui.view'].search([
            ("model", "=", self.model_id.model),
            ('type', "=", "form"),
            ('arch_db', 'ilike', 'name="button_box"')
        ], limit=1, order='id asc')

        # Build XML to insert in new view
        arch = f'<div name="button_box" position="inside"><button type="action" name="{self.action_id.id}" icon="fa-database">Check logs</button></div>'

        if model_view:
            # Remove existing view with smart button so no doubles can be created
            self.env['ir.ui.view'].search([
                ("model", "=", self.model_id.model),
                ('name', "=", 'auditlog.' + model_view.name)]
            ).unlink()

            # Create new view
            view_data = {
                'name': 'auditlog.' + model_view.name,
                'type': 'form',
                'model': self.model_id.model,
                'priority': 1,
                'inherit_id': model_view.id,
                'mode': 'extension',
                'arch_base': arch.encode('utf-8')
            }
            self.smart_button_view_id = self.env["ir.ui.view"].create(view_data).id

    def action_remove_smartbutton_on_forms(self):
        for rule in self:
            rule.smart_button_view_id.unlink()

    def unsubscribe(self):
        # Remove smart buttons on unsubscribe
        self.action_remove_smartbutton_on_forms()
        return super(AuditlogRule, self).unsubscribe()

    def _make_create(self):
        """Instanciate a create method that log its calls."""
        self.ensure_one()
        log_type = self.log_type

        super_return = super(AuditlogRule, self)._make_create()

        @api.model_create_multi
        @api.returns("self", lambda value: value.id)
        def create_specific_fields(self, vals_list, **kwargs):
            self = self.with_context(auditlog_disabled=True)
            rule_model = self.env["auditlog.rule"]
            new_records = create_specific_fields.origin(self, vals_list, **kwargs)
            # Take a snapshot of record values from the cache instead of using
            # 'read()'. It avoids issues with related/computed fields which
            # stored in the database only at the end of the transaction, but
            # their values exist in cache.
            new_values = {}
            for new_record in new_records.sudo():
                new_values.setdefault(new_record.id, {})
                for fname, field in new_record._fields.items():
                    if fname not in fields_list:
                        continue
                    new_values[new_record.id][fname] = field.convert_to_read(
                        new_record[fname], new_record
                    )
            if new_values:
                rule_model.sudo().create_logs(
                    self.env.uid,
                    self._name,
                    new_records.ids,
                    "create",
                    None,
                    new_values,
                    {"log_type": log_type},
                )
            return new_records

        if self.log_type == 'specific_fields':
            fields_list = list(
                f.name
                for f in self.field_ids
                if (not f.compute and not f.related) or f.store
            )
            return create_specific_fields

        return super_return

    def _make_write(self):
        """Instanciate a write method that log its calls."""
        self.ensure_one()
        log_type = self.log_type

        super_return = super(AuditlogRule, self)._make_write()

        def write_specific_fields(self, vals, **kwargs):
            self = self.with_context(auditlog_disabled=True)
            rule_model = self.env["auditlog.rule"]
            old_values = {
                d["id"]: d
                for d in self.sudo()
                    .with_context(prefetch_fields=False)
                    .read(fields_list)
            }
            result = write_specific_fields.origin(self, vals, **kwargs)
            new_values = {
                d["id"]: d
                for d in self.sudo()
                    .with_context(prefetch_fields=False)
                    .read(fields_list)
            }
            if new_values and old_values:
                rule_model.sudo().create_logs(
                    self.env.uid,
                    self._name,
                    self.ids,
                    "write",
                    old_values,
                    new_values,
                    {"log_type": log_type},
                )
            return result

        if self.log_type == 'specific_fields':
            fields_list = list(
                f.name
                for f in self.field_ids
                if (not f.compute and not f.related) or f.store
            )
            return write_specific_fields

        return super_return

    def create_logs(
            self,
            uid,
            res_model,
            res_ids,
            method,
            old_values=None,
            new_values=None,
            additional_log_values=None,
    ):
        """Create logs. `old_values` and `new_values` are dictionaries, e.g:
        {RES_ID: {'FIELD': VALUE, ...}}
        """
        if old_values is None:
            old_values = EMPTY_DICT
        if new_values is None:
            new_values = EMPTY_DICT
        log_model = self.env["auditlog.log"]
        http_request_model = self.env["auditlog.http.request"]
        http_session_model = self.env["auditlog.http.session"]
        for res_id in res_ids:
            model_model = self.env[res_model]
            name = model_model.browse(res_id).name_get()
            model_id = self.pool._auditlog_model_cache[res_model]
            auditlog_rule = self.env["auditlog.rule"].search(
                [("model_id", "=", model_id)]
            )
            res_name = name and name[0] and name[0][1]
            vals = {
                "name": res_name,
                "model_id": self.pool._auditlog_model_cache[res_model],
                "res_id": res_id,
                "method": method,
                "user_id": uid,
                "http_request_id": http_request_model.current_http_request(),
                "http_session_id": http_session_model.current_http_session(),
            }
            vals.update(additional_log_values or {})
            diff = DictDiffer(
                new_values.get(res_id, EMPTY_DICT), old_values.get(res_id, EMPTY_DICT)
            )

            # Don't create a log when method is write and there are no differences
            if not diff.changed() and method == 'write':
                continue

            log = log_model.create(vals)
            if method == "create":
                self._create_log_line_on_create(log, diff.added(), new_values)
            elif method == "read":
                self._create_log_line_on_read(
                    log, list(old_values.get(res_id, EMPTY_DICT).keys()), old_values
                )
            elif method == "write":
                self._create_log_line_on_write(
                    log, diff.changed(), old_values, new_values
                )
            elif method == "unlink" and auditlog_rule.capture_record:
                self._create_log_line_on_read(
                    log, list(old_values.get(res_id, EMPTY_DICT).keys()), old_values
                )
