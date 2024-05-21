# -*- coding: utf-8 -*-
# Copyright (c) 2023 Benoit Kohler
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    BASE = r"""
requirements:
  - infrahub_sdk
options:
  api_endpoint:
    description: Endpoint of the Infrahub API
    required: True
    env:
        - name: INFRAHUB_ADDRESS
  token:
    required: True
    description:
        - Infrahub API token to be able to read against Infrahub.
    env:
        - name: INFRAHUB_API_TOKEN
  timeout:
    required: False
    description: Timeout for Infrahub requests in seconds
    type: int
    default: 10
  branch:
    required: False
    description:
        - Branch in which the request is made
    type: str
    default: main
  validate_certs:
    description:
        - Whether or not to validate SSL of the Infrahub instance
    required: False
    default: True
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
