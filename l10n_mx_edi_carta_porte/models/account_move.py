# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from lxml import etree
from reportlab.graphics.barcode import createBarcodeDrawing, getCodes
from reportlab.lib.units import mm
import uuid
import pytz
from odoo import tools
import base64

import logging
_logger = logging.getLogger(__name__)

class CfdiTrasladoLine(models.Model):
    _name = "cp.traslado.line"
    _description = 'CfdiTrasladoLine'

    cfdi_traslado_id= fields.Many2one(comodel_name='account.move',string="CFDI Traslado")
    product_id = fields.Many2one('product.product',string='Producto',required=True)
    name = fields.Text(string='Descripción',required=True,)
    quantity = fields.Float(string='Cantidad', digits='Product Unit',required=True, default=1)
    price_unit = fields.Float(string='Precio unitario', required=True, digits='Product Price')
    invoice_line_tax_ids = fields.Many2many('account.tax',string='Taxes')
    currency_id = fields.Many2one('res.currency', related='cfdi_traslado_id.currency_id', store=True, related_sudo=False, readonly=False)
    price_subtotal = fields.Monetary(string='Subtotal',
        store=True, readonly=True, compute='_compute_price', help="Subtotal")
    price_total = fields.Monetary(string='Cantidad (con Impuestos)',
        store=True, readonly=True, compute='_compute_price', help="Cantidad total con impuestos")
    pesoenkg = fields.Float(string='Peso Kg', digits='Product Price')
    guias_line_ids = fields.Many2many('cp.guias.line', string='Guías', copy=True)
    aduanera_line_ids = fields.Many2many('cp.aduanera.line', string='Inf. Aduanera', copy=True)
    transporta_line_ids = fields.Many2many('cp.transporta.line', string='Cant. Trans.', copy=True)
    moneda = fields.Selection(
        selection=[('MXN', 'MXN'), 
                   ('USD', 'USD'), 
                   ('EUR', 'EUR'),
                   ('CAD', 'CAD')
                  ],
        string='Moneda',
        default = 'MXN'
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self.name = self.product_id.partner_ref
        company_id = self.env.user.company_id
        taxes = self.product_id.taxes_id.filtered(lambda r: r.company_id == company_id)
        self.invoice_line_tax_ids = fp_taxes = taxes
        fix_price = self.env['account.tax']._fix_tax_included_price
        self.price_unit = fix_price(self.product_id.lst_price, taxes, fp_taxes)
        self.pesoenkg = self.product_id.weight

    @api.depends('price_unit', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'cfdi_traslado_id.partner_id', 'cfdi_traslado_id.currency_id',)
    def _compute_price(self):
        for line in self:
            currency = line.cfdi_traslado_id and line.cfdi_traslado_id.currency_id or None
            price = line.price_unit
            taxes = False
            if line.invoice_line_tax_ids:
                taxes = line.invoice_line_tax_ids.compute_all(price, currency, line.quantity, product=line.product_id, partner=line.cfdi_traslado_id.partner_id)
            line.price_subtotal = taxes['total_excluded'] if taxes else line.quantity * price
            line.price_total = taxes['total_included'] if taxes else line.price_subtotal

    @api.onchange('quantity')
    def _onchange_quantity(self):
        self.pesoenkg = self.product_id.weight * self.quantity

class CCPUbicacionesLine(models.Model):
    _name = "cp.ubicaciones.line"
    _description = 'CCPUbicacionesLine'
    
    cfdi_traslado_id= fields.Many2one(comodel_name='account.move',string="CFDI Traslado")
    tipoubicacion = fields.Selection(
        selection=[('Origen', 'Origen'), 
                   ('Destino', 'Destino'),],
        string='Tipo Ubicación', required=True
    )
    contacto = fields.Many2one('res.partner',string="Remitente / Destinatario", required=True)
    numestacion = fields.Many2one('cve.estaciones',string='Número de estación')
    fecha = fields.Datetime(string='Fecha Salida / Llegada', required=True)
    tipoestacion = fields.Many2one('cve.estacion',string='Tipo estación')
    distanciarecorrida = fields.Float(string='Distancia recorrida')
    tipo_transporte = fields.Selection(
        selection=[('01', 'Autotransporte'), 
                  # ('02', 'Marítimo'), 
                   ('03', 'Aereo'),
                   #('04', 'Ferroviario')
                  ],
        string='Tipo de transporte'
    )
    idubicacion = fields.Char(string='ID Ubicacion')

class CCPRemolqueLine(models.Model):
    _name = "cp.remolques.line"
    _description = 'CCPRemolqueLine'

    cfdi_traslado_id= fields.Many2one(comodel_name='account.move',string="CFDI Traslado")
    subtipo_id = fields.Many2one('cve.remolque.semiremolque',string="Subtipo")
    placa = fields.Char(string='Placa')

class CCPPropietariosLine(models.Model):
    _name = "cp.figura.line"
    _description = 'CCPPropietariosLine'

    cfdi_traslado_id= fields.Many2one(comodel_name='account.move',string="CFDI Traslado")
    figura_id = fields.Many2one('res.partner',string="Contacto")
    tipofigura = fields.Many2one('cve.figura.transporte',string="Tipo figura")
    partetransporte = fields.Many2many('cve.parte.transporte',string="Parte transporte")

class CfdiAduaneraLine(models.Model):
    _name = "cp.aduanera.line"
    _description = 'CCPAduaneraLine'
    _rec_name = "pedimento"

    cfdi_traslado_id= fields.Many2one(comodel_name='account.move',string="CFDI Traslado")
    tipo_documento_id = fields.Many2one('ccp.tipo.documento',string='Tipo de documento',required=True)
    pedimento = fields.Text(string='Pedimento')
    id_doc_aduanero = fields.Text(string='Identificador documento aduanero')
    rfc_import = fields.Text(string='RFC de importador')

class CfdiTransportaLine(models.Model):
    _name = "cp.transporta.line"
    _description = "CCPTransportaLine"
    _rec_name = "name"

    cfdi_traslado_id= fields.Many2one(comodel_name='account.move',string="CFDI Traslado")
    cantidad = fields.Float(string='Cantidad')
    idorigen = fields.Char(string='ID Origen')
    iddestino = fields.Char(string='ID Destino')
    name = fields.Char(string='Nombre')

class CfdiGuiasLine(models.Model):
    _name = "cp.guias.line"
    _description = "CCPguiasLine"
    _rec_name = "guiaid_numero"

    cfdi_traslado_id= fields.Many2one(comodel_name='account.move',string="CFDI Traslado")
    guiaid_numero = fields.Char(string='No. Guia')
    guiaid_descrip = fields.Char(string='Descr. guia')
    guiaid_peso = fields.Float(string='Peso guia')

    @api.onchange('guiaid_numero')
    def _compute_no_guia(self):
        for rec in self:
            if rec.guiaid_numero:
                if len(rec.guiaid_numero) < 10:
                    raise UserError(_('El número de guia debe ser mayor de 10 y menor de 30 caracteres.'))

class CCPAduaneroLine(models.Model):
    _name = "cp.aduanero.line"
    _description = "CCPAduaneroLine"

    cfdi_traslado_id= fields.Many2one(comodel_name='account.move',string="CFDI Traslado")
    regimen_aduanero = fields.Many2one('ccp.regimen.aduanero',string='Regimen aduanero')

class AccountMove(models.Model):
    _inherit = 'account.move'

    factura_line_ids = fields.One2many(comodel_name='cp.traslado.line', inverse_name='cfdi_traslado_id', string='CFDI Traslado Line', copy=True)
    tipo_transporte = fields.Selection(
        selection=[('01', 'Autotransporte'), 
                  # ('02', 'Marítimo'), 
                   ('03', 'Aereo'),
                  # ('04', 'Ferroviario')
                  ],
        string='Tipo de transporte',required=True, default='01'
    )
    carta_porte = fields.Boolean('Agregar carta porte', default = False)

    ##### atributos CP 
    transpinternac = fields.Selection(
        selection=[('Sí', 'Si'), 
                   ('No', 'No'),],
        string='¿Es un transporte internacional?', default='No',
    )
    entradasalidamerc = fields.Selection(
        selection=[('Entrada', 'Entrada'), 
                   ('Salida', 'Salida'),],
        string='¿Las mercancías ingresan o salen del territorio nacional?',
    )
    viaentradasalida = fields.Many2one('cve.transporte',string='Vía de ingreso / salida')
    totaldistrec = fields.Float(string='Distancia recorrida')

    ##### ubicaciones CP
    ubicaciones_line_ids = fields.One2many(comodel_name='cp.ubicaciones.line', inverse_name='cfdi_traslado_id', string='Ubicaciones', copy=True)

    ##### mercancias CP
    pesobrutototal = fields.Float(string='Peso bruto total', compute='_compute_pesobruto')
    unidadpeso = fields.Many2one('cve.clave.unidad',string='Unidad peso')
    pesonetototal = fields.Float(string='Peso neto total')
    numerototalmercancias = fields.Float(string='Numero total de mercancías', compute='_compute_mercancia')
    cargoportasacion = fields.Float(string='Cargo por tasación')

    #transporte
    permisosct = fields.Many2one('cve.tipo.permiso',string='Permiso SCT')
    numpermisosct = fields.Char(string='Número de permiso SCT')

    #autotransporte
    autotrasporte_ids = fields.Many2one('cp.autotransporte',string='Unidad')
    remolque_line_ids = fields.One2many(comodel_name='cp.remolques.line', inverse_name='cfdi_traslado_id', string='Remolque', copy=True)
    nombreaseg_merc = fields.Char(string='Nombre de la aseguradora')
    numpoliza_merc = fields.Char(string='Número de póliza')
    primaseguro_merc = fields.Float(string='Prima del seguro')
    seguro_ambiente = fields.Char(string='Nombre aseguradora')
    poliza_ambiente = fields.Char(string='Póliza no.')

    ##### Aereo CP
    numeroguia = fields.Char(string='Número de guía')
    lugarcontrato = fields.Char(string='Lugar de contrato')
    matriculaaeronave = fields.Char(string='Matrícula Aeronave')
    transportista_id = fields.Many2one('res.partner',string="Transportista")
    embarcador_id = fields.Many2one('res.partner',string="Embarcador")

    uuidcomercioext = fields.Char(string='UUID Comercio Exterior')
    paisorigendestino = fields.Many2one('res.country', string='País Origen / Destino')

    # figura transporte
    figuratransporte_ids = fields.One2many(comodel_name='cp.figura.line', inverse_name='cfdi_traslado_id', string='Seguro mercancías', copy=True)
    IdCCP = fields.Char(string='IdCCP', readonly=True, copy=False)

    regimen_aduanero = fields.Many2one('ccp.regimen.aduanero',string='Regimen aduanero') # archivar en siguientes versiones
    aduanero_line_ids = fields.One2many('cp.aduanero.line', 'cfdi_traslado_id', string='Regimen aduanero', copy=True)
    LogisticaInversa = fields.Selection(
        selection=[('Sí', 'Si'),],
        string='Logistica Inversa Recoleccion Devolucion',
    )
    qr_ccp_value = fields.Char(string='QR CCP', copy=False)
    qrcode_ccp_image = fields.Binary("QRCode CCP", copy=False)
    aduanera_line_ids = fields.One2many(comodel_name='cp.aduanera.line', inverse_name='cfdi_traslado_id', string='CFDI Aduanera Line', copy=True)
    guias_line_ids = fields.One2many(comodel_name='cp.guias.line', inverse_name='cfdi_traslado_id', string='CFDI Guias Line', copy=True)
    manejodeguias = fields.Boolean('Manejo de guías')
    transporta_line_ids = fields.One2many(comodel_name='cp.transporta.line', inverse_name='cfdi_traslado_id', string='CFDI Transporte Line', copy=True)
    manejodeids = fields.Boolean('Manejo de IDs')

    @api.onchange('factura_line_ids')
    def _compute_pesobruto(self):
        for invoice in self:
           peso = 0
           if invoice.carta_porte:
              if invoice.factura_line_ids:
                  for line in invoice.factura_line_ids:
                     peso += line.pesoenkg
              invoice.pesobrutototal = peso
           else:
              invoice.pesobrutototal = peso

    @api.onchange('factura_line_ids')
    def _compute_mercancia(self):
        for invoice in self:
           cant = 0
           if invoice.carta_porte:
              if invoice.factura_line_ids:
                  for line in invoice.factura_line_ids:
                      cant += 1
              invoice.numerototalmercancias = cant
           else:
              invoice.numerototalmercancias = cant

    def _l10n_mx_edi_add_invoice_cfdi_values(self, cfdi_values):
        # EXTENDS 'l10n_mx_edi'
        self.ensure_one()
        super()._l10n_mx_edi_add_invoice_cfdi_values(cfdi_values)
        comp_construccion = cfdi_values['carta_porte'] = {}
        for invoice in self:
          if invoice.carta_porte:
             invoice.totaldistrec = 0
             if not invoice.IdCCP:
              invoice.IdCCP = str(uuid.uuid4()).upper()
              invoice.IdCCP = invoice.IdCCP[:0] + 'CCC' + invoice.IdCCP[3:]

             cp_ubicacion = []
             for ubicacion in invoice.ubicaciones_line_ids:

                 #corregir hora
                 timezone = invoice._context.get('tz')
                 if not timezone:
                    timezone = invoice.env.user.partner_id.tz or 'America/Mexico_City'
                 local = pytz.timezone(timezone)
                 local_dt_from = ubicacion.fecha.replace(tzinfo=pytz.UTC).astimezone(local)
                 date_fecha = local_dt_from.strftime ("%Y-%m-%dT%H:%M:%S")
                 invoice.totaldistrec += float(ubicacion.distanciarecorrida)
                 #_logger.info('totaldistrec %s', invoice.totaldistrec)
                 cp_ubicacion.append({
                                 'TipoUbicacion': ubicacion.tipoubicacion,
                                 'IDUbicacion': ubicacion.idubicacion,
                                 'RFCRemitenteDestinatario': ubicacion.contacto.vat,
                                 'NombreRemitenteDestinatario': ubicacion.contacto.name,
                                 'NumRegIdTrib': ubicacion.contacto.vat if ubicacion.contacto.country_id.l10n_mx_edi_code != 'MEX' else '',
                                 'ResidenciaFiscal': ubicacion.contacto.country_id.l10n_mx_edi_code if ubicacion.contacto.country_id.l10n_mx_edi_code != 'MEX' else '',
                                 'NumEstacion': invoice.tipo_transporte != '01' and ubicacion.numestacion.clave_identificacion or '',
                                 'NombreEstacion': invoice.tipo_transporte != '01' and ubicacion.numestacion.descripcion or '',
                               # 'NavegacionTrafico': invoice.company_id.zip,
                                 'FechaHoraSalidaLlegada': date_fecha,
                                 'TipoEstacion': invoice.tipo_transporte != '01' and ubicacion.tipoestacion.c_estacion or '',
                                 'DistanciaRecorrida': ubicacion.distanciarecorrida > 0 and ubicacion.distanciarecorrida or '',
                                 'Domicilio': {
                                     'Calle': ubicacion.contacto.street_name,
                                     'NumeroExterior': ubicacion.contacto.street_number,
                                     'NumeroInterior': ubicacion.contacto.street_number2,
                                     'Colonia': ubicacion.contacto.l10n_mx_edi_colony_code if ubicacion.contacto.country_id.l10n_mx_edi_code == 'MEX' else ubicacion.contacto.l10n_mx_edi_colony or '',
                                     'Localidad': ubicacion.contacto.l10n_mx_edi_locality_id.code if ubicacion.contacto.country_id.l10n_mx_edi_code == 'MEX' else ubicacion.contacto.l10n_mx_edi_locality,
                               #      'Referencia': self.company_id.cce_clave_estado.c_estado,
                                     'Municipio': ubicacion.contacto.city_id.l10n_mx_edi_code if ubicacion.contacto.country_id.l10n_mx_edi_code == 'MEX' else ubicacion.contacto.city,
                                     'Estado': ubicacion.contacto.state_id.code if ubicacion.contacto.country_id.l10n_mx_edi_code in ('MEX', 'USA', 'CAN') or ubicacion.contacto.state_id.code else 'NA',
                                     'Pais': ubicacion.contacto.country_id.l10n_mx_edi_code,
                                     'CodigoPostal': ubicacion.contacto.zip,
                                 },
                              })

             #################  Atributos y Ubicacion ############################
        #     if self.tipo_transporte == '01' or self.tipo_transporte == '04':
             cartaporte31= {
                            'IdCCP': invoice.IdCCP,
                            'TranspInternac': invoice.transpinternac,
                         #  'RegimenAduanero': invoice.regimen_aduanero.clave,
                            'EntradaSalidaMerc': invoice.entradasalidamerc,
                            'ViaEntradaSalida': invoice.viaentradasalida.c_transporte,
                            'TotalDistRec': invoice.tipo_transporte == '01' and invoice.totaldistrec or '',
                            'PaisOrigenDestino': invoice.paisorigendestino.l10n_mx_edi_code,
                           }

             if invoice.aduanero_line_ids:
                cp_aduanero = []
                for aduanero in self.aduanero_line_ids:
                    cp_aduanero.append({
                                    'RegimenAduanero': aduanero.regimen_aduanero.clave,
                                 })
                cartaporte31.update({'Aduaneros': cp_aduanero})

             cartaporte31.update({'Ubicaciones': cp_ubicacion})

             #################  Mercancias ############################
             mercancias = { 
                            'PesoBrutoTotal': invoice.pesobrutototal, #solo si es aereo o ferroviario
                            'UnidadPeso': invoice.unidadpeso.clave,
                            'PesoNetoTotal': invoice.pesonetototal if invoice.pesonetototal > 0 else '',
                            'NumTotalMercancias': int(invoice.numerototalmercancias),
                            'CargoPorTasacion': invoice.cargoportasacion if invoice.cargoportasacion > 0 else '',
                            'LogisticaInversa': invoice.LogisticaInversa,
             }

             mercancia = []
             mercancia_atributos = []
             for line in invoice.factura_line_ids:
                 if line.quantity <= 0:
                     continue

                 #################  Guias ############################
                 guias = []
                 for guia_line in line.guias_line_ids:
                     guias.append({
                               'NumeroGuiaIdentificacion': guia_line.guiaid_numero,
                               'DescripGuiaIdentificacion': guia_line.guiaid_descrip,
                               'PesoGuiaIdentificacion': guia_line.guiaid_peso,
                     })

                 #################  Pedimentos ############################
                 pedimentos = []
                 for aduanera_line in line.aduanera_line_ids:
                     pedimentos.append({
                               'TipoDocumento': aduanera_line.tipo_documento_id.clave,
                               'NumPedimento': aduanera_line.pedimento[:2] + '  ' + aduanera_line.pedimento[2:4] + '  ' + aduanera_line.pedimento[4:8] + '  ' + aduanera_line.pedimento[8:],
                               'IdentDocAduanero': aduanera_line.id_doc_aduanero,
                               'RFCImpo': aduanera_line.rfc_import,
                     })

                 #################  CantidadTransporta ############################
                 transporta = []
                 for transporta_line in line.transporta_line_ids:
                     transporta.append({
                                'Cantidad': transporta_line.cantidad,
                                'IDOrigen': transporta_line.idorigen,
                                'IDDestino': transporta_line.iddestino,
                                #'CvesTransporte': merc.valorunitarioaduana,
                     })

                 #################  DetalleMercancia ############################
           #      mercancia_detalle = {
           #                          'UnidadPesoMerc': merc.product_id.code,
           #                          'PesoBruto': merc.fraccionarancelaria.c_fraccionarancelaria,
           #                          'PesoNeto': merc.cantidadaduana,
           #                          'PesoTara': merc.valorunitarioaduana,
           #                          'NumPiezas': merc.valordolares,
           #      }

                 mercancia_atributos.append({
                                 'BienesTransp': line.product_id.unspsc_code_id.code,
                                 'ClaveSTCC': line.product_id.clave_stcc,
                                 'Descripcion': self.clean_text(line.product_id.name),
                                 'Cantidad': line.quantity,
                                 'ClaveUnidad': line.product_id.uom_id.unspsc_code_id.code,
                                 'Unidad': line.product_id.uom_id.name,
                                 'Dimensiones': line.product_id.dimensiones or '',
                                 'MaterialPeligroso': line.product_id.materialpeligroso or '',
                                 'CveMaterialPeligroso': line.product_id.clavematpeligroso.clave or '',
                                 'Embalaje': line.product_id.embalaje.clave or '',
                                 'DescripEmbalaje': line.product_id.desc_embalaje or '',
                                 'PesoEnKg': line.pesoenkg,
                                 'ValorMercancia': line.price_subtotal,
                                 'Moneda': invoice.currency_id.name,
                                 'FraccionArancelaria': line.product_id.l10n_mx_edi_tariff_fraction_id.code if invoice.transpinternac == 'Sí' else '',
                                 'UUIDComercioExt': invoice.uuidcomercioext,
                                 'SectorCofepris': line.product_id.SectorCofepris.clave,
                                 'IngredienteActivo': line.product_id.IngredienteActivo,
                                 'NomQuimico': line.product_id.NomQuimico,
                                 'DenominacionGenerica': line.product_id.DenominacionGenerica,
                                 'DenominacionDistintiva': line.product_id.DenominacionDistintiva,
                                 'Fabricante': line.product_id.Fabricante,
                                 'FechaCaducidad': line.product_id.FechaCaducidad,
                                 'LoteMedicamento': line.product_id.LoteMedicamento,
                                 'FormaFarmaceutica': line.product_id.FormaFarmaceutica.clave,
                                 'CondicionesEsp': line.product_id.CondicionesEsp.clave,
                                 'RegistroSanitario': line.product_id.RegistroSanitario,
                                 'PermisoImportacion': line.product_id.PermisoImportacion,
                                 'FolioImpoVUCEM': line.product_id.FolioImpoVUCEM,
                                 'NumCAS': line.product_id.NumCAS,
                                 'RazonSocialEmpImp': line.product_id.RazonSocialEmpImp,
                                 'NumRegSan': line.product_id.NumRegSan,
                                 'DatosFabricante': line.product_id.DatosFabricante,
                                 'DatosFormulador': line.product_id.DatosFormulador,
                                 'DatosMaquilador': line.product_id.DatosMaquilador,
                                 'UsoAutorizado': line.product_id.UsoAutorizado,
                                 'TipoMateria': line.product_id.TipoMateria.clave,
                                 'DescripcionMateria': line.product_id.DescripcionMateria,
                                 'GuiasIdentificacion': guias,
                                 'DocumentacionAduanera': pedimentos,
                                 'CantidadTransporta': transporta,
                 })
             mercancias.update({'mercancia': {'atributos': mercancia_atributos}})

             if invoice.tipo_transporte == '01': #autotransporte
                   transpote_detalle = {
                                 'PermSCT': invoice.permisosct.clave,
                                 'NumPermisoSCT': invoice.numpermisosct,
                                 'IdentificacionVehicular': {
                                      'ConfigVehicular': invoice.autotrasporte_ids.confvehicular.clave,
                                      'PesoBrutoVehicular': invoice.autotrasporte_ids.PesoBrutoVehicular,
                                      'PlacaVM': invoice.autotrasporte_ids.placavm,
                                      'AnioModeloVM': invoice.autotrasporte_ids.aniomodelo,
                                 },
                                 'Seguros': {
                                      'AseguraRespCivil': invoice.autotrasporte_ids.nombreaseg,
                                      'PolizaRespCivil': invoice.autotrasporte_ids.numpoliza,
                                      'AseguraCarga': invoice.nombreaseg_merc,
                                      'PolizaCarga': invoice.numpoliza_merc,
                                      'PrimaSeguro': invoice.primaseguro_merc,
                                      'AseguraMedAmbiente': invoice.seguro_ambiente,
                                      'PolizaMedAmbiente': invoice.poliza_ambiente,
                                 },
                   }
                   remolques = []
                   if invoice.remolque_line_ids:
                      for remolque in invoice.remolque_line_ids:
                          remolques.append({
                                 'SubTipoRem': remolque.subtipo_id.clave,
                                 'Placa': remolque.placa,
                          })
                      transpote_detalle.update({'Remolques': remolques})

                   mercancias.update({'Autotransporte': transpote_detalle})
             elif invoice.tipo_transporte == '02': # maritimo
                   maritimo = []
             elif invoice.tipo_transporte == '03': #aereo
                   transpote_detalle = {
                                 'PermSCT': invoice.permisosct.clave,
                                 'NumPermisoSCT': invoice.numpermisosct,
                                 'MatriculaAeronave': invoice.matriculaaeronave,
                              #   'NombreAseg': invoice.nombreaseg,  ******
                              #   'NumPolizaSeguro': invoice.numpoliza, *****
                                 'NumeroGuia': invoice.numeroguia,
                                 'LugarContrato': invoice.lugarcontrato,
                                 'CodigoTransportista': invoice.transportista_id.codigotransportista.clave,
                                 'RFCEmbarcador': invoice.embarcador_id.vat if invoice.embarcador_id.country_id.l10n_mx_edi_code == 'MEX' else '',
                                 'NumRegIdTribEmbarc': invoice.embarcador_id.vat if invoice.embarcador_id.country_id.l10n_mx_edi_code != 'MEX' else '',
                                 'ResidenciaFiscalEmbarc': invoice.embarcador_id.country_id.l10n_mx_edi_code if invoice.embarcador_id.country_id.l10n_mx_edi_code != 'MEX' else '',
                                 'NombreEmbarcador': invoice.embarcador_id.name,
                   }
                   mercancias.update({'TransporteAereo': transpote_detalle})
             elif invoice.tipo_transporte == '04': #ferroviario
                   ferroviario = []

             cartaporte31.update({'Mercancias': mercancias})

             #################  Figura transporte ############################
             figuratransporte = []
             tipos_figura = []
             for figura in invoice.figuratransporte_ids:
                 tipos_figura = {
                            'TipoFigura': figura.tipofigura.clave,
                            'RFCFigura': figura.figura_id.vat if figura.figura_id.country_id.l10n_mx_edi_code == 'MEX' else '',
                            'NumLicencia': figura.figura_id.cce_licencia,
                            'NombreFigura': figura.figura_id.name,
                            'NumRegIdTribFigura': figura.figura_id.vat if figura.figura_id.country_id.l10n_mx_edi_code != 'MEX' else '',
                            'ResidenciaFiscalFigura': figura.figura_id.country_id.l10n_mx_edi_code if figura.figura_id.country_id.l10n_mx_edi_code != 'MEX' else '',
                            'Domicilio': {
                                     'Calle': figura.figura_id.street_name,
                                     'NumeroExterior': figura.figura_id.street_number,
                                     'NumeroInterior': figura.figura_id.street_number2,
                                     'Colonia': figura.figura_id.l10n_mx_edi_colony_code if ubicacion.contacto.country_id.l10n_mx_edi_code == 'MEX' else ubicacion.contacto.l10n_mx_edi_colony or '',
                                     'Localidad': figura.figura_id.l10n_mx_edi_locality_id.code if ubicacion.contacto.country_id.l10n_mx_edi_code == 'MEX' else ubicacion.contacto.l10n_mx_edi_locality,
                               #      'Referencia': operador.company_id.cce_clave_estado.c_estado,
                                     'Municipio': figura.figura_id.city_id.l10n_mx_edi_code if figura.figura_id.country_id.l10n_mx_edi_code == 'MEX' else figura.figura_id.city,
                                     'Estado': figura.figura_id.state_id.code if figura.figura_id.country_id.l10n_mx_edi_code in ('MEX', 'USA', 'CAN') or figura.figura_id.state_id.code else 'NA',
                                     'Pais': figura.figura_id.country_id.l10n_mx_edi_code,
                                     'CodigoPostal': figura.figura_id.zip,
                            },
                 }

                 partes = []
                 for parte in figura.partetransporte:
                    partes.append({
                         'ParteTransporte': parte.clave,
                    })
                 figuratransporte.append({'TiposFigura': tipos_figura, 'PartesTransporte': partes})

             cartaporte31.update({'FiguraTransporte': figuratransporte})
             comp_construccion.update({'cartaporte31': cartaporte31})

             options = {'width': 275 * mm, 'height': 275 * mm}
             ubicacion = invoice.ubicaciones_line_ids[0]
             #corregir hora
             timezone = invoice._context.get('tz')
             if not timezone:
                timezone = invoice.env.user.partner_id.tz or 'America/Mexico_City'
             local = pytz.timezone(timezone)
             local_dt_from = ubicacion.fecha.replace(tzinfo=pytz.UTC).astimezone(local)
             fechaorig = local_dt_from.strftime ("%Y-%m-%dT%H:%M:%S")
#             edi_result = invoice.env['l10n_mx_edi.document']._decode_cfdi_attachment(invoice.l10n_mx_edi_cfdi_attachment_id.raw)
             qr_ccp_value = 'https://verificacfdi.facturaelectronica.sat.gob.mx/verificaccp/default.aspx?IdCCP=%s&FechaOrig=%s&FechaTimb=%s' % (
                 invoice.IdCCP,
                 fechaorig,
#                 edi_result.get('emission_date_str'),
                 cfdi_values['fecha'],
             )
             invoice.qr_ccp_value = qr_ccp_value
             ret_val = createBarcodeDrawing('QR', value=qr_ccp_value, **options)
             invoice.qrcode_ccp_image = base64.encodebytes(ret_val.asString('jpg'))
#      return vals

    def clean_text(self, text):
        clean_text = text.replace('\n', ' ').replace('\\', ' ').replace('-', ' ').replace('/', ' ').replace('|', ' ')
        clean_text = clean_text.replace(',', ' ').replace(';', ' ').replace('>', ' ').replace('<', ' ')
        return clean_text[:1000]

    def llenar_id_ubicacion(self):
        for traslado in self:
            orig = 1
            dest = 1
            for line in traslado.ubicaciones_line_ids:
                if line.tipoubicacion == 'Origen':
                    line.idubicacion = 'OR' + str(orig).rjust(6, '0')
                    orig += 1
                else:
                    line.idubicacion = 'DE' + str(dest).rjust(6, '0')
                    dest += 1

# opcional odoo sh
#class L10nMxEdiDocument(models.Model):
#    _inherit = 'l10n_mx_edi.document'

#    @api.model
#    def _get_cadena_xslts(self):
#        return 'l10n_mx_edi/data/4.0/xslt/cadenaoriginal_TFD.xslt', 'l10n_mx_edi_carta_porte/data/4.0/cadenaoriginal_4_0.xslt'
