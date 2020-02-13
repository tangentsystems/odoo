from datetime import datetime, date

from .time_utils import BY_DAY, BY_WEEK, BY_MONTH, BY_QUARTER, BY_YEAR, \
    get_start_end_date_value_with_delta, \
    get_same_date_delta_period


def get_json_render(data_type, extend, data_render,
                    name_card, selection, function_retrieve,
                    extra_param, currency_id, extra_graph_setting={}):
    return {
        'function_retrieve': function_retrieve,
        'data_type': data_type,
        'extend': extend,
        'data_render': data_render,
        'name': name_card,
        'selection': selection,
        'extra_param': extra_param,
        'extra_graph_setting': extra_graph_setting,
        'currency_id': currency_id,
    }

def get_json_data_for_selection(self, selection, periods, default_selection):
    """ Function return json setting for fields selection time, that defined
    in variables "period_by_month" and "period_by_complex"

    :param periods:
    :param selection:
    :return:
    """

    for period in periods:
        start, end = get_start_end_date_value_with_delta(self, datetime.now(), period['t'], period['d'])

        # If period is compute to today we will convert the end day to the date of same period
        if period.get('td', False):
            month = 0
            if period['t'] == BY_QUARTER:
                month = end.month - (datetime.now().month%3 - 3)
            elif period['t'] == BY_YEAR:
                month = datetime.now().month
            end = get_same_date_delta_period(end, day=datetime.now().day, month=month)

        period_selection = {
            'n': period['n'],  # What will show in selection field
            's': start.strftime('%Y-%m-%d'),  # start date of that period base on current time
            'e': end.strftime('%Y-%m-%d'),  # end date of that period base on current time
            'd': period['n'] == default_selection  # var bool to check what will be chosen defaultly
        }

        # Append and setting for case return the type period used to group in data return
        # instead of by month in default
        if period.setdefault('k', BY_MONTH):
            period_selection['k'] = period['k']
        selection.append(period_selection)


def push_to_list_lists_at_timestamp(lists, values, list_time_name, format):
    for (idx, list) in enumerate(lists):
        push_to_list_values_at_timestamp(list, values[idx], list_time_name, format)

def push_to_list_values_at_timestamp(list, value, list_time_name, period_type, x=None):
    name = get_chart_point_name(list_time_name, period_type)
    list.append({
        'x': x or len(list),
        'y': value,
        'name': name
    })

def push_to_list_values_to_sales(past_sale_values,
                                 future_sale_values, value, index,
                                 list_time_name, period_type, x=None):
    if list_time_name[0] <= date.today():
        push_to_list_values_at_timestamp(
            past_sale_values, value,
            list_time_name, period_type, x=index)
    if list_time_name[1] >= date.today():
        push_to_list_values_at_timestamp(
            future_sale_values, value,
            list_time_name, period_type, x=index)

def get_chart_point_name(list_time_name, period_type):
    """ Function support return the label that will show on each point in chart
     base on list_time_name value and type of period defined in period_type

    :param list_time_name:
    :param period_type:
    :return:
    """
    name = ""
    if len(list_time_name):
        if period_type == BY_DAY:
            date_point = list_time_name[0]
            name = '%s %s/%s' % (date_point.strftime('%a'), date_point.month, date_point.day)
        elif period_type == BY_WEEK:
            first_date = list_time_name[0]
            second_date = list_time_name[1]
            name = '%s-%s' % (first_date.strftime('%d %b'), second_date.strftime('%d %b'))
        elif period_type == BY_MONTH:
            date_point = list_time_name[0]
            name = date_point.strftime('%b %Y')
        elif period_type == BY_QUARTER:
            date_point = list_time_name[0]
            quarter = int((date_point.month - 1) / 3) + 1
            name = 'Q%s %s' % (quarter, date_point.year)
        elif period_type == BY_YEAR:
            date_point = list_time_name[0]
            name = date_point.strftime('%Y')

    return name