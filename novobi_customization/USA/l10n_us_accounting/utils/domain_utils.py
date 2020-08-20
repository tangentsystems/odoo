# Copyright 2020 Novobi
# See LICENSE file for full copyright and licensing details.

INDEX_DOMAIN_FIELD = 0
INDEX_DOMAIN_OPERATOR = 1
INDEX_DOMAIN_VALUE = 2

DOMAIN_LENGTH = 3


def find_domain_by_field(domains, field_name):
    for index, domain in enumerate(domains):
        if len(domain) == DOMAIN_LENGTH and domain[INDEX_DOMAIN_FIELD] == field_name:
            return index
    return -1
