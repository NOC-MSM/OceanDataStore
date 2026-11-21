# ===================================================================
# Copyright 2026 National Oceanography Centre
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
# ===================================================================
"""
logging.py

Description:
This module defines the logging utility function for the OceanDataStore
package.

Authors:
    - Ollie Tooth
"""

import logging
import sys

from OceanDataStore import __version__

logger = logging.getLogger(__name__)

_BANNER = """
         .~~~.
       .(     ).~~~~~~.
     ~(               ).~~~.
   .(    OceanDataStore     ).
  (___________________________).
          version: %s

"""


def initialise_logging() -> None:
    """
    Initialise OceanDataStore logging.

    Configures the root logger to write INFO-level messages to stdout
    and logs the OceanDataStore banner and version.
    """
    logging.basicConfig(
        stream=sys.stdout,
        format="🌐  OceanDataStore  🌐 | %(levelname)10s | %(asctime)s | %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info(_BANNER, __version__)
