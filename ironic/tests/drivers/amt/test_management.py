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
Test class for AMT ManagementInterface
"""

import mock
from oslo_config import cfg

from ironic.common import boot_devices
from ironic.common import exception
from ironic.conductor import task_manager
from ironic.drivers.modules.amt import common as amt_common
from ironic.drivers.modules.amt import management as amt_mgmt
from ironic.drivers.modules.amt import resource_uris
from ironic.tests.conductor import utils as mgr_utils
from ironic.tests.db import base as db_base
from ironic.tests.db import utils as db_utils
from ironic.tests.drivers.drac import utils as test_utils
from ironic.tests.objects import utils as obj_utils

INFO_DICT = db_utils.get_test_amt_info()
CONF = cfg.CONF


@mock.patch.object(amt_common, 'pywsman')
class AMTManagementInteralMethodsTestCase(db_base.DbTestCase):

    def setUp(self):
        super(AMTManagementInteralMethodsTestCase, self).setUp()
        mgr_utils.mock_the_extension_manager(driver='fake_amt')
        self.node = obj_utils.create_test_node(self.context,
                                               driver='fake_amt',
                                               driver_info=INFO_DICT)

    def test__set_boot_device_order(self, mock_client_pywsman):
        namespace = resource_uris.CIM_BootConfigSetting
        device = boot_devices.PXE
        result_xml = test_utils.build_soap_xml([{'ReturnValue': '0'}],
                                                namespace)
        mock_xml = test_utils.mock_wsman_root(result_xml)
        mock_pywsman = mock_client_pywsman.Client.return_value
        mock_pywsman.invoke.return_value = mock_xml

        amt_mgmt._set_boot_device_order(self.node, device)

        mock_pywsman.invoke.assert_called_once_with(mock.ANY,
            namespace, 'ChangeBootOrder')

    def test__set_boot_device_order_fail(self, mock_client_pywsman):
        namespace = resource_uris.CIM_BootConfigSetting
        device = boot_devices.PXE
        result_xml = test_utils.build_soap_xml([{'ReturnValue': '2'}],
                                               namespace)
        mock_xml = test_utils.mock_wsman_root(result_xml)
        mock_pywsman = mock_client_pywsman.Client.return_value
        mock_pywsman.invoke.return_value = mock_xml

        self.assertRaises(exception.AMTFailure,
                          amt_mgmt._set_boot_device_order, self.node, device)
        mock_pywsman.invoke.assert_called_once_with(mock.ANY,
            namespace, 'ChangeBootOrder')

        mock_pywsman = mock_client_pywsman.Client.return_value
        mock_pywsman.invoke.return_value = None

        self.assertRaises(exception.AMTConnectFailure,
                          amt_mgmt._set_boot_device_order, self.node, device)

    def test__enable_boot_config(self, mock_client_pywsman):
        namespace = resource_uris.CIM_BootService
        result_xml = test_utils.build_soap_xml([{'ReturnValue': '0'}],
                                               namespace)
        mock_xml = test_utils.mock_wsman_root(result_xml)
        mock_pywsman = mock_client_pywsman.Client.return_value
        mock_pywsman.invoke.return_value = mock_xml

        amt_mgmt._enable_boot_config(self.node)

        mock_pywsman.invoke.assert_called_once_with(mock.ANY,
            namespace, 'SetBootConfigRole')

    def test__enable_boot_config_fail(self, mock_client_pywsman):
        namespace = resource_uris.CIM_BootService
        result_xml = test_utils.build_soap_xml([{'ReturnValue': '2'}],
                                               namespace)
        mock_xml = test_utils.mock_wsman_root(result_xml)
        mock_pywsman = mock_client_pywsman.Client.return_value
        mock_pywsman.invoke.return_value = mock_xml

        self.assertRaises(exception.AMTFailure,
                          amt_mgmt._enable_boot_config, self.node)
        mock_pywsman.invoke.assert_called_once_with(mock.ANY,
            namespace, 'SetBootConfigRole')

        mock_pywsman = mock_client_pywsman.Client.return_value
        mock_pywsman.invoke.return_value = None

        self.assertRaises(exception.AMTConnectFailure,
                          amt_mgmt._enable_boot_config, self.node)


class AMTManagementTestCase(db_base.DbTestCase):

    def setUp(self):
        super(AMTManagementTestCase, self).setUp()
        mgr_utils.mock_the_extension_manager(driver='fake_amt')
        self.info = INFO_DICT
        self.node = obj_utils.create_test_node(self.context,
                                               driver='fake_amt',
                                               driver_info=self.info)

    def test_get_properties(self):
        expected = amt_common.COMMON_PROPERTIES
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=True) as task:
            self.assertEqual(expected, task.driver.get_properties())

    @mock.patch.object(amt_common, 'parse_driver_info')
    def test_validate(self, mock_drvinfo):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=True) as task:
            task.driver.management.validate(task)
            mock_drvinfo.assert_called_once_with(task.node)

    @mock.patch.object(amt_common, 'parse_driver_info')
    def test_validate_fail(self, mock_drvinfo):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=True) as task:
            mock_drvinfo.side_effect = exception.InvalidParameterValue('x')
            self.assertRaises(exception.InvalidParameterValue,
                              task.driver.management.validate,
                              task)

    def test_get_supported_boot_devices(self):
        expected = [boot_devices.PXE, boot_devices.DISK, boot_devices.CDROM]
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=True) as task:
            self.assertEqual(
                sorted(expected),
                sorted(task.driver.management.get_supported_boot_devices()))

    def test_set_boot_device_one_time(self):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.set_boot_device(task, 'pxe')
            self.assertEqual('pxe',
                             task.node.driver_internal_info["amt_boot_device"])
            self.assertFalse(
                task.node.driver_internal_info["amt_boot_persistent"])

    def test_set_boot_device_persistent(self):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.set_boot_device(task, 'pxe',
                                                   persistent=True)
            self.assertEqual('pxe',
                             task.node.driver_internal_info["amt_boot_device"])
            self.assertTrue(
                task.node.driver_internal_info["amt_boot_persistent"])

    def test_set_boot_device_fail(self):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            self.assertRaises(exception.InvalidParameterValue,
                              task.driver.management.set_boot_device,
                              task, 'fake-device')

    @mock.patch.object(amt_mgmt, '_enable_boot_config')
    @mock.patch.object(amt_mgmt, '_set_boot_device_order')
    def test_ensure_next_boot_device_one_time(self, mock_sbdo, mock_ebc):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=True) as task:
            device = boot_devices.PXE
            task.node.driver_internal_info['amt_boot_device'] = 'pxe'
            task.driver.management.ensure_next_boot_device(task.node, device)
            self.assertEqual('disk',
                             task.node.driver_internal_info["amt_boot_device"])
            self.assertTrue(
                task.node.driver_internal_info["amt_boot_persistent"])
            mock_sbdo.assert_called_once_with(task.node, device)
            mock_ebc.assert_called_once_with(task.node)

    @mock.patch.object(amt_mgmt, '_enable_boot_config')
    @mock.patch.object(amt_mgmt, '_set_boot_device_order')
    def test_ensure_next_boot_device_persistent(self, mock_sbdo, mock_ebc):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=True) as task:
            device = boot_devices.PXE
            task.node.driver_internal_info['amt_boot_device'] = 'pxe'
            task.node.driver_internal_info['amt_boot_persistent'] = True
            task.driver.management.ensure_next_boot_device(task.node, device)
            self.assertEqual('pxe',
                             task.node.driver_internal_info["amt_boot_device"])
            self.assertTrue(
                task.node.driver_internal_info["amt_boot_persistent"])
            mock_sbdo.assert_called_once_with(task.node, device)
            mock_ebc.assert_called_once_with(task.node)

    def test_get_boot_device(self):
        expected = {'boot_device': boot_devices.DISK, 'persistent': True}
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=True) as task:
            self.assertEqual(expected,
                             task.driver.management.get_boot_device(task))

    def test_get_sensor_data(self):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=True) as task:
            self.assertRaises(NotImplementedError,
                              task.driver.management.get_sensors_data,
                              task)
