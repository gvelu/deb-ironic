# Copyright 2014 Hewlett-Packard Development Company, L.P.
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


"""Test class for Management Interface used by iLO modules."""

import mock
from oslo_config import cfg

from ironic.common import exception
from ironic.common import states
from ironic.conductor import task_manager
from ironic.conductor import utils as conductor_utils
from ironic.db import api as dbapi
from ironic.drivers.modules.ilo import common as ilo_common
from ironic.drivers.modules.ilo import inspect as ilo_inspect
from ironic.drivers.modules.ilo import power as ilo_power
from ironic.tests.conductor import utils as mgr_utils
from ironic.tests.db import base as db_base
from ironic.tests.db import utils as db_utils
from ironic.tests.objects import utils as obj_utils


INFO_DICT = db_utils.get_test_ilo_info()
CONF = cfg.CONF


class IloInspectTestCase(db_base.DbTestCase):

    def setUp(self):
        super(IloInspectTestCase, self).setUp()
        mgr_utils.mock_the_extension_manager(driver="fake_ilo")
        self.node = obj_utils.create_test_node(self.context,
                driver='fake_ilo', driver_info=INFO_DICT)

    def test_get_properties(self):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            properties = ilo_common.REQUIRED_PROPERTIES.copy()
            self.assertEqual(properties,
                             task.driver.inspect.get_properties())

    @mock.patch.object(ilo_common, 'parse_driver_info')
    def test_validate(self, driver_info_mock):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.inspect.validate(task)
            driver_info_mock.assert_called_once_with(task.node)

    @mock.patch.object(ilo_inspect, '_get_capabilities')
    @mock.patch.object(ilo_inspect, '_create_ports_if_not_exist')
    @mock.patch.object(ilo_inspect, '_get_essential_properties')
    @mock.patch.object(ilo_power.IloPower, 'get_power_state')
    @mock.patch.object(ilo_common, 'get_ilo_object')
    def test_inspect_essential_ok(self, get_ilo_object_mock,
                                  power_mock,
                                  get_essential_mock,
                                  create_port_mock,
                                  get_capabilities_mock):
        ilo_object_mock = get_ilo_object_mock.return_value
        properties = {'memory_mb': '512', 'local_gb': '10',
                      'cpus': '1', 'cpu_arch': 'x86_64'}
        macs = {'Port 1': 'aa:aa:aa:aa:aa:aa', 'Port 2': 'bb:bb:bb:bb:bb:bb'}
        capabilities = ''
        result = {'properties': properties, 'macs': macs}
        get_essential_mock.return_value = result
        get_capabilities_mock.return_value = capabilities
        power_mock.return_value = states.POWER_ON
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.inspect.inspect_hardware(task)
            self.assertEqual(properties, task.node.properties)
            power_mock.assert_called_once_with(task)
            get_essential_mock.assert_called_once_with(task.node,
                                                       ilo_object_mock)
            get_capabilities_mock.assert_called_once_with(task.node,
                                                          ilo_object_mock)
            create_port_mock.assert_called_once_with(task.node, macs)

    @mock.patch.object(ilo_inspect, '_get_capabilities')
    @mock.patch.object(ilo_inspect, '_create_ports_if_not_exist')
    @mock.patch.object(ilo_inspect, '_get_essential_properties')
    @mock.patch.object(conductor_utils, 'node_power_action')
    @mock.patch.object(ilo_power.IloPower, 'get_power_state')
    @mock.patch.object(ilo_common, 'get_ilo_object')
    def test_inspect_essential_ok_power_off(self, get_ilo_object_mock,
                                            power_mock,
                                            set_power_mock,
                                            get_essential_mock,
                                            create_port_mock,
                                            get_capabilities_mock):
        ilo_object_mock = get_ilo_object_mock.return_value
        properties = {'memory_mb': '512', 'local_gb': '10',
                      'cpus': '1', 'cpu_arch': 'x86_64'}
        macs = {'Port 1': 'aa:aa:aa:aa:aa:aa', 'Port 2': 'bb:bb:bb:bb:bb:bb'}
        capabilities = ''
        result = {'properties': properties, 'macs': macs}
        get_essential_mock.return_value = result
        get_capabilities_mock.return_value = capabilities
        power_mock.return_value = states.POWER_OFF
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.inspect.inspect_hardware(task)
            self.assertEqual(properties, task.node.properties)
            power_mock.assert_called_once_with(task)
            set_power_mock.assert_any_call(task, states.POWER_ON)
            get_essential_mock.assert_called_once_with(task.node,
                                                       ilo_object_mock)
            get_capabilities_mock.assert_called_once_with(task.node,
                                                          ilo_object_mock)
            create_port_mock.assert_called_once_with(task.node, macs)

    @mock.patch.object(ilo_inspect, '_get_capabilities')
    @mock.patch.object(ilo_inspect, '_create_ports_if_not_exist')
    @mock.patch.object(ilo_inspect, '_get_essential_properties')
    @mock.patch.object(ilo_power.IloPower, 'get_power_state')
    @mock.patch.object(ilo_common, 'get_ilo_object')
    def test_inspect_essential_capabilities_ok(self, get_ilo_object_mock,
                                               power_mock,
                                               get_essential_mock,
                                               create_port_mock,
                                               get_capabilities_mock):
        ilo_object_mock = get_ilo_object_mock.return_value
        properties = {'memory_mb': '512', 'local_gb': '10',
                      'cpus': '1', 'cpu_arch': 'x86_64'}
        macs = {'Port 1': 'aa:aa:aa:aa:aa:aa', 'Port 2': 'bb:bb:bb:bb:bb:bb'}
        capability_str = 'BootMode:uefi'
        capabilities = {'BootMode': 'uefi'}
        result = {'properties': properties, 'macs': macs}
        get_essential_mock.return_value = result
        get_capabilities_mock.return_value = capabilities
        power_mock.return_value = states.POWER_ON
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.inspect.inspect_hardware(task)
            expected_properties = {'memory_mb': '512', 'local_gb': '10',
                                   'cpus': '1', 'cpu_arch': 'x86_64',
                                   'capabilities': capability_str}
            self.assertEqual(expected_properties, task.node.properties)
            power_mock.assert_called_once_with(task)
            get_essential_mock.assert_called_once_with(task.node,
                                                       ilo_object_mock)
            get_capabilities_mock.assert_called_once_with(task.node,
                                                          ilo_object_mock)
            create_port_mock.assert_called_once_with(task.node, macs)

    @mock.patch.object(ilo_inspect, '_get_capabilities')
    @mock.patch.object(ilo_inspect, '_create_ports_if_not_exist')
    @mock.patch.object(ilo_inspect, '_get_essential_properties')
    @mock.patch.object(ilo_power.IloPower, 'get_power_state')
    @mock.patch.object(ilo_common, 'get_ilo_object')
    def test_inspect_essential_capabilities_exist_ok(self, get_ilo_object_mock,
                                                     power_mock,
                                                     get_essential_mock,
                                                     create_port_mock,
                                                     get_capabilities_mock):
        ilo_object_mock = get_ilo_object_mock.return_value
        properties = {'memory_mb': '512', 'local_gb': '10',
                      'cpus': '1', 'cpu_arch': 'x86_64',
                      'somekey': 'somevalue'}
        macs = {'Port 1': 'aa:aa:aa:aa:aa:aa', 'Port 2': 'bb:bb:bb:bb:bb:bb'}
        result = {'properties': properties, 'macs': macs}
        capabilities = {'BootMode': 'uefi'}
        get_essential_mock.return_value = result
        get_capabilities_mock.return_value = capabilities
        power_mock.return_value = states.POWER_ON
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.node.properties = {'capabilities': 'foo:bar'}
            expected_capabilities = ('BootMode:uefi,'
                                     'foo:bar')
            set1 = set(expected_capabilities.split(','))
            task.driver.inspect.inspect_hardware(task)
            end_capabilities = task.node.properties['capabilities']
            set2 = set(end_capabilities.split(','))
            self.assertEqual(set1, set2)
            expected_properties = {'memory_mb': '512', 'local_gb': '10',
                                   'cpus': '1', 'cpu_arch': 'x86_64',
                                   'capabilities': end_capabilities}
            power_mock.assert_called_once_with(task)
            self.assertEqual(task.node.properties, expected_properties)
            get_essential_mock.assert_called_once_with(task.node,
                                                       ilo_object_mock)
            get_capabilities_mock.assert_called_once_with(task.node,
                                                          ilo_object_mock)
            create_port_mock.assert_called_once_with(task.node, macs)


class TestInspectPrivateMethods(db_base.DbTestCase):

    def setUp(self):
        super(TestInspectPrivateMethods, self).setUp()
        mgr_utils.mock_the_extension_manager(driver="fake_ilo")
        self.node = obj_utils.create_test_node(self.context,
                driver='fake_ilo', driver_info=INFO_DICT)

    @mock.patch.object(ilo_inspect.LOG, 'info')
    @mock.patch.object(dbapi, 'get_instance')
    def test__create_ports_if_not_exist(self, instance_mock, log_mock):
        db_obj = instance_mock.return_value
        macs = {'Port 1': 'aa:aa:aa:aa:aa:aa', 'Port 2': 'bb:bb:bb:bb:bb:bb'}
        node_id = self.node.id
        port_dict1 = {'address': 'aa:aa:aa:aa:aa:aa', 'node_id': node_id}
        port_dict2 = {'address': 'bb:bb:bb:bb:bb:bb', 'node_id': node_id}
        ilo_inspect._create_ports_if_not_exist(self.node, macs)
        instance_mock.assert_called_once_with()
        self.assertTrue(log_mock.called)
        db_obj.create_port.assert_any_call(port_dict1)
        db_obj.create_port.assert_any_call(port_dict2)

    @mock.patch.object(ilo_inspect.LOG, 'warn')
    @mock.patch.object(dbapi, 'get_instance')
    def test__create_ports_if_not_exist_mac_exception(self,
                                                      instance_mock,
                                                      log_mock):
        dbapi_mock = instance_mock.return_value
        dbapi_mock.create_port.side_effect = exception.MACAlreadyExists('f')
        macs = {'Port 1': 'aa:aa:aa:aa:aa:aa', 'Port 2': 'bb:bb:bb:bb:bb:bb'}
        ilo_inspect._create_ports_if_not_exist(self.node, macs)
        instance_mock.assert_called_once_with()
        self.assertTrue(log_mock.called)

    def test__get_essential_properties_ok(self):
        ilo_mock = mock.MagicMock()
        properties = {'memory_mb': '512', 'local_gb': '10',
                      'cpus': '1', 'cpu_arch': 'x86_64'}
        macs = {'Port 1': 'aa:aa:aa:aa:aa:aa', 'Port 2': 'bb:bb:bb:bb:bb:bb'}
        result = {'properties': properties, 'macs': macs}
        ilo_mock.get_essential_properties.return_value = result
        actual_result = ilo_inspect._get_essential_properties(self.node,
                                                              ilo_mock)
        self.assertEqual(result, actual_result)

    def test__get_essential_properties_fail(self):
        ilo_mock = mock.MagicMock()
        # Missing key: cpu_arch
        properties = {'memory_mb': '512', 'local_gb': '10',
                      'cpus': '1'}
        macs = {'Port 1': 'aa:aa:aa:aa:aa:aa', 'Port 2': 'bb:bb:bb:bb:bb:bb'}
        result = {'properties': properties, 'macs': macs}
        ilo_mock.get_essential_properties.return_value = result
        result = self.assertRaises(exception.HardwareInspectionFailure,
                                   ilo_inspect._get_essential_properties,
                                   self.node,
                                   ilo_mock)
        self.assertEqual(
            result.format_message(),
            ("Failed to inspect hardware. Reason: Server didn't return the "
             "key(s): cpu_arch"))

    def test__get_essential_properties_fail_invalid_format(self):
        ilo_mock = mock.MagicMock()
        # Not a dict
        properties = ['memory_mb', '512', 'local_gb', '10',
                      'cpus', '1']
        macs = ['aa:aa:aa:aa:aa:aa', 'bb:bb:bb:bb:bb:bb']
        capabilities = ''
        result = {'properties': properties, 'macs': macs}
        ilo_mock.get_essential_properties.return_value = result
        ilo_mock.get_additional_capabilities.return_value = capabilities
        self.assertRaises(exception.HardwareInspectionFailure,
                          ilo_inspect._get_essential_properties,
                          self.node, ilo_mock)

    def test__get_essential_properties_fail_mac_invalid_format(self):
        ilo_mock = mock.MagicMock()
        properties = {'memory_mb': '512', 'local_gb': '10',
                      'cpus': '1', 'cpu_arch': 'x86_64'}
        # Not a dict
        macs = 'aa:aa:aa:aa:aa:aa'
        result = {'properties': properties, 'macs': macs}
        ilo_mock.get_essential_properties.return_value = result
        self.assertRaises(exception.HardwareInspectionFailure,
                          ilo_inspect._get_essential_properties,
                          self.node, ilo_mock)

    def test__get_essential_properties_hardware_port_empty(self):
        ilo_mock = mock.MagicMock()
        properties = {'memory_mb': '512', 'local_gb': '10',
                      'cpus': '1', 'cpu_arch': 'x86_64'}
        # Not a dictionary
        macs = None
        result = {'properties': properties, 'macs': macs}
        capabilities = ''
        ilo_mock.get_essential_properties.return_value = result
        ilo_mock.get_additional_capabilities.return_value = capabilities
        self.assertRaises(exception.HardwareInspectionFailure,
                          ilo_inspect._get_essential_properties,
                          self.node, ilo_mock)

    def test__get_essential_properties_hardware_port_not_dict(self):
        ilo_mock = mock.MagicMock()
        properties = {'memory_mb': '512', 'local_gb': '10',
                      'cpus': '1', 'cpu_arch': 'x86_64'}
        # Not a dict
        macs = 'aa:bb:cc:dd:ee:ff'
        result = {'properties': properties, 'macs': macs}
        ilo_mock.get_essential_properties.return_value = result
        result = self.assertRaises(
            exception.HardwareInspectionFailure,
            ilo_inspect._get_essential_properties, self.node, ilo_mock)

    @mock.patch.object(ilo_inspect, '_update_capabilities')
    def test__get_capabilities_ok(self, capability_mock):
        ilo_mock = mock.MagicMock()
        capabilities = {'ilo_firmware_version': 'xyz'}
        ilo_mock.get_server_capabilities.return_value = capabilities
        cap = ilo_inspect._get_capabilities(self.node, ilo_mock)
        self.assertEqual(cap, capabilities)

    def test__validate_ok(self):
        properties = {'memory_mb': '512', 'local_gb': '10',
                      'cpus': '2', 'cpu_arch': 'x86_arch'}
        macs = {'Port 1': 'aa:aa:aa:aa:aa:aa'}
        data = {'properties': properties, 'macs': macs}
        valid_keys = set(ilo_inspect.ESSENTIAL_PROPERTIES_KEYS)
        ilo_inspect._validate(self.node, data)
        self.assertEqual(sorted(set(properties)), sorted(valid_keys))

    def test__validate_essential_keys_fail_missing_key(self):
        properties = {'memory_mb': '512', 'local_gb': '10',
                      'cpus': '1'}
        macs = {'Port 1': 'aa:aa:aa:aa:aa:aa'}
        data = {'properties': properties, 'macs': macs}
        self.assertRaises(exception.HardwareInspectionFailure,
                          ilo_inspect._validate, self.node, data)

    def test__update_capabilities(self):
        capabilities = {'ilo_firmware_version': 'xyz'}
        cap_string = 'ilo_firmware_version:xyz'
        cap_returned = ilo_inspect._update_capabilities(self.node,
                                                        capabilities)
        self.assertEqual(cap_string, cap_returned)
        self.assertIsInstance(cap_returned, str)

    def test__update_capabilities_multiple_keys(self):
        capabilities = {'ilo_firmware_version': 'xyz',
                        'foo': 'bar', 'somekey': 'value'}
        cap_string = 'ilo_firmware_version:xyz,foo:bar,somekey:value'
        cap_returned = ilo_inspect._update_capabilities(self.node,
                                                        capabilities)
        set1 = set(cap_string.split(','))
        set2 = set(cap_returned.split(','))
        self.assertEqual(set1, set2)
        self.assertIsInstance(cap_returned, str)

    def test__update_capabilities_invalid_capabilities(self):
        capabilities = 'ilo_firmware_version'
        self.assertRaises(exception.HardwareInspectionFailure,
                          ilo_inspect._update_capabilities,
                          self.node, capabilities)

    def test__update_capabilities_capabilities_not_dict(self):
        capabilities = ['ilo_firmware_version:xyz', 'foo:bar']
        self.assertRaises(exception.HardwareInspectionFailure,
                          ilo_inspect._update_capabilities,
                          self.node, capabilities)

    def test__update_capabilities_add_to_existing_capabilities(self):
        node_capabilities = {'capabilities': 'foo:bar'}
        self.node.properties.update(node_capabilities)
        new_capabilities = {'BootMode': 'uefi'}
        expected_capabilities = 'BootMode:uefi,foo:bar'
        cap_returned = ilo_inspect._update_capabilities(self.node,
                                                        new_capabilities)
        set1 = set(expected_capabilities.split(','))
        set2 = set(cap_returned.split(','))
        self.assertEqual(set1, set2)
        self.assertIsInstance(cap_returned, str)

    def test__update_capabilities_replace_to_existing_capabilities(self):
        node_capabilities = {'capabilities': 'BootMode:uefi'}
        self.node.properties.update(node_capabilities)
        new_capabilities = {'BootMode': 'bios'}
        expected_capabilities = 'BootMode:bios'
        cap_returned = ilo_inspect._update_capabilities(self.node,
                                                        new_capabilities)
        set1 = set(expected_capabilities.split(','))
        set2 = set(cap_returned.split(','))
        self.assertEqual(set1, set2)
        self.assertIsInstance(cap_returned, str)
