# -*- coding: utf-8 -*-
##############################################################################
#                 @author IT Admin
#
##############################################################################

{
    'name': 'Complemento Carta porte',
    'version': '19.1.0',
    'description': ''' 
                    En la factura se puede habilitar si se requiere el complemento carta porte.
                    Se agregan varios campos para llenar la información requerida en el complemento.
                    ''',
    'author': 'IT Admin',
    'website': 'www.itadmin.com.mx',
    'depends': ['l10n_mx_edi', 'l10n_mx_edi', 'l10n_mx_catalogos', 'l10n_mx_edi_extended', 'stock'],
    'data': [
        'data/4.0/cfdi.xml',
        'security/ir.model.access.csv',
        'views/account_move_view.xml',
        'views/product_view.xml',
        'views/report_invoice.xml',
        'views/res_partner_view.xml',
        'views/autotransporte_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
}
