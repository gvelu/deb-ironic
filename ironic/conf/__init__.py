# Copyright 2016 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg

from ironic.conf import cimc
from ironic.conf import cisco_ucs
from ironic.conf import conductor
from ironic.conf import console
from ironic.conf import database
from ironic.conf import dhcp

CONF = cfg.CONF

cimc.register_opts(CONF)
cisco_ucs.register_opts(CONF)
conductor.register_opts(CONF)
console.register_opts(CONF)
database.register_opts(CONF)
dhcp.register_opts(CONF)
