# -*- coding: utf-8 -*-
# Copyright (c) 2023 Benoit Kohler
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    BASE = r"""
requirements:
  - xxx
options:
  infrahub_url:
    description:
      - The URL of the Infrahub instance.
      - Must be accessible by the Ansible control host.
    required: true
    type: str
  infrahub_token:
    description:
      - The infrahub API token.
    required: true
    type: str
  api_version:
    description:
      - "API Version Infrahub API"
    required: false
    type: str
"""

    TAGS = r"""
options:
  tags:
    description:
      - "Any tags that this item may need to be associated with"
    required: false
    type: list
    elements: raw
"""
