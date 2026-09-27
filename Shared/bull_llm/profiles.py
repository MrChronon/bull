"""Validation boundary for versioned tested-profile hand-offs."""

from __future__ import annotations
from copy import deepcopy

from .schemas import TESTED_PROFILE_SCHEMA,TESTED_PROFILE_SCHEMA_VERSION


def validate_tested_profiles_document(value):
    if not isinstance(value,dict):
        raise ValueError('tested profiles document must be an object')
    if value.get('schema')!=TESTED_PROFILE_SCHEMA or value.get('schema_version')!=TESTED_PROFILE_SCHEMA_VERSION:
        raise ValueError(f'expected {TESTED_PROFILE_SCHEMA} v{TESTED_PROFILE_SCHEMA_VERSION}')
    profiles=value.get('profiles')
    if not isinstance(profiles,list):
        raise ValueError('profiles must be an array')
    ids=set()
    for row in profiles:
        if not isinstance(row,dict) or not row.get('profile_id') or not row.get('model'):
            raise ValueError('each tested profile needs profile_id and model')
        if row['profile_id'] in ids:
            raise ValueError('profile_id must be unique')
        ids.add(row['profile_id'])
        if not isinstance(row.get('client_profile'),dict):
            raise ValueError('each tested profile needs client_profile')
    return deepcopy(value)


def select_tested_profile(document,selector):
    checked=validate_tested_profiles_document(document)
    matches=[row for row in checked['profiles'] if row['profile_id']==selector or row['model']==selector]
    if len(matches)!=1:
        raise ValueError('selector must resolve to exactly one tested profile')
    return matches[0]
