# -*- coding: utf-8 -*-
##############################################################################

#    Copyright (C) 2020 Novobi LLC (<http://novobi.com>)
#
##############################################################################
from odoo import models, fields, api, _


class ProjectTask(models.Model):
    _inherit = 'project.task'
    _order = 'date_deadline, name'


class ProjectSite(models.Model):
    _inherit = 'project.site'
    _order = 'name'
