# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning, UserError
from odoo.tools.float_utils import float_compare, float_is_zero

from ..models.model_const import ACCOUNT_BANK_STATEMENT_LINE_MAPPING, ACCOUNT_VOUCHER


class AccountMoveUSA(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'account.caching.mixin.usa', 'mail.thread', 'mail.activity.mixin']

    has_been_reviewed = fields.Boolean(compute='_compute_has_been_reviewed')
    state = fields.Selection(track_visibility='onchange')

    @api.multi
    def _compute_has_been_reviewed(self):
        for record in self:
            reviewed_transactions = self.env['account.bank.statement.line'].search([
                ('status', '=', 'confirm'),
                ('applied_aml_ids', 'in', record.line_ids.ids)])

            # if it's reconciled, show error instead of confirmation
            reconciled_move_lines = record.line_ids.filtered(lambda x: x.bank_reconciled)

            if reviewed_transactions and not reconciled_move_lines:
                record.has_been_reviewed = True

    @api.multi
    def _reconcile_warning(self):
        # only check if cancel from button in JE's form
        if self.env.context.get('reconciled_warning', False):
            for record in self:
                reconciled_move_lines = record.line_ids.filtered(lambda x: x.bank_reconciled)
                if reconciled_move_lines:
                    raise UserError(_('This transaction was reconciled. Please unreconcile it first.'))

    @api.multi
    def _match_warning(self):
        # only check if cancel from button in JE's form
        if self.env.context.get('reconciled_warning', False):
            for record in self:
                matched_lines = record.line_ids.filtered(lambda x: x.matched_debit_ids or x.matched_credit_ids or x.full_reconcile_id)
                if matched_lines:
                    raise UserError(_('This journal entry has already been matched with other transactions. Please unmatch it first.'))


    @api.multi
    def post(self, invoice=False):
        self._post_validate()
        tracking = set()
        for move in self:
            move.line_ids.create_analytic_lines()
            if move.name == '/':
                new_name = False
                journal = move.journal_id

                if invoice and invoice.move_name and invoice.move_name != '/':
                    new_name = invoice.move_name
                else:
                    if journal.sequence_id:
                        # If invoice is actually refund and journal has a refund_sequence then use
                        # that one or use the regular one
                        sequence = journal.sequence_id
                        if invoice and invoice.type in ['out_refund', 'in_refund']:
                            if invoice.is_write_off:
                                sequence = journal.write_off_sequence_id
                            elif journal.refund_sequence:
                                if not journal.refund_sequence_id:
                                    raise UserError('Please define a sequence for the credit notes')
                                sequence = journal.refund_sequence_id

                        new_name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
                    else:
                        raise UserError('Please define a sequence on the journal.')

                if new_name:
                    move.name = new_name

            journal_name = move.journal_id.name
            if journal_name not in tracking:
                # Enable trigger to run finding possible match
                self.trigger_apply_matching(self.build_batch_deposit_key(journal_name))
                self.trigger_apply_matching(self.build_journal_item_key(journal_name))

                tracking.add(journal_name)

            if move == move.company_id.account_opening_move_id and not move.company_id.account_bank_reconciliation_start:
                # For opening moves, we set the reconciliation date threshold
                # to the move's date if it wasn't already set (we don't want
                # to have to reconcile all the older payments -made before
                # installing Accounting- with bank statements)
                move.company_id.account_bank_reconciliation_start = move.date

        return self.write({'state': 'posted'})

    @api.multi
    def button_cancel(self):
        # Show error when JE is already matched with other transactions
        self._match_warning()

        # Show error when JE is already reconciled
        self._reconcile_warning()

        result = super(AccountMoveUSA, self).button_cancel()

        for record in self:
            journal_name = record._get_journal_name()
            # Enable trigger to run finding possible match
            self.trigger_apply_matching(self.build_batch_deposit_key(journal_name))
            self.trigger_apply_matching(self.build_journal_item_key(journal_name))

        # uncheck aml when cancel
        self.mapped('line_ids').write({'temporary_reconciled': False})

        # Trigger function to update Changes in reconciliation report
        reconciliation_line_ids = self.env['account.bank.reconciliation.data.line'].search([('aml_id',
                                                                                             'in', self.line_ids.ids)])
        reconciliation_line_ids.compute_change_status()
        return result

    def _get_journal_name(self):
        account_voucher = self.env[ACCOUNT_VOUCHER].search([('move_id', '=', self.id)])
        return account_voucher.payment_journal_id.name if account_voucher else self.journal_id.name

    @api.multi
    def reverse_moves(self, date=None, journal_id=None, auto=False):
        # Show error when JE is already reconciled
        # bypass if undo last reconciliation
        if not self.env.context.get('discrepancy_entry', False):
            self.with_context(reconciled_warning = True)._reconcile_warning()

        result = super(AccountMoveUSA, self).reverse_moves(date, journal_id, auto)

        tracking = set()
        for move in self:
            journal_name = move.journal_id.name
            if journal_name not in tracking:
                # Enable trigger to run finding possible match
                self.trigger_apply_matching(self.build_batch_deposit_key(journal_name))
                self.trigger_apply_matching(self.build_journal_item_key(journal_name))

                tracking.add(journal_name)

        return result

    def _log_message_move(self, values):
        if 'line_ids' in values:
            for record in self:
                msg = "<b>Journal Entry lines have been updated:</b><ul>"
                for line in record.line_ids:
                    msg += "<li>{}: {}</li>".format(line.account_id.name, line.balance)
                msg += "</ul>"
                record.message_post(body=msg, message_type="comment", subtype="mail.mt_note")

    @api.multi
    def write(self, values):
        res = super().write(values)
        self._log_message_move(values)
        return res

    @api.model
    def create(self, values):
        res = super().create(values)
        res._log_message_move(values)
        return res


class AccountMoveLineUSA(models.Model):
    _name = 'account.move.line'
    _inherit = ['account.move.line', 'account.caching.mixin.usa']

    temporary_reconciled = fields.Boolean()
    bank_reconciled = fields.Boolean()
    is_fund_line = fields.Boolean()

    @api.multi
    def update_temporary_reconciled(self, ids, checked):
        return self.browse(ids).write({'temporary_reconciled': checked})

    @api.multi
    def mark_bank_reconciled(self):
        self.write({'bank_reconciled': True})
        payment_ids = self.filtered(lambda aml: aml.payment_id).mapped('payment_id')
        payment_ids.write({'state': 'reconciled'})

    @api.multi
    def undo_bank_reconciled(self):
        self.write({'bank_reconciled': False})
        payment_ids = self.filtered(lambda aml: aml.payment_id).mapped('payment_id')
        payment_ids.write({'state': 'posted'})

    @api.model
    def create(self, values):
        result = super(AccountMoveLineUSA, self).create(values)

        journal_name = result.journal_id.name
        self.trigger_apply_matching(self.build_batch_deposit_key(journal_name))
        self.trigger_apply_matching(self.build_journal_item_key(journal_name))

        return result

    @api.multi
    def unlink(self):
        # If we delete the journal entry, we must delete a bank statement line mapping manually to call computed fields
        self.env[ACCOUNT_BANK_STATEMENT_LINE_MAPPING].search([('journal_entry_id', 'in', self.ids)]).sudo().unlink()

        tracking = set()
        for record in self:
            journal_name = record.journal_id.name
            if journal_name in tracking:
                continue

            self.trigger_apply_matching(self.build_batch_deposit_key(journal_name))
            self.trigger_apply_matching(self.build_journal_item_key(journal_name))

            tracking.add(journal_name)

        result = super(AccountMoveLineUSA, self).unlink()

        return result

    # get partial reconcile moves to unlink
    def _get_rec_move_ids(self, part_rec_ids, invoice_id, side):
        rec_move_ids = self.env['account.partial.reconcile']
        aml_to_keep = invoice_id.move_id.line_ids | invoice_id.move_id.line_ids.mapped('full_reconcile_id.exchange_move_id.line_ids')
        if side == 'debit':
            for rec in part_rec_ids:
                if rec.debit_move_id.id in aml_to_keep.ids:
                    rec_move_ids += rec
        else:
            for rec in part_rec_ids:
                if rec.credit_move_id.id in aml_to_keep.ids:
                    rec_move_ids += rec
        return rec_move_ids

    @api.multi
    def remove_move_reconcile(self):
        # override Odoo's function, change original un-reconcile
        if not self:
            return True
        rec_move_ids = self.env['account.partial.reconcile']
        for account_move_line in self:
            account_move_line.move_id._check_lock_date()
            id = self.env.context.get('invoice_id', False)
            if id:  # un-reconcile in Invoice form
                invoice = self.env['account.invoice'].browse(id)
                if account_move_line in invoice.payment_move_line_ids:
                    account_move_line.payment_id.write({'invoice_ids': [(3, invoice.id, None)]})

                    # remove journal item to Payment
                    if account_move_line.payment_id:
                        remove_lines = account_move_line.payment_id.open_invoice_ids.filtered(lambda x:
                                                                                             x.invoice_id.id == id)
                        account_move_line.payment_id.write({'open_invoice_ids': [(3, line.id, None) for line in remove_lines]})

                    rec_move_ids += self._get_rec_move_ids(account_move_line.matched_debit_ids, invoice, 'debit')
                    rec_move_ids += self._get_rec_move_ids(account_move_line.matched_credit_ids, invoice, 'credit')
            else:  # general case
                account_move_line.payment_id.write({'invoice_ids': [(5,)], 'open_invoice_ids': [(5,)]})  # unlink
                rec_move_ids += account_move_line.matched_debit_ids
                rec_move_ids += account_move_line.matched_credit_ids

        return rec_move_ids.unlink()

    # override to reconcile partial amount
    @api.multi
    def _reconcile_lines(self, debit_moves, credit_moves, field):
        """ This function loops on the 2 recordsets given as parameter as long as it
            can find a debit and a credit to reconcile together. It returns the recordset of the
            account move lines that were not reconciled during the process.
        """
        (debit_moves + credit_moves).read([field])
        to_create = []
        cash_basis = debit_moves and debit_moves[0].account_id.internal_type in ('receivable', 'payable') or False
        cash_basis_percentage_before_rec = {}

        # get partial amount
        partial_total = self.env.context.get('partial_amount', False)
        is_partial = True if partial_total else False

        while (debit_moves and credit_moves):
            debit_move = debit_moves[0]
            credit_move = credit_moves[0]
            company_currency = debit_move.company_id.currency_id
            # We need those temporary value otherwise the computation might be wrong below
            temp_amount_residual = min(debit_move.amount_residual, -credit_move.amount_residual)
            temp_amount_residual_currency = min(debit_move.amount_residual_currency, -credit_move.amount_residual_currency)
            amount_reconcile = min(debit_move[field], -credit_move[field])

            # # TODO: Support multi currencies
            if is_partial:
                if float_is_zero(partial_total, precision_digits=2):
                    break

                amount_reconcile = min(amount_reconcile, partial_total)
                partial_total -= amount_reconcile

                if not debit_move.currency_id and not credit_move.currency_id:  # expressed in company currency
                    temp_amount_residual = amount_reconcile
                    temp_amount_residual_currency = 0
                # elif debit_move.currency_id and debit_move.currency_id == credit_move.currency_id:
                #     temp_amount_residual = self._convert_amount(debit_move.currency_id, company_currency, amount_reconcile)
                #     temp_amount_residual_currency = amount_reconcile

            #Remove from recordset the one(s) that will be totally reconciled
            # For optimization purpose, the creation of the partial_reconcile are done at the end,
            # therefore during the process of reconciling several move lines, there are actually no recompute performed by the orm
            # and thus the amount_residual are not recomputed, hence we have to do it manually.
            if amount_reconcile == debit_move[field]:
                debit_moves -= debit_move
            else:
                debit_moves[0].amount_residual -= temp_amount_residual
                debit_moves[0].amount_residual_currency -= temp_amount_residual_currency

            if amount_reconcile == -credit_move[field]:
                credit_moves -= credit_move
            else:
                credit_moves[0].amount_residual += temp_amount_residual
                credit_moves[0].amount_residual_currency += temp_amount_residual_currency
            #Check for the currency and amount_currency we can set
            currency = False
            amount_reconcile_currency = 0
            if field == 'amount_residual_currency':
                currency = credit_move.currency_id.id
                amount_reconcile_currency = temp_amount_residual_currency
                amount_reconcile = temp_amount_residual

            if cash_basis:
                tmp_set = debit_move | credit_move
                cash_basis_percentage_before_rec.update(tmp_set._get_matched_percentage())

            to_create.append({
                'debit_move_id': debit_move.id,
                'credit_move_id': credit_move.id,
                'amount': amount_reconcile,
                'amount_currency': amount_reconcile_currency,
                'currency_id': currency,
            })

            # if self.env.context.get('partial_amount', False):
            #     break

        part_rec = self.env['account.partial.reconcile']
        index = 0
        with self.env.norecompute():
            for partial_rec_dict in to_create:
                new_rec = self.env['account.partial.reconcile'].create(partial_rec_dict)
                part_rec += new_rec
                if cash_basis:
                    new_rec.create_tax_cash_basis_entry(cash_basis_percentage_before_rec)
                    index += 1
        self.recompute()

        return debit_moves+credit_moves

    @api.multi
    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        """
        This function is to add applied journal items to payment.

        CUSTOMER PAYMENT:
        Payment is credit move.
        Invoices and opening balance are debit move.
        """
        debit_moves = self.filtered(lambda r: r.debit != 0 or r.amount_currency > 0)
        credit_moves = self.filtered(lambda r: r.credit != 0 or r.amount_currency < 0)
        debit_moves = debit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
        credit_moves = credit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))

        res = super(AccountMoveLineUSA, self).reconcile(writeoff_acc_id, writeoff_journal_id)

        # Customer Payment
        if not credit_moves or not debit_moves:
            return res

        internal_type = 'receivable'
        invoice_amls = []
        payment_move = False
        if credit_moves and credit_moves[0].account_id.internal_type == 'receivable':
            payment_move = credit_moves[0]
            invoice_amls = debit_moves
        elif debit_moves and debit_moves[0].account_id.internal_type == 'payable':
            payment_move = debit_moves[0]
            invoice_amls = credit_moves
            internal_type = 'payable'

        if not payment_move or not invoice_amls:
            return res

        if payment_move.payment_id:
            payment = payment_move.payment_id
            for invoice_aml in invoice_amls:
                total_amount = self._get_payment_amount(invoice_aml, payment_move, internal_type)

                if not total_amount:
                    continue

                existing_ids = [line.account_move_line_id.id for line in payment.open_invoice_ids]
                if invoice_aml.id not in existing_ids:
                    payment.with_context(usa_reconcile=True).write(
                        {'open_invoice_ids': [(0, 0, {'account_move_line_id': invoice_aml.id,
                                                      'payment': total_amount})]})
                else:
                    update_line = payment.open_invoice_ids.filtered(lambda x: x.account_move_line_id == invoice_aml)
                    payment.with_context(usa_reconcile=True).write(
                        {'open_invoice_ids': [(1, update_line.id, {'payment': total_amount})]})

        return res

    def _get_payment_amount(self, invoice_aml, payment_move, internal_type):
        if not internal_type:
            return False

        payment = payment_move.payment_id
        match_field = 'matched_credit_ids'
        side_field = 'credit_move_id'
        if internal_type == 'payable':
            match_field = 'matched_debit_ids'
            side_field = 'debit_move_id'

        to_currency = payment.currency_id
        return sum([self._convert_amount(False, to_currency, p.amount, p)
                    for p in invoice_aml[match_field] if p[side_field] in payment.move_line_ids])

    def _convert_amount(self, from_currency, to_currency, amount, partial_reconcile=None):
        if partial_reconcile and partial_reconcile.currency_id == to_currency:
            return partial_reconcile.amount_currency

        company_id = self.env.user.company_id
        from_currency = from_currency or company_id.currency_id
        if from_currency != to_currency:
            return from_currency._convert(amount, to_currency, company_id, fields.Date.today())
        return amount
