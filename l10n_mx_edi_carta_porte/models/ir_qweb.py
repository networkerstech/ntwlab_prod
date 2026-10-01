# -*- coding: utf-8 -*-

from lxml import etree
from odoo import _, api, models, modules, fields, tools, SUPERUSER_ID
from odoo.addons.base.models.ir_qweb import keep_query
from markupsafe import Markup, escape

class IrQweb(models.AbstractModel):
    _inherit = 'ir.qweb'

    def _render(self, template: int | str | etree._Element, values: dict | None = None, **options) -> Markup:
        cfdi = super(IrQweb, self)._render(template, values, **options)

        if 'xmlns:cartaporte31' in cfdi:
            cfdi = cfdi.replace('xmlns:cce20', 'xmlns:CartaPorte31')
            cfdi = cfdi.replace('http://www.sat.gob.mx/ComercioExterior20', 'http://www.sat.gob.mx/CartaPorte31')
            cfdi = cfdi.replace('http://www.sat.gob.mx/sitio_internet/cfd/ComercioExterior20/ComercioExterior20.xsd', 'http://www.sat.gob.mx/sitio_internet/cfd/CartaPorte/CartaPorte31.xsd ')

        return cfdi