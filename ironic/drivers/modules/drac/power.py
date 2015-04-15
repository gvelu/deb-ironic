#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
DRAC Power Driver using the Base Server Profile
"""

from oslo_utils import excutils
from oslo_utils import importutils

from ironic.common import exception
from ironic.common.i18n import _LE
from ironic.common import states
from ironic.conductor import task_manager
from ironic.drivers import base
from ironic.drivers.modules.drac import client as drac_client
from ironic.drivers.modules.drac import common as drac_common
from ironic.drivers.modules.drac import resource_uris
from ironic.openstack.common import log as logging

pywsman = importutils.try_import('pywsman')

LOG = logging.getLogger(__name__)

POWER_STATES = {
    '2': states.POWER_ON,
    '3': states.POWER_OFF,
    '11': states.REBOOT,
}

REVERSE_POWER_STATES = dict((v, k) for (k, v) in POWER_STATES.items())


def _get_power_state(node):
    """Returns the current power state of the node

    :param node: The node.
    :returns: power state, one of :mod: `ironic.common.states`.
    :raises: DracClientError if the client received unexpected response.
    :raises: InvalidParameterValue if required DRAC credentials are missing.
    """

    client = drac_client.get_wsman_client(node)
    filter_query = ('select EnabledState,ElementName from DCIM_ComputerSystem '
                    'where Name="srv:system"')
    try:
        doc = client.wsman_enumerate(resource_uris.DCIM_ComputerSystem,
                                     filter_query=filter_query)
    except exception.DracClientError as exc:
        with excutils.save_and_reraise_exception():
            LOG.error(_LE('DRAC driver failed to get power state for node '
                          '%(node_uuid)s. Reason: %(error)s.'),
                      {'node_uuid': node.uuid, 'error': exc})

    enabled_state = drac_common.find_xml(doc, 'EnabledState',
                                         resource_uris.DCIM_ComputerSystem)
    return POWER_STATES[enabled_state.text]


def _set_power_state(node, target_state):
    """Turns the server power on/off or do a reboot.

    :param node: an ironic node object.
    :param target_state: target state of the node.
    :raises: DracClientError if the client received unexpected response.
    :raises: InvalidParameterValue if an invalid power state was specified.
    """

    client = drac_client.get_wsman_client(node)
    selectors = {'CreationClassName': 'DCIM_ComputerSystem',
                 'Name': 'srv:system'}
    properties = {'RequestedState': REVERSE_POWER_STATES[target_state]}

    try:
        client.wsman_invoke(resource_uris.DCIM_ComputerSystem,
                            'RequestStateChange', selectors, properties)
    except exception.DracRequestFailed as exc:
        with excutils.save_and_reraise_exception():
            LOG.error(_LE('DRAC driver failed to set power state for node '
                          '%(node_uuid)s to %(target_power_state)s. '
                          'Reason: %(error)s.'),
                      {'node_uuid': node.uuid,
                       'target_power_state': target_state,
                       'error': exc})


class DracPower(base.PowerInterface):
    """Interface for power-related actions."""

    def get_properties(self):
        return drac_common.COMMON_PROPERTIES

    def validate(self, task):
        """Validate the driver-specific Node power info.

        This method validates whether the 'driver_info' property of the
        supplied node contains the required information for this driver to
        manage the power state of the node.

        :param task: a TaskManager instance containing the node to act on.
        :raises: InvalidParameterValue if required driver_info attribute
                 is missing or invalid on the node.
        """
        return drac_common.parse_driver_info(task.node)

    def get_power_state(self, task):
        """Return the power state of the task's node.

        :param task: a TaskManager instance containing the node to act on.
        :returns: a power state. One of :mod:`ironic.common.states`.
        :raises: DracClientError if the client received unexpected response.
        """
        return _get_power_state(task.node)

    @task_manager.require_exclusive_lock
    def set_power_state(self, task, power_state):
        """Set the power state of the task's node.

        :param task: a TaskManager instance containing the node to act on.
        :param power_state: Any power state from :mod:`ironic.common.states`.
        :raises: DracClientError if the client received unexpected response.
        :raises: DracOperationFailed if the client received response with an
                 error message.
        :raises: DracUnexpectedReturnValue if the client received a response
                 with unexpected return value.

        """
        _set_power_state(task.node, power_state)

    @task_manager.require_exclusive_lock
    def reboot(self, task):
        """Perform a hard reboot of the task's node.

        :param task: a TaskManager instance containing the node to act on.
        :raises: DracClientError if the client received unexpected response.
        :raises: DracOperationFailed if the client received response with an
                 error message.
        :raises: DracUnexpectedReturnValue if the client received a response
                 with unexpected return value.
        """

        current_power_state = _get_power_state(task.node)
        if current_power_state == states.POWER_ON:
            target_power_state = states.REBOOT
        else:
            target_power_state = states.POWER_ON

        _set_power_state(task.node, target_power_state)
