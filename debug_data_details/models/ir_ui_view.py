
from lxml import etree
from lxml.builder import E
from odoo import models, api, _
from odoo.tools import frozendict
from odoo.exceptions import UserError


class Model(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _get_default_debug_form_view(self):
        """ Generates a default single-line form view using all fields
        of the current model.

        :returns: a form view as an lxml document
        :rtype: etree._Element
        """
        group = E.group(col="4")
        for fname, field in self._fields.items():
            # In base form view has issue.
            if fname =='needed_terms' and field.type == 'binary':
                continue
            if field.automatic:
                continue
            elif field.type in ('one2many', 'many2many', 'text', 'html'):
                group.append(E.newline())
                group.append(E.field(name=fname, colspan="4"))
                group.append(E.newline())
            else:
                group.append(E.field(name=fname, colspan="4"))
        group.append(E.separator())
        return E.form(E.sheet(group, string=self._description))

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        if options.get('open_all_data', False):
            self.check_access_rights('read')
            result = dict(self._get_debug_view_cache(view_id, view_type, **options))
            node = etree.fromstring(result['arch'])
            node = self.env['ir.ui.view']._postprocess_access_rights(node)
            node = self.env['ir.ui.view']._postprocess_context_dependent(node)
            result['arch'] = etree.tostring(node, encoding="unicode").replace('\t', '')
            return result
        return  super(Model, self).get_view(view_id, view_type, **options)

    @api.model
    def _get_debug_view_cache(self, view_id=None, view_type='form', **options):
        # Get the view arch and all other attributes describing the composition of the view
        View = self.env['ir.ui.view'].sudo()
        view = View.browse()
        try:
            arch = getattr(self, '_get_default_debug_%s_view' % view_type)()
        except AttributeError:
            raise UserError(_("No default view of type '%s' could be found !", view_type))
        
        # Apply post processing, groups and modifiers etc...
        arch, models = view.postprocess_and_fields(arch, model=self._name, **options)
        models = self._get_view_fields(view_type or view.type, models)
        result = {
            'arch': arch,
            # TODO: only `web_studio` seems to require this. I guess this is acceptable to keep it.
            'id': view.id,
            # TODO: only `web_studio` seems to require this. But this one on the other hand should be eliminated:
            # you just called `get_views` for that model, so obviously the web client already knows the model.
            'model': self._name,
            # Set a frozendict and tuple for the field list to make sure the value in cache cannot be updated.
            'models': frozendict({model: tuple(fields) for model, fields in models.items()}),
        }
        return frozendict(result)
