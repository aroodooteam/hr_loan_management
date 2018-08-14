# -*- coding: utf-8 -*-

from openerp import api, exceptions, fields, models, _
from openerp.exceptions import Warning, ValidationError
import datetime
import logging

_logger = logging.getLogger(__name__)


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    _description = 'Rajouter le code rubrique'


    @api.multi
    def name_get(self):
        result = super(HrSalaryRule,self).name_get()
        res = []
        print("result = %s" % result)
        for rec in result:
            el_obj = self.browse(rec[0])
            #r_name = rec[1] + ' '+ '[' + el_obj.code + ']'
            r_name = '[' + el_obj.code + ']'+' '+ rec[1]
            res.append((el_obj.id,  r_name))
        return res


class HrLoanRequestType(models.Model):
    _name = 'hr.loan.request.type'
    _description = 'Type de prets existants'

    code = fields.Char(string='Code',size=64)
    name = fields.Char(string=u"Type de prêts",size=64)
    amount_max = fields.Integer(string='Montant maximum')
    cession_max = fields.Integer(string='Cession Maximum (%)')
    age_max = fields.Integer(string='Age Maximum')
    duree_max = fields.Integer(string=u'Durée Maximum (Mois)')
    rate = fields.Float(string='Taux',default=0.0,digits=(6, 2))
    rubrique_id = fields.Many2one('hr.salary.rule', string='Rubrique')
    limited_on_current_year = fields.Boolean(string=u'Limite sur l\'année en cours')
    formule = fields.Char(string='Formule', size=128, help='''
        Pour les calcule de quotite cessible,Capital et/ou Plafond on utilise les variables suivantes :
            salaire_base : Salaire de base
            Transport : Indemnite de Transport
            Logement : Indemnite de Logement
            Anciennete : Prime d anciennete
            constante : Constant (pour ppe en generale)
        ''')
    formule_plafond = fields.Char(string='Formule plafond', size=128,help='''
            Pour les calcule de quotite cessible,Capital et/ou Plafond on utilise les variables suivantes :
                salaire_base : Salaire de base
                Transport : Indemnite de Transport
                Logement : Indemnite de Logement
                Anciennete : Prime d anciennete
                constante : Constant (pour ppe en generale)
        ''')
    rub_code = fields.Char(string='Code de la ligne de rubrique', size=64)
    constante = fields.Float(string='Constante')

class HrBacklogType(models.Model):
    _name = 'hr.backlog.type'
    _description = u'Type d arriérés existant'

    code = fields.Char(string='Code',size=64)
    name = fields.Char(string=u"Type de prêts",size=64)
    rubrique_id = fields.Many2one('hr.salary.rule', string='Rubrique')


class HrLoanRequest(models.Model):
    _name = 'hr.loan.request'
    _description = 'Gestion de demande de prets'

    employee_id = fields.Many2one(string=u'Employé',related="contract_id.employee_id",store=True,readonly=True)
    contract_id = fields.Many2one('hr.contract',string=u'Demandeur')
    #loan_contract_id = fields.Many2one('hr.contract',string='Contrat')
    request_amount = fields.Float(string=u'Montant demandé',required=True)
    approved_amount = fields.Float(string=u'Montant accordé',required=True)
    somme_retenue = fields.Float(string=u'Amortissement',required=True)
    date_request = fields.Datetime(string=u'Envoyé le',required=True)
    request_id = fields.Many2one('hr.loan.request.type',string=u'Type de prêt',required=True)
    #quotite_cessible = fields.Float(string=u'Quotité cessible',digits=(16, 2))
    quotite_saisissable = fields.Float(string=u'Quotité cessible',digits=(16, 2))
    quotite_saisissable_restante = fields.Float(string=u'Quotité cessible restante',digits=(16, 2))
    quotite_ph_saisissable_restante = fields.Float(string=u'Quotité cessible restante',digits=(16, 2))
    quotite_conjoint = fields.Float(string=u'Quotité conjoint',digits=(16, 2))
    quotite_engage = fields.Float(string=u'Quotité engagée',digits=(16, 2))
    capital_forme = fields.Float(string=u'Capital formé',digits=(16, 2))
    capital_ph_dispo = fields.Float(string=u'Capital disponible',digits=(16, 2))
    duree_ph = fields.Integer(string=u'Durée')
    duree_grande_avance = fields.Integer(string=u'Mensualité',required=True)
    loan_interest = fields.Float(string=u'Intérêt',digits=(16, 2))
    total_deduction = fields.Float(string=u'Retenue sur salaire',digits=(16, 2))
    total_ppe = fields.Float(string=u'PPE en Cours',digits=(16, 2))
    total_ph = fields.Float(string=u'PH en Cours',digits=(16, 2))
    total_avex = fields.Float(string=u'Avance en Cours',digits=(16, 2))
    pret_initial = fields.Float(string=u'Prêt initial',digits=(16, 2))
    type_credit= fields.Text(string='Type de crédit')
    observation = fields.Text(string='Motif')
    drh_notification = fields.Text(string='Observations')
    date_start = fields.Date(string=u'Date début')
    date_end = fields.Date(string=u'Date fin')
    active = fields.Boolean(string='Actif')

    
    

    @api.multi
    def get_quotite_cessible(self):
        current_date=datetime.datetime.now()
        #_logger.info("\n === DATE DU JOUR = %s" % current_date)
        current_month=current_date.month
        #_logger.info("\n === MOIS EN COURS = %s" % current_month)
        month_remaining=13-current_month
        #_logger.info("\n === MOIS RESTANT = %s" % month_remaining)
        current_year=current_date.year
        #_logger.info("\n === ANNEE EN COURS = %s" % current_year)
        loan_type_obj=self.env['hr.loan.request.type']
        avance_quinze_id=loan_type_obj.search([('code','=','AV15')])
        avex_id=loan_type_obj.search([('code','=','AVEX')])
        ppe_id=loan_type_obj.search([('code','=','PPE')])
        ph_id=loan_type_obj.search([('code','=','PH')])
        res_avex_remaining=[]
        res_avex_amount=[]
        res_total_current_avex=[]
        res_ph_remaining=[]
        res_ph_amount=[]
        res_total_current_ph=[]

        emp_loan_request=self.env['hr.loan.request']
        avex_request_active=emp_loan_request.search([('active','=',True),('contract_id','=',self.contract_id.id),('request_id','=', avex_id.id)])
        loan_active_avex=avex_request_active.mapped('date_end')
        #_logger.info("\n === AVEX EN COURS = %s" % loan_active_avex)
        active_avex_amount=avex_request_active.mapped('somme_retenue')
        #_logger.info("\n === SOMME RETENUE AVEX EN COURS = %s" % active_avex_amount)
        ppe_request_active=emp_loan_request.search([('active','=',True),('contract_id','=',self.contract_id.id),('request_id','=', ppe_id.id)])
        ph_request_active=emp_loan_request.search([('active','=',True),('contract_id','=',self.contract_id.id),('request_id','=', ph_id.id)])
        loan_active_ph=ph_request_active.mapped('date_end')
        active_ph_amount=ph_request_active.mapped('somme_retenue')


        #AVEX en cours
        if loan_active_avex:
            for avex_loan in loan_active_avex:
                day_end=datetime.datetime.strptime(avex_loan,'%Y-%m-%d')
                month_end=day_end.month
                _logger.info("\n === ECHEANCE AVEX = %s" % month_end)
                avex_remaining=(month_end-current_month)+1
                res_avex_remaining.append(avex_remaining)
                #return res_avex_remaining
            _logger.info("\n === LISTE ECHEANCE AVEX = %s" % res_avex_remaining)
            for rec_avex_amount in active_avex_amount:
                avex_amount=rec_avex_amount
                res_avex_amount.append(avex_amount)
                #return res_avex_remaining
            _logger.info("\n === LISTE MONTANT AVEX = %s" % res_avex_amount)
            res_total_current_avex=[avex_restant*avex_retenue for  avex_restant,avex_retenue in zip(res_avex_remaining,res_avex_amount)]
            _logger.info("\n === TOTAL AVEX EN COURS = %s" % res_total_current_avex)

        #PPE en cours
        if ppe_request_active.id:
            for ppe_loan in ppe_request_active:
                day_end=datetime.datetime.strptime(ppe_loan.date_end,'%Y-%m-%d')
                month_end=day_end.month
                #_logger.info("\n === MOIS FIN = %s" % month_end)
                year_end=day_end.year
                #_logger.info("\n === ANNEE FIN = %s" % year_end)
        else:
            month_end=0
            year_end=0
            #_logger.info("\n === ANNEE FIN = %s" % year_end)

        if year_end > current_year:
            ppe_remaining=month_remaining
            #_logger.info("\n === MENSUALITES PPE RESTANT = %s" % ppe_remaining)
        elif year_end <= current_year and year_end != 0:
            ppe_remaining=(month_end-current_month)+1
            #_logger.info("\n === MENSUALITES PPE RESTANT = %s" % ppe_remaining)
        elif year_end == 0:
            ppe_remaining=0
            #_logger.info("\n === MENSUALITES PPE RESTANT = %s" % ppe_remaining)

        # PH en cours
        # if ph_request_active.id:
        #     for ph_loan in ppe_request_active:
        #         ph_day_end=datetime.datetime.strptime(ph_loan.date_end,'%Y-%m-%d')
        #         ph_month_end=day_end.month
        #         _logger.info("\n === MOIS FIN = %s" % ph_month_end)
        #         ph_year_end=day_end.year
        #         _logger.info("\n === ANNEE FIN = %s" % ph_year_end)
        # else:
        #     ph_month_end=0
        #     ph_year_end=0
        #     _logger.info("\n === ANNEE FIN = %s" % ph_year_end)

        #PH en cours
        if loan_active_ph:
            for ph_loan in loan_active_ph:
                ph_day_end=datetime.datetime.strptime(ph_loan,'%Y-%m-%d')
                ph_month_end=ph_day_end.month
                ph_year_end=ph_day_end.year
                if ph_year_end > current_year:
                    ph_remaining=month_remaining
                    res_ph_remaining.append(ph_remaining)
                elif ph_year_end <= current_year:
                    ph_remaining=(ph_month_end-current_month)+1
                    res_ph_remaining.append(ph_remaining)
                _logger.info("\n === MENSUALITES PH RESTANT = %s" % res_ph_remaining)
            for rec_ph_amount in active_ph_amount:
                ph_amount=rec_ph_amount
                res_ph_amount.append(ph_amount)
            _logger.info("\n === LISTE MONTANT PH = %s" % res_ph_amount)
            res_total_current_ph=[ph_restant*ph_retenue for  ph_restant,ph_retenue in zip(res_ph_remaining,res_ph_amount)]
            _logger.info("\n === TOTAL PH EN COURS = %s" % res_total_current_ph)

        # if ph_year_end > current_year:
        #     ph_remaining=month_remaining
        #     _logger.info("\n === MENSUALITES PH RESTANT = %s" % ph_remaining)
        # elif ph_year_end <= current_year and year_end != 0:
        #     ph_remaining=(month_end-current_month)+1
        #     _logger.info("\n === MENSUALITES PH RESTANT = %s" % ph_remaining)
        # elif ph_year_end == 0:
        #     ph_remaining=0
        #     _logger.info("\n === MENSUALITES PH RESTANT = %s" % ppe_remaining)


        for employee_request in self:
            emp_wage=employee_request.contract_id.wage
            emp_seniority=employee_request.contract_id.prime_anciennete
            emp_logement=employee_request.contract_id.indemnite_logement
            emp_transport=employee_request.contract_id.indemnite_transport
            emp_ressources=emp_wage+emp_seniority+emp_logement+emp_transport
            emp_avex=employee_request.contract_id.retenue_avex
            emp_ppe=employee_request.contract_id.retenue_ppe
            emp_ph=employee_request.contract_id.retenue_ph
            emp_ksa=employee_request.contract_id.retenue_ksa
            if employee_request.request_id.id == avance_quinze_id.id:
                retenue_max=emp_ressources*0.5
                remboursement_en_cours=emp_avex+emp_ppe+emp_ph+emp_ksa
                employee_request.quotite_saisissable=retenue_max-remboursement_en_cours
            elif employee_request.request_id.id == avex_id.id:
                #_logger.info('\n=== ACTIVE PPE = %s ===\n' % ppe_request_active.id)
                nb_mois=employee_request.duree_grande_avance
                plafond_avance=(emp_ressources*0.3)*nb_mois
                employee_request.total_avex=sum(res_total_current_avex)
                employee_request.total_ppe=emp_ppe*ppe_remaining
                employee_request.total_ph=sum(res_total_current_ph)
                emp_current_loan=employee_request.total_ppe+employee_request.total_avex+employee_request.total_ph
                employee_request.quotite_saisissable=plafond_avance-emp_current_loan
            elif employee_request.request_id.id == ppe_id.id:
                qcm=emp_ressources*0.3
                qc_restant=qcm-emp_ph
                capital=(qc_restant/3.042)*100
                employee_request.quotite_saisissable=qcm
                employee_request.quotite_saisissable_restante=qc_restant
                employee_request.capital_forme=capital
            elif employee_request.request_id.id == ph_id.id:
                qci=(emp_wage+emp_seniority+emp_transport)*0.3+emp_logement
                employee_request.quotite_saisissable=qci
                qce=employee_request.quotite_engage
                employee_request.quotite_ph_saisissable_restante=qci-qce

    @api.multi
    def get_loan_deduction(self):
        res_capital=[]
        res_interest=[]

        code_av15=self.request_id.search([('code','=','AV15')]).id
        code_avex=self.request_id.search([('code','=','AVEX')]).id
        code_ppe=self.request_id.search([('code','=','PPE')]).id
        code_ph=self.request_id.search([('code','=','PH')]).id

        if self.date_start and self.date_end:
            if self.date_start < self.date_end:
                day_start=datetime.datetime.strptime(self.date_start,'%Y-%m-%d')
                day_end=datetime.datetime.strptime(self.date_end,'%Y-%m-%d')
                month_end=day_end.month
                month_start=day_start.month
                avex_period=(month_end-month_start)+1
            else:
                raise Warning('Vérifiez vos dates, la date de début doit être inférieure à la date de fin')
        else:
            raise Warning('Veuillez remplir les champs dates')
            # raise ValidationError("Incorrect date value")
            
        i=0
        for  employee_request in self:
            if employee_request.approved_amount:
                imputed_amount=employee_request.approved_amount
                if employee_request.request_id.id == code_av15:
                    avex_amort=employee_request.approved_amount
                    loan_deduction=0
                elif employee_request.request_id.id == code_avex:
                    avex_amort=employee_request.approved_amount / avex_period
                    res_capital.append(imputed_amount)
                    avex_cap=imputed_amount
                    while i < avex_period -1:
                        avex_temp= avex_cap-avex_amort
                        avex_int=avex_temp / 200
                        res_capital.append(avex_temp)
                        res_interest.append(avex_int)
                        avex_cap=avex_temp
                        i+=1
                    loan_deduction= sum(res_interest) /  avex_period
            else:
                raise Warning('Veuillez renseigner le champ Retenue Principale')
            employee_request.somme_retenue=avex_amort
            employee_request.loan_interest=loan_deduction
            employee_request.total_deduction=avex_amort+loan_deduction
            _logger.info("\n === AMORTISSEMENT PRINCIPAL = %s" % avex_amort)
            _logger.info("\n === CAPITAL = %s" % res_capital)
            _logger.info("\n === INTERET = %s" % res_interest)
            _logger.info("\n === INTERET LISSE = %s" % loan_deduction)
        
        # i=0
        # res_capital.append(imputed_amount)
        # avex_cap=imputed_amount
        # while i < avex_period -1:
        #     avex_temp= avex_cap-avex_amort
        #     avex_int=avex_temp / 200
        #     res_capital.append(avex_temp)
        #     res_interest.append(avex_int)
        #     avex_cap=avex_temp
        #     i+=1

        # loan_deduction= sum(res_interest) /  avex_period

        # _logger.info("\n === CAPITAL = %s" % res_capital)
        # _logger.info("\n === INTERET = %s" % res_interest)
        # _logger.info("\n === INTERET LISSE = %s" % loan_deduction)

    @api.onchange('request_id')
    def _onchange_request_id(self):
        for employee_request in self:
            code_av15=employee_request.request_id.search([('code','=','AV15')]).id
            _logger.info("\n === CODE_AV15 = %s" % code_av15)
            code_avex=employee_request.request_id.search([('code','=','AVEX')]).id
            _logger.info("\n === CODE_AVEX = %s" % code_avex)
            code_ppe=employee_request.request_id.search([('code','=','PPE')]).id
            _logger.info("\n === CODE_PPE = %s" % code_ppe)
            code_ph=employee_request.request_id.search([('code','=','PH')]).id
            _logger.info("\n === CODE_PH = %s" % code_ph)
    #         #if employee_request.request_id.id == 1:
    #         if employee_request.request_id.id == code_av15:
    #             #request=employee_request.request_id.id
    #             #_logger.info("\n === request_id = %s" % request)
    #             quotite =employee_request.contract_id.avance_quinze
    #         #_logger.info("\n === quotite cessible = %s" % quotite)
    #             employee_request.quotite_saisissable=quotite
    #         elif employee_request.request_id.id == code_avex:
    #              quotite = employee_request.contract_id.avex
    #             #_logger.info("\n === quotite cessible = %s" % quotite)
    #              employee_request.quotite_saisissable=quotite
    #         elif employee_request.request_id.id == code_ppe:
    #              quotite = employee_request.contract_id.ppe
    #              #_logger.info("\n === quotite cessible = %s" % quotite)
    #              employee_request.quotite_saisissable=quotite
    #         elif employee_request.request_id.id == code_ph:
    #              quotite = employee_request.contract_id.ph
    #              #_logger.info("\n === quotite cessible = %s" % quotite)
    #              employee_request.quotite_saisissable=quotite

    @api.onchange('date_end')
    def update_employee_loan_request(self):
        if self.date_end:
            days = datetime.datetime.now() - datetime.datetime.strptime(self['date_end'], '%Y-%m-%d')
            _logger.info("\n === DAYS = %s" % days)
            day=days.days
            _logger.info("\n === JOUR = %s" % day)
            if day >= 0:
                _logger.info("\n === ECHU = ")
                self.active=False
            else:
                _logger.info("\n === EN COURS = ")
                self.active =True
        
    @api.model
    def create(self,vals):
        res = super(HrLoanRequest, self).create(vals)
        loan_type_obj = self.env['hr.loan.request.type']

        avance_quinze_id = loan_type_obj.search([('code', '=', 'AV15')])
        avex_id = loan_type_obj.search([('code', '=', 'AVEX')])
        ppe_id = loan_type_obj.search([('code', '=', 'PPE')])
        ph_id = loan_type_obj.search([('code', '=', 'PH')])

        values = {}
        # loan_amt = res.somme_retenue
        
        if res.request_id.id == avance_quinze_id.id:
            loan_ids = self.search(
                [
                    ('request_id', '=', avance_quinze_id.id),
                    ('active', '=', True),
                    ('contract_id', '=', res.contract_id.id)
                ])
            loan_avance_quinze = loan_ids.mapped('somme_retenue')
            loan_amt = sum(loan_avance_quinze)
            _logger.info("\n ===SOMME AVANCE 15 = %s" % loan_amt)
            values = {'retenue_avance_quinze': loan_amt}
        elif res.request_id.id == avex_id.id:
            loan_ids = self.search(
                [
                    ('request_id', '=', avex_id.id),
                    ('active', '=', True),
                    ('contract_id', '=', res.contract_id.id)
                ])
            loan_avex = loan_ids.mapped('somme_retenue')
            loan_amt = sum(loan_avex)
            values = {'retenue_avex': loan_amt}
        elif res.request_id.id == ppe_id.id:
            loan_ids = self.search(
                [
                    ('request_id', '=', ppe_id.id),
                    ('active', '=', True),
                    ('contract_id', '=', res.contract_id.id)
                ])
            loan_ppe = loan_ids.mapped('somme_retenue')
            loan_amt = sum(loan_ppe)
            values = {'retenue_ppe': loan_amt}
        elif res.request_id.id == ph_id.id:
            loan_ids = self.search(
                [
                    ('request_id', '=', ph_id.id),
                    ('active', '=', True),
                    ('contract_id', '=', res.contract_id.id)
                ])
            loan_ph = loan_ids.mapped('somme_retenue')
            loan_amt = sum(loan_ph)
            values = {'retenue_ph': loan_amt}

        res.contract_id.write(values)
        return res

    @api.multi
    def write(self,vals):
        #traitement
        res = super(HrLoanRequest, self).write(vals)
        #arr_amt = res.backlog_amount
        loan_type_obj = self.env['hr.loan.request.type']
        avance_quinze_id = loan_type_obj.search([('code', '=', 'AV15')])
        avex_id = loan_type_obj.search([('code', '=', 'AVEX')])
        ppe_id = loan_type_obj.search([('code', '=', 'PPE')])
        ph_id = loan_type_obj.search([('code', '=', 'PH')])
        values={}

        for rec in self:
            if rec.request_id.id == avance_quinze_id.id:
                _logger.info("\n === REACTIVATION AV15 = ")
                #loan_amt=rec.somme_retenue
                bl_ids = self.search(
                    [
                        ('request_id', '=', avance_quinze_id.id),
                        ('active', '=', True),
                        ('contract_id', '=', rec.contract_id.id)
                    ])
                bl_arr = bl_ids.mapped('somme_retenue')
                loan_amt = sum(bl_arr)
                values = {'retenue_avance_quinze': loan_amt}
                _logger.info('\n=== SOMME QUINZE= %s ===\n' % values)
                rec.contract_id.write(values)
            elif rec.request_id.id == avex_id.id:
                _logger.info("\n === REACTIVATION AVEX = ")
                #loan_amt=rec.somme_retenue
                bl_ids = self.search(
                    [
                        ('request_id', '=', avex_id.id),
                        ('active', '=', True),
                        ('contract_id', '=', rec.contract_id.id)
                    ])
                bl_arr = bl_ids.mapped('somme_retenue')
                loan_amt = sum(bl_arr)
                values = {'retenue_avex': loan_amt}
                _logger.info('\n=== SOMME AVEX= %s ===\n' % values)
                rec.contract_id.write(values)
            elif rec.request_id.id == ppe_id.id:
                _logger.info("\n === REACTIVATION PPE = ")
                #loan_amt=rec.somme_retenue
                bl_ids = self.search(
                    [
                        ('request_id', '=', ppe_id.id),
                        ('active', '=', True),
                        ('contract_id', '=', rec.contract_id.id)
                    ])
                bl_arr = bl_ids.mapped('somme_retenue')
                loan_amt = sum(bl_arr)
                values = {'retenue_ppe': loan_amt}
                _logger.info('\n=== SOMME PPE= %s ===\n' % values)
                rec.contract_id.write(values)
            elif rec.request_id.id == ph_id.id:
                _logger.info("\n === REACTIVATION PH = ")
                #loan_amt=rec.somme_retenue
                bl_ids = self.search(
                    [
                        ('request_id', '=', ph_id.id),
                        ('active', '=', True),
                        ('contract_id', '=', rec.contract_id.id)
                    ])
                bl_arr = bl_ids.mapped('somme_retenue')
                loan_amt = sum(bl_arr)
                values = {'retenue_ph': loan_amt}
                _logger.info('\n=== SOMME PH= %s ===\n' % values)
                rec.contract_id.write(values)
        return res

    @api.multi
    def unlink(self):
        #traitement
        loan_type_obj = self.env['hr.loan.request.type']
        avance_quinze_id = loan_type_obj.search([('code', '=', 'AV15')])
        avex_id = loan_type_obj.search([('code', '=', 'AVEX')])
        ppe_id = loan_type_obj.search([('code', '=', 'PPE')])
        ph_id = loan_type_obj.search([('code', '=', 'PH')])

        for rec in self:
            if rec.request_id.id == avance_quinze_id.id:
                rec.contract_id.retenue_avance_quinze = rec.contract_id.retenue_avance_quinze - rec.somme_retenue
            elif rec.request_id.id == avex_id.id:
                rec.contract_id.retenue_avex = rec.contract_id.retenue_avex - rec.somme_retenue
            elif rec.request_id.id == ppe_id.id:
                rec.contract_id.retenue_ppe = rec.contract_id.retenue_ppe - rec.somme_retenue
            elif rec.request_id.id == ph_id.id:
                rec.contract_id.retenue_ph = rec.contract_id.retenue_ph - rec.somme_retenue

        res = super(HrLoanRequest, self).unlink()
        return res
    
class HrBacklog(models.Model):
    _name = 'hr.backlog'
    _description = u'Arriérés'

    employee_id = fields.Many2one(string=u'Employé',related="contract_id.employee_id",store=True,readonly=True)
    contract_id = fields.Many2one('hr.contract',string=u'Demandeur')
    request_id = fields.Many2one('hr.backlog.type',string=u'Type de prêt')
    backlog_amount = fields.Float(string=u'Montant arriéré',required=True)
    date_start = fields.Date(string=u'Date début')
    date_end = fields.Date(string=u'Date fin')
    observation = fields.Text(string='Observations')
    backlog_status = fields.Char(string='Statut')
    active = fields.Boolean(string='Actif')

    @api.onchange('date_end')
    def update_employee_backlog(self):
        if self.date_end:
            days = datetime.datetime.now() - datetime.datetime.strptime(self['date_end'], '%Y-%m-%d')
            _logger.info("\n === DAYS = %s" % days)
            day=days.days
            _logger.info("\n === JOUR = %s" % day)
            if day >= 0:
                _logger.info("\n === ECHU = ")
                self.active=False
            else:
                _logger.info("\n === EN COURS = ")
                self.active =True


    @api.multi
    def unlink(self):
        #traitement
        blog_type_obj = self.env['hr.backlog.type']
        arr_id = blog_type_obj.search([('code', '=', 'ARR')])
        as_aro_id = blog_type_obj.search([('code', '=','OP AS ARO')])
        ins_id = blog_type_obj.search([('code', '=', 'ASS')])
        div_id = blog_type_obj.search([('code', '=', 'DIV')])
        ksa_id = blog_type_obj.search([('code', '=', 'KSA')])
        mal_id = blog_type_obj.search([('code', '=', 'MAL')])
        vam_id = blog_type_obj.search([('code', '=', 'VAM')])

        for rec in self:
            if rec.request_id.id == arr_id.id:
                rec.contract_id.retenue_arr = rec.contract_id.retenue_arr - rec.backlog_amount
            elif rec.request_id.id == as_aro_id.id:
                rec.contract_id.retenue_as_aro = rec.contract_id.retenue_as_aro - rec.backlog_amount
            elif rec.request_id.id == ins_id.id:
                rec.contract_id.retenue_assurance = rec.contract_id.retenue_assurance - rec.backlog_amount
            elif rec.request_id.id == div_id.id:
                rec.contract_id.retenue_divers = rec.contract_id.retenue_divers - rec.backlog_amount
            elif rec.request_id.id == ksa_id.id:
                rec.contract_id.retenue_ksa = rec.contract_id.retenue_ksa - rec.backlog_amount
            elif rec.request_id.id == mal_id.id:
                rec.contract_id.retenue_maladie = rec.contract_id.retenue_maladie - rec.backlog_amount
            elif rec.request_id.id == vam_id.id:
                rec.contract_id.retenue_vam = rec.contract_id.retenue_vam - rec.backlog_amount

        res = super(HrBacklog, self).unlink()
        return res
    
    @api.multi
    def write(self,vals):
        #traitement
        res = super(HrBacklog, self).write(vals)
        #arr_amt = res.backlog_amount
        blog_type_obj = self.env['hr.backlog.type']
        arr_id = blog_type_obj.search([('code', '=', 'ARR')])
        as_aro_id = blog_type_obj.search([('code', '=','OP AS ARO')])
        ins_id = blog_type_obj.search([('code', '=', 'ASS')])
        div_id = blog_type_obj.search([('code', '=', 'DIV')])
        ksa_id = blog_type_obj.search([('code', '=', 'KSA')])
        mal_id = blog_type_obj.search([('code', '=', 'MAL')])
        vam_id = blog_type_obj.search([('code', '=', 'VAM')])
        values={}

        for rec in self:
            if rec.request_id.id == arr_id.id:
                _logger.info("\n === REACTIVATION ARRIERES = ")
                arr_amt=rec.backlog_amount
                bl_ids = self.search(
                    [
                        ('request_id', '=', arr_id.id),
                        ('active', '=', True),
                        ('contract_id', '=', rec.contract_id.id)
                    ])
                bl_arr = bl_ids.mapped('backlog_amount')
                arr_amt = sum(bl_arr)
                values = {'retenue_arr': arr_amt}
                _logger.info('\n=== SOMME ARRIERES = %s ===\n' % values)
                rec.contract_id.write(values)
            elif rec.request_id.id == as_aro_id.id:
                _logger.info("\n === REACTIVATION AS ARO = ")
                arr_amt=rec.backlog_amount
                bl_ids = self.search(
                    [
                        ('request_id', '=', as_aro_id.id),
                        ('active', '=', True),
                        ('contract_id', '=', rec.contract_id.id)
                    ])
                bl_arr = bl_ids.mapped('backlog_amount')
                arr_amt = sum(bl_arr)
                values = {'retenue_as_aro': arr_amt}
                _logger.info('\n=== SOMME AS ARO = %s ===\n' % values)
                rec.contract_id.write(values)
            elif rec.request_id.id == ins_id.id:
                _logger.info("\n === REACTIVATION ASSURANCES = ")
                arr_amt=rec.backlog_amount
                bl_ids = self.search(
                    [
                        ('request_id', '=', ins_id.id),
                        ('active', '=', True),
                        ('contract_id', '=', rec.contract_id.id)
                    ])
                bl_arr = bl_ids.mapped('backlog_amount')
                arr_amt = sum(bl_arr)
                values = {'retenue_assurance': arr_amt}
                _logger.info('\n=== SOMME ASSURANCE = %s ===\n' % values)
                rec.contract_id.write(values)
            elif rec.request_id.id == div_id.id:
                _logger.info("\n === REACTIVATION DIVERS = ")
                arr_amt=rec.backlog_amount
                bl_ids = self.search(
                    [
                        ('request_id', '=', div_id.id),
                        ('active', '=', True),
                        ('contract_id', '=', rec.contract_id.id)
                    ])
                bl_arr = bl_ids.mapped('backlog_amount')
                arr_amt = sum(bl_arr)
                values = {'retenue_divers': arr_amt}
                _logger.info('\n=== SOMME DIVERS = %s ===\n' % values)
                rec.contract_id.write(values)
            elif rec.request_id.id == ksa_id.id:
                _logger.info("\n === REACTIVATION DIVERS = ")
                arr_amt=rec.backlog_amount
                bl_ids = self.search(
                    [
                        ('request_id', '=', ksa_id.id),
                        ('active', '=', True),
                        ('contract_id', '=', rec.contract_id.id)
                    ])
                bl_arr = bl_ids.mapped('backlog_amount')
                arr_amt = sum(bl_arr)
                values = {'retenue_ksa': arr_amt}
                _logger.info('\n=== SOMME KSA = %s ===\n' % values)
                rec.contract_id.write(values)
            elif rec.request_id.id == mal_id.id:
                _logger.info("\n === REACTIVATION MALADIE = ")
                arr_amt=rec.backlog_amount
                bl_ids = self.search(
                    [
                        ('request_id', '=', mal_id.id),
                        ('active', '=', True),
                        ('contract_id', '=', rec.contract_id.id)
                    ])
                bl_arr = bl_ids.mapped('backlog_amount')
                arr_amt = sum(bl_arr)
                values = {'retenue_maladie': arr_amt}
                _logger.info('\n=== SOMME MALADIE = %s ===\n' % values)
                rec.contract_id.write(values)
            elif rec.request_id.id == vam_id.id:
                _logger.info("\n === REACTIVATION VAM = ")
                arr_amt=rec.backlog_amount
                bl_ids = self.search(
                    [
                        ('request_id', '=', vam_id.id),
                        ('active', '=', True),
                        ('contract_id', '=', rec.contract_id.id)
                    ])
                bl_arr = bl_ids.mapped('backlog_amount')
                arr_amt = sum(bl_arr)
                values = {'retenue_vam': arr_amt}
                _logger.info('\n=== SOMME VAM = %s ===\n' % values)
                rec.contract_id.write(values)
        return res




        
        # for rec in self:
        #     if rec.request_id.id == arr_id.id:
        #         if rec.contract_id.retenue_arr == 0.00:
        #             rec.contract_id.write({'retenue_arr': vals.get('backlog_amount')})
        #         else:
        #             _logger.info("\n === REACTIVATION ARRIERES = ")
        #             arr_amt=rec.backlog_amount
        #             bl_ids = self.search(
        #                 [
        #                    ('request_id', '=', arr_id.id),
        #                    ('active', '=', True),
        #                    ('contract_id', '=', rec.contract_id.id)
        #                 ])
        #             bl_arr = bl_ids.mapped('backlog_amount')
        #             arr_amt = sum(bl_arr)
        #             values = {'retenue_arr': arr_amt}
        #             _logger.info('\n=== SOMME RETENUE = %s ===\n' % values)
        #             rec.contract_id.write(values)
        #     elif rec.request_id.id == as_aro_id:
        #         if rec.contract_id.retenue_as_aro == 0.00:
        #             rec.contract_id.write({'retenue_as_aro': vals.get('backlog_amount')})
        #         else:
        #             arr_amt=rec.backlog_amount
        #             bl_ids = self.search(
        #                 [
        #                    ('request_id', '=', as_aro_id.id),
        #                    ('active', '=', True),
        #                    ('contract_id', '=', rec.contract_id.id)
        #                 ])
        #             bl_arr = bl_ids.mapped('backlog_amount')
        #             arr_amt = sum(bl_arr)
        #             values = {'retenue_as_aro': arr_amt}
        #             _logger.info('\n=== SOMME RETENUE = %s ===\n' % values)
        #             rec.contract_id.write(values)
        #     elif rec.request_id.id == ksa_id:
        #         if rec.contract_id.retenue_ksa == 0.00:
        #             _logger.info("\n === REACTIVATION KSA = ")
        #             rec.contract_id.write({'retenue_ksa': vals.get('backlog_amount')})
        #         else:
        #             arr_amt=rec.backlog_amount
        #             bl_ids = self.search(
        #                 [
        #                    ('request_id', '=', ksa_id.id),
        #                    ('active', '=', True),
        #                    ('contract_id', '=', rec.contract_id.id)
        #                 ])
        #             bl_arr = bl_ids.mapped('backlog_amount')
        #             arr_amt = sum(bl_arr)
        #             values = {'retenue_ksa': arr_amt}
        #             _logger.info('\n=== SOMME RETENUE = %s ===\n' % values)
        #             rec.contract_id.write(values)
        #return res

    @api.model
    def create(self,vals):
        res = super(HrBacklog, self).create(vals)
        
        blog_type_obj = self.env['hr.backlog.type']
        arr_id = blog_type_obj.search([('code', '=', 'ARR')])
        as_aro_id = blog_type_obj.search([('code', '=','OP AS ARO')])
        ins_id = blog_type_obj.search([('code', '=', 'ASS')])
        div_id = blog_type_obj.search([('code', '=', 'DIV')])
        ksa_id = blog_type_obj.search([('code', '=', 'KSA')])
        mal_id = blog_type_obj.search([('code', '=', 'MAL')])
        vam_id = blog_type_obj.search([('code', '=', 'VAM')])

        #ass_amt=self.mapped('contract_id.employee_backlog_ids').search([('request_id','=',ass_id)]).backlog_amount
        #backlog=self.browse(backlog_ids)

        #    arr_id=employee_backlog.request_id.search([('code','=','ARR')]).id
        #    _logger.info('\n=== ID ARRIERES = %s ===\n' % arr_id)
        values = {}
        arr_amt = res.backlog_amount

        #if res.request_id.id == arr_id.id and res.active == True:
        if res.request_id.id == arr_id.id:
            bl_ids = self.search(
                [
                    ('request_id', '=', arr_id.id),
                    ('active', '=', True),
                    ('contract_id', '=', res.contract_id.id)
                ])
            bl_arr = bl_ids.mapped('backlog_amount')
            _logger.info('\n=== bl_ids = %s ===\n' % bl_ids)
            _logger.info('\n=== bl_arr = %s ===\n' % bl_arr)
            arr_amt = sum(bl_arr)
            values = {'retenue_arr': arr_amt}
            _logger.info('\n=== values = %s ===\n' % values)
        elif res.request_id.id == ins_id.id:
            bl_ids = self.search(
                [
                    ('request_id', '=', ins_id.id),
                    ('active', '=', True),
                    ('contract_id', '=', res.contract_id.id)
                ])
            bl_ins = bl_ids.mapped('backlog_amount')
            arr_amt = sum(bl_ins)
            values = {'retenue_assurance': arr_amt}
        elif res.request_id.id == as_aro_id.id:
            bl_ids = self.search(
                [
                    ('request_id', '=', as_aro_id.id),
                    ('active', '=', True),
                    ('contract_id', '=', res.contract_id.id)
                ])
            bl_as_aro = bl_ids.mapped('backlog_amount')
            arr_amt = sum(bl_as_aro)
            values = {'retenue_as_aro': arr_amt}
        elif res.request_id.id == div_id.id:
            bl_ids = self.search(
                [
                    ('request_id', '=', div_id.id),
                    ('active', '=', True),
                    ('contract_id', '=', res.contract_id.id)
                ])
            bl_divers = bl_ids.mapped('backlog_amount')
            arr_amt = sum(bl_divers)
            values = {'retenue_divers': arr_amt}
        elif res.request_id.id == ksa_id.id:
            bl_ids = self.search(
                [
                    ('request_id', '=', ksa_id.id),
                    ('active', '=', True),
                    ('contract_id', '=', res.contract_id.id)
                ])
            bl_ksa = bl_ids.mapped('backlog_amount')
            arr_amt = sum(bl_ksa)
            values = {'retenue_ksa': arr_amt}
        elif res.request_id.id == mal_id.id:
            bl_ids = self.search(
                [
                    ('request_id', '=', mal_id.id),
                    ('active', '=', True),
                    ('contract_id', '=', res.contract_id.id)
                ])
            bl_mal = bl_ids.mapped('backlog_amount')
            arr_amt = sum(bl_mal)
            values = {'retenue_maladie': arr_amt}
        elif res.request_id.id == vam_id.id:
            bl_ids = self.search(
                [
                    ('request_id', '=', vam_id.id),
                    ('active', '=', True),
                    ('contract_id', '=', res.contract_id.id)
                ])
            bl_vam = bl_ids.mapped('backlog_amount')
            arr_amt = sum(bl_vam)
            values = {'retenue_vam': arr_amt}

        res.contract_id.write(values)
        #arr_amt = res.mapped('contract_id.employee_backlog_ids').search([('request_id','=',arr_id)]).backlog_amount
        # _logger.info('\n=== ARR AMOUNT = %s ===\n' % arr_amt)

        # values={'retenue_arr': arr_amt}
        # res.contract_id.write(values)
        return res

class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Rajouter le nom dans le champ de selection de contract_id'

    @api.multi
    def name_get(self):
        result = super(HrContract,self).name_get()
        res = []
        print("result = %s" % result)
        for rec in result:
            # rec = (rec.id,  r_name)
            el_obj = self.browse(rec[0])
            #r_name = rec[1] + ' '+ '[' + el_obj.annee + ']'+ ' '+ '[' + el_obj.employee_id.name.name + ']'
            r_name = rec[1] + ' '+ '[' + el_obj.employee_id.name + ']'
            res.append((el_obj.id,  r_name))
        return res

    #seniority = fields.Integer(string=u'Ancienneté')
    employee_seniority = fields.Integer(string=u'Ancienneté',related='employee_id.employee_seniority_for_payroll')
    avance_quinze = fields.Float(string=u'Avance du 15')
    avex = fields.Float(string=u'Avance exceptionnelle')
    ppe = fields.Float(string=u'Prêt Petit Equipement')
    ph = fields.Float(string=u'Prêt Hypothécaire')
    employee_backlog_ids = fields.One2many('hr.backlog','contract_id',string=u'Arriérés')
    employee_loan_request_ids = fields.One2many('hr.loan.request','contract_id',string=u'Echéancier')
    retenue_avance_quinze = fields.Float(string=u'Montant Avance du 15')
    retenue_avex = fields.Float(string=u'Montant Avance exceptionnelle')
    retenue_ppe = fields.Float(string=u'Montant Prêt Petit Equipement')
    retenue_ph = fields.Float(string=u'Montant Prêt Hypothécaire')
    #test_ph = fields.Float(string=u'Montant Prêt Hypothécaire',compute="get_loan_request_amount",store=True)
    retenue_arr = fields.Float(string=u'Arriérés')
    retenue_as_aro = fields.Float(string=u'AS ARO')
    retenue_assurance = fields.Float(string=u'Assurance')
    retenue_divers = fields.Float(string=u'Divers')
    retenue_ksa = fields.Float(string=u'Opération KSA')
    retenue_maladie = fields.Float(string=u'Sinitre maladie')
    retenue_vam = fields.Float(string=u'Opération VAM')

    @api.multi
    @api.onchange('employee_loan_request_ids')
    def get_loan_request_amount(self):
        _logger.info('\n=== ctx = %s ===\n' % self._context)
        _logger.info('\n=== line_ids = %s ===\n' % self.employee_loan_request_ids)
        ctt_obj = self.browse([self._context.get('default_contract_id')])
        _logger.info('\n=== ctt_obj = %s ===\n' % ctt_obj)
        vals = {}
        for employee_loan_request_id in ctt_obj.employee_loan_request_ids:
            _logger.info("\n === RETENUE = %s" %employee_loan_request_id.contract_id)
            code_retenue_15=employee_loan_request_id.request_id.search([('code','=','AV15')]).id
            code_retenue_avex=employee_loan_request_id.request_id.search([('code','=','AVEX')]).id
            code_retenue_ppe=employee_loan_request_id.request_id.search([('code','=','PPE')]).id
            code_retenue_ph=employee_loan_request_id.request_id.search([('code','=','PH')]).id
            if employee_loan_request_id.request_id.id == code_retenue_15:
                vals['retenue_avance_quinze'] = employee_loan_request_id.somme_retenue
                ctt_obj.write(vals)
            elif employee_loan_request_id.request_id.id == code_retenue_avex:
                vals['retenue_avex'] = employee_loan_request_id.somme_retenue
                ctt_obj.write(vals)
            elif employee_loan_request_id.request_id.id == code_retenue_ppe:
                vals['retenue_ppe'] = employee_loan_request_id.somme_retenue
                ctt_obj.write(vals)
            elif employee_loan_request_id.request_id.id == code_retenue_ph:
                vals['retenue_ph'] = employee_loan_request_id.somme_retenue
                ctt_obj.write(vals)

    @api.multi
    @api.onchange('employee_backlog_ids')
    def get_backlog_amount(self):
        ctt_obj = self.browse([self._context.get('default_contract_id')])
        vals = {}
        for employee_backlog_id in ctt_obj.employee_backlog_ids:
            code_arr=employee_backlog_id.request_id.search([('code','=','ARR')]).id
            if employee_backlog_id.request_id.id == code_arr:
                vals['retenue_arr'] = employee_backlog_id.backlog_amount
                ctt_obj.write(vals)
            elif employee_backlog_id.request_id.id == 2:
                vals['retenue_as_aro'] = employee_backlog_id.backlog_amount
                ctt_obj.write(vals)
            elif employee_backlog_id.request_id.id == 3:
                vals['retenue_assurance'] = employee_backlog_id.backlog_amount
                ctt_obj.write(vals)
            elif employee_backlog_id.request_id.id == 4:
                vals['retenue_divers'] = employee_backlog_id.backlog_amount
                ctt_obj.write(vals)
            elif employee_backlog_id.request_id.id == 5:
                vals['retenue_ksa'] = employee_backlog_id.backlog_amount
                ctt_obj.write(vals)
            elif employee_backlog_id.request_id.id == 6:
                vals['retenue_maladie'] = employee_backlog_id.backlog_amount
                ctt_obj.write(vals)
            elif employee_backlog_id.request_id.id == 7:
                vals['retenue_vam'] = employee_backlog_id.backlog_amount
                ctt_obj.write(vals)



    # @api.multi
    # @api.onchange('wage','prime_anciennete','indemnite_transport','indemnite_logement','retenue_ph','retenue_avex','retenue_ppe','retenue_ph','retenue_ksa')
    # def get_quotite_cessible(self):
    #     for emp_contract in self:
    #         retenue_max=(emp_contract.wage+emp_contract.prime_anciennete+emp_contract.indemnite_transport+emp_contract.indemnite_logement)/2
    #         remboursement_en_cours=emp_contract.retenue_avex+emp_contract.retenue_ppe+emp_contract.retenue_ph+emp_contract.retenue_ksa
    #         result=retenue_max-remboursement_en_cours
    #         _logger.info('\n=== QUOTITE AVANCE 15 = %s ===\n' % result)
    #         emp_contract.avance_quinze=result
    #         result_1=((emp_contract.wage+emp_contract.prime_anciennete+emp_contract.indemnite_transport+emp_contract.indemnite_logement)*0.3)
    #         emp_contract.avex=result_1 *12
    #         qcr=result_1 - emp_contract.remboursement_pret_hypothecaire
    #         result_3=(qcr/3.042)*100
    #         emp_contract.ppe=result_3
    #         result_4=((emp_contract.wage+emp_contract.prime_anciennete+emp_contract.indemnite_transport)*0.3)+emp_contract.indemnite_logement
    #         emp_contract.ph=result_4

    # @api.multi
    # def get_quotite_saisissable(self):
    #     for emp_contract in self:
    #         retenue_max=(emp_contract.wage+emp_contract.prime_anciennete+emp_contract.indemnite_transport+emp_contract.indemnite_logement)/2
    #         remboursement_en_cours=emp_contract.retenue_avex+emp_contract.retenue_ppe+emp_contract.retenue_ph+emp_contract.retenue_ksa
    #         result=retenue_max-remboursement_en_cours
    #         emp_contract.avance_quinze=result
    #         _logger.info('\n=== QUOTITE AVANCE 15 = %s ===\n' % result)



    @api.multi
    def button_quotite(self):
        for emp_contract in self:
            retenue_max=(emp_contract.wage+emp_contract.prime_anciennete+emp_contract.indemnite_transport+emp_contract.indemnite_logement)/2
            remboursement_en_cours=emp_contract.retenue_avex+emp_contract.retenue_ppe+emp_contract.retenue_ph+emp_contract.retenue_ksa
            result=retenue_max-remboursement_en_cours
            _logger.info('\n=== QUOTITE AVANCE 15 = %s ===\n' % result)
            emp_contract.avance_quinze=result

    @api.multi
    def button_update_backlog(self):
        emp_blog=self.env['hr.backlog']
        #emp_blog_active=emp_blog.search([('active','=',True),('contract_id','=',self.id)])
        emp_blog_active=emp_blog.search([('active','=',True)])
        _logger.info('\n=== ACTIVE = %s ===\n' % emp_blog_active)
        # bl_active=emp_blog_active.mapped('active')
        # bl_date_end=emp_blog_active.mapped('date_end')
        # res={}
        # i=0
        # len_bl_date_end=len(bl_date_end)
        for rec_blog in emp_blog_active:
            # while i<len_bl_date_end:
            # date_string=str(bl_date_end[i])
            day_end=datetime.datetime.strptime(rec_blog.date_end,'%Y-%m-%d')
            _logger.info('\n=== day_end = %s ===\n' % day_end)
            days=datetime.datetime.now()-day_end
            remaining_day=days.days
                # _logger.info('\n=== ECHEANCE = %s ===\n' % bl_date_end[i])
            _logger.info('\n=== JOURS RESTANT= %s ===\n' % days)
                # _logger.info('\n=== REMAINING DAY= %s ===\n' % remaining_day)
            if remaining_day > 0:
                _logger.info('\n === ECHU = %s === \n' % rec_blog)
                rec_blog.write({'active':False})
        #             res=rec_blog.active
        #             _logger.info('\n=== STATUT= %s ===\n' % res)
        #         else:
        #             _logger.info("\n === EN COURS = ")
        #             rec_blog.active=True
        #             res=rec_blog.active
        #             _logger.info('\n=== STATUT= %s ===\n' % res)
        #         i+=1
        
            
    @api.multi
    def button_update_loan(self):
        emp_loan_request=self.env['hr.loan.request']
        emp_loan_request_active=emp_loan_request.search([('active','=',True)])
        _logger.info('\n=== ACTIVE LOAN = %s ===\n' % emp_loan_request_active)
        for rec_loan in emp_loan_request_active:
            day_end=datetime.datetime.strptime(rec_loan.date_end,'%Y-%m-%d')
            _logger.info('\n=== day_end = %s ===\n' % day_end)
            days=datetime.datetime.now()-day_end
            remaining_day=days.days
            _logger.info('\n=== JOURS RESTANT= %s ===\n' % days)
            if remaining_day > 0:
                _logger.info('\n === ECHU = %s === \n' % rec_loan)
                rec_loan.write({'active':False})











