# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.


from ..utils.time_utils import BY_MONTH
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ########################################################
    # GENERAL FUNCTION
    ########################################################
    def summarize_group_account(self, date_from, date_to, period_type=BY_MONTH, expenses_domain=[]):
        """

        :param date_from:
        :param date_to:
        :param period_type:
        :param expenses_domain:
        :return:
        """
        _, extend_condition_clause, extend_where_params = self.env['account.move.line']._query_get(
            domain=expenses_domain)
        return self.get_group_account_move_line(date_from, date_to, period_type, extend_condition_clause,
                                                extend_where_params)

    def get_group_account_move_line(self, date_from, date_to, period_type=BY_MONTH, extend_condition_clause="",
                                    extend_where_params=[]):
        """ Function return the group accounts move by time range,
        type of period used to group and some extend condition and
        also corresponding param for the extend condition

        :param date_from:
        :param date_to:
        :param period_type:
        :param extend_condition_clause:
        :param extend_where_params:
        :return:
        """

        sql_params = [period_type, date_from, date_to]
        sql_params.extend(extend_where_params)

        query = """SELECT date_part('year', "account_move_line".date::date) as year,
                            date_part(%s, "account_move_line".date::date) AS period,
                            COUNT (*),
                            MIN("account_move_line".date) as date_in_period,
                            SUM("account_move_line".balance) as total_balance,
                            SUM("account_move_line".credit) as total_credit,
                            SUM("account_move_line".debit) as total_debit

                        FROM "account_move" as "account_move_line__move_id","account_move_line",
                            "account_account" as "account_move_line__account_id"

                        WHERE ("account_move_line"."move_id"="account_move_line__move_id"."id") AND
                            "account_move_line".date >= %s AND
                            "account_move_line".date <= %s AND """ + extend_condition_clause + """
                            GROUP BY year, period
                            ORDER BY year, period;"""

        self.env.cr.execute(query, sql_params)
        data_fetch = self.env.cr.dictfetchall()

        return data_fetch
