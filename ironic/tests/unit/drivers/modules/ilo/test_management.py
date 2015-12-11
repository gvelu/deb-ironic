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
from oslo_utils import importutils

from ironic.common import boot_devices
from ironic.common import exception
from ironic.conductor import task_manager
from ironic.drivers.modules.ilo import common as ilo_common
from ironic.drivers.modules.ilo import management as ilo_management
from ironic.drivers.modules import ipmitool
from ironic.tests.unit.conductor import mgr_utils
from ironic.tests.unit.db import base as db_base
from ironic.tests.unit.db import utils as db_utils
from ironic.tests.unit.objects import utils as obj_utils

ilo_error = importutils.try_import('proliantutils.exception')

INFO_DICT = db_utils.get_test_ilo_info()
CONF = cfg.CONF


class IloManagementTestCase(db_base.DbTestCase):

    def setUp(self):
        super(IloManagementTestCase, self).setUp()
        mgr_utils.mock_the_extension_manager(driver="fake_ilo")
        self.node = obj_utils.create_test_node(
            self.context, driver='fake_ilo', driver_info=INFO_DICT)

    def test_get_properties(self):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            expected = ilo_management.MANAGEMENT_PROPERTIES
            self.assertEqual(expected,
                             task.driver.management.get_properties())

    @mock.patch.object(ilo_common, 'parse_driver_info', spec_set=True,
                       autospec=True)
    def test_validate(self, driver_info_mock):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.validate(task)
            driver_info_mock.assert_called_once_with(task.node)

    def test_get_supported_boot_devices(self):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            expected = [boot_devices.PXE, boot_devices.DISK,
                        boot_devices.CDROM]
            self.assertEqual(
                sorted(expected),
                sorted(task.driver.management.
                       get_supported_boot_devices(task)))

    @mock.patch.object(ilo_common, 'get_ilo_object', spec_set=True,
                       autospec=True)
    def test_get_boot_device_next_boot(self, get_ilo_object_mock):
        ilo_object_mock = get_ilo_object_mock.return_value
        ilo_object_mock.get_one_time_boot.return_value = 'CDROM'
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            expected_device = boot_devices.CDROM
            expected_response = {'boot_device': expected_device,
                                 'persistent': False}
            self.assertEqual(expected_response,
                             task.driver.management.get_boot_device(task))
            ilo_object_mock.get_one_time_boot.assert_called_once_with()

    @mock.patch.object(ilo_common, 'get_ilo_object', spec_set=True,
                       autospec=True)
    def test_get_boot_device_persistent(self, get_ilo_object_mock):
        ilo_mock = get_ilo_object_mock.return_value
        ilo_mock.get_one_time_boot.return_value = 'Normal'
        ilo_mock.get_persistent_boot_device.return_value = 'NETWORK'

        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            expected_device = boot_devices.PXE
            expected_response = {'boot_device': expected_device,
                                 'persistent': True}
            self.assertEqual(expected_response,
                             task.driver.management.get_boot_device(task))
            ilo_mock.get_one_time_boot.assert_called_once_with()
            ilo_mock.get_persistent_boot_device.assert_called_once_with()

    @mock.patch.object(ilo_common, 'get_ilo_object', spec_set=True,
                       autospec=True)
    def test_get_boot_device_fail(self, get_ilo_object_mock):
        ilo_mock_object = get_ilo_object_mock.return_value
        exc = ilo_error.IloError('error')
        ilo_mock_object.get_one_time_boot.side_effect = exc

        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            self.assertRaises(exception.IloOperationError,
                              task.driver.management.get_boot_device,
                              task)
        ilo_mock_object.get_one_time_boot.assert_called_once_with()

    @mock.patch.object(ilo_common, 'get_ilo_object', spec_set=True,
                       autospec=True)
    def test_get_boot_device_persistent_fail(self, get_ilo_object_mock):
        ilo_mock_object = get_ilo_object_mock.return_value
        ilo_mock_object.get_one_time_boot.return_value = 'Normal'
        exc = ilo_error.IloError('error')
        ilo_mock_object.get_persistent_boot_device.side_effect = exc

        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            self.assertRaises(exception.IloOperationError,
                              task.driver.management.get_boot_device,
                              task)
        ilo_mock_object.get_one_time_boot.assert_called_once_with()
        ilo_mock_object.get_persistent_boot_device.assert_called_once_with()

    @mock.patch.object(ilo_common, 'get_ilo_object', spec_set=True,
                       autospec=True)
    def test_set_boot_device_ok(self, get_ilo_object_mock):
        ilo_object_mock = get_ilo_object_mock.return_value
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.set_boot_device(task, boot_devices.CDROM,
                                                   False)
            get_ilo_object_mock.assert_called_once_with(task.node)
            ilo_object_mock.set_one_time_boot.assert_called_once_with('CDROM')

    @mock.patch.object(ilo_common, 'get_ilo_object', spec_set=True,
                       autospec=True)
    def test_set_boot_device_persistent_true(self, get_ilo_object_mock):
        ilo_mock = get_ilo_object_mock.return_value
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.set_boot_device(task, boot_devices.PXE,
                                                   True)
            get_ilo_object_mock.assert_called_once_with(task.node)
            ilo_mock.update_persistent_boot.assert_called_once_with(
                ['NETWORK'])

    @mock.patch.object(ilo_common, 'get_ilo_object', spec_set=True,
                       autospec=True)
    def test_set_boot_device_fail(self, get_ilo_object_mock):
        ilo_mock_object = get_ilo_object_mock.return_value
        exc = ilo_error.IloError('error')
        ilo_mock_object.set_one_time_boot.side_effect = exc

        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            self.assertRaises(exception.IloOperationError,
                              task.driver.management.set_boot_device,
                              task, boot_devices.PXE)
        ilo_mock_object.set_one_time_boot.assert_called_once_with('NETWORK')

    @mock.patch.object(ilo_common, 'get_ilo_object', spec_set=True,
                       autospec=True)
    def test_set_boot_device_persistent_fail(self, get_ilo_object_mock):
        ilo_mock_object = get_ilo_object_mock.return_value
        exc = ilo_error.IloError('error')
        ilo_mock_object.update_persistent_boot.side_effect = exc

        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            self.assertRaises(exception.IloOperationError,
                              task.driver.management.set_boot_device,
                              task, boot_devices.PXE, True)
        ilo_mock_object.update_persistent_boot.assert_called_once_with(
            ['NETWORK'])

    def test_set_boot_device_invalid_device(self):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            self.assertRaises(exception.InvalidParameterValue,
                              task.driver.management.set_boot_device,
                              task, 'fake-device')

    @mock.patch.object(ilo_common, 'update_ipmi_properties', spec_set=True,
                       autospec=True)
    @mock.patch.object(ipmitool.IPMIManagement, 'get_sensors_data',
                       spec_set=True, autospec=True)
    def test_get_sensor_data(self, get_sensors_data_mock, update_ipmi_mock):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.get_sensors_data(task)
            update_ipmi_mock.assert_called_once_with(task)
            get_sensors_data_mock.assert_called_once_with(mock.ANY, task)

    @mock.patch.object(ilo_common, 'get_ilo_object', spec_set=True,
                       autospec=True)
    def test__execute_ilo_clean_step_ok(self, get_ilo_object_mock):
        ilo_mock = get_ilo_object_mock.return_value
        clean_step_mock = getattr(ilo_mock, 'fake-step')
        ilo_management._execute_ilo_clean_step(
            self.node, 'fake-step', 'args', kwarg='kwarg')
        clean_step_mock.assert_called_once_with('args', kwarg='kwarg')

    @mock.patch.object(ilo_management, 'LOG', spec_set=True, autospec=True)
    @mock.patch.object(ilo_common, 'get_ilo_object', spec_set=True,
                       autospec=True)
    def test__execute_ilo_clean_step_not_supported(self, get_ilo_object_mock,
                                                   log_mock):
        ilo_mock = get_ilo_object_mock.return_value
        exc = ilo_error.IloCommandNotSupportedError("error")
        clean_step_mock = getattr(ilo_mock, 'fake-step')
        clean_step_mock.side_effect = exc
        ilo_management._execute_ilo_clean_step(
            self.node, 'fake-step', 'args', kwarg='kwarg')
        clean_step_mock.assert_called_once_with('args', kwarg='kwarg')
        self.assertTrue(log_mock.warning.called)

    @mock.patch.object(ilo_common, 'get_ilo_object', spec_set=True,
                       autospec=True)
    def test__execute_ilo_clean_step_fail(self, get_ilo_object_mock):
        ilo_mock = get_ilo_object_mock.return_value
        exc = ilo_error.IloError("error")
        clean_step_mock = getattr(ilo_mock, 'fake-step')
        clean_step_mock.side_effect = exc
        self.assertRaises(exception.NodeCleaningFailure,
                          ilo_management._execute_ilo_clean_step,
                          self.node, 'fake-step', 'args', kwarg='kwarg')
        clean_step_mock.assert_called_once_with('args', kwarg='kwarg')

    @mock.patch.object(ilo_management, '_execute_ilo_clean_step',
                       spec_set=True, autospec=True)
    def test_reset_ilo(self, clean_step_mock):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.reset_ilo(task)
            clean_step_mock.assert_called_once_with(task.node, 'reset_ilo')

    @mock.patch.object(ilo_management, '_execute_ilo_clean_step',
                       spec_set=True, autospec=True)
    def test_reset_ilo_credential_ok(self, clean_step_mock):
        info = self.node.driver_info
        info['ilo_change_password'] = "fake-password"
        self.node.driver_info = info
        self.node.save()
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.reset_ilo_credential(task)
            clean_step_mock.assert_called_once_with(
                task.node, 'reset_ilo_credential', 'fake-password')
            self.assertIsNone(
                task.node.driver_info.get('ilo_change_password'))
            self.assertEqual(task.node.driver_info['ilo_password'],
                             'fake-password')

    @mock.patch.object(ilo_management, 'LOG', spec_set=True, autospec=True)
    @mock.patch.object(ilo_management, '_execute_ilo_clean_step',
                       spec_set=True, autospec=True)
    def test_reset_ilo_credential_no_password(self, clean_step_mock,
                                              log_mock):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.reset_ilo_credential(task)
            self.assertFalse(clean_step_mock.called)
            self.assertTrue(log_mock.info.called)

    @mock.patch.object(ilo_management, '_execute_ilo_clean_step',
                       spec_set=True, autospec=True)
    def test_reset_bios_to_default(self, clean_step_mock):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.reset_bios_to_default(task)
            clean_step_mock.assert_called_once_with(task.node,
                                                    'reset_bios_to_default')

    @mock.patch.object(ilo_management, '_execute_ilo_clean_step',
                       spec_set=True, autospec=True)
    def test_reset_secure_boot_keys_to_default(self, clean_step_mock):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.reset_secure_boot_keys_to_default(task)
            clean_step_mock.assert_called_once_with(task.node,
                                                    'reset_secure_boot_keys')

    @mock.patch.object(ilo_management, '_execute_ilo_clean_step',
                       spec_set=True, autospec=True)
    def test_clear_secure_boot_keys(self, clean_step_mock):
        with task_manager.acquire(self.context, self.node.uuid,
                                  shared=False) as task:
            task.driver.management.clear_secure_boot_keys(task)
            clean_step_mock.assert_called_once_with(task.node,
                                                    'clear_secure_boot_keys')
