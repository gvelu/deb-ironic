# Copyright 2015 Red Hat, Inc.
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

import ast
import six

from oslo_versionedobjects import fields as object_fields

from ironic.common import utils


class _Callable(object):
    """Helper class to make this work like old-style fields.

    This class makes the object able to be called like a function,
    which emulates the old interface that objects are expecting. This
    should be removed once objects/base.py is updated to stop using the
    old interface for the fields.

    """
    def __call__(self, value):
        return self.coerce(None, None, value)


class IntegerField(object_fields.IntegerField, _Callable):
    pass


class UUIDField(object_fields.UUIDField, _Callable):
    pass


class StringField(object_fields.StringField, _Callable):
    pass


class DateTimeField(object_fields.DateTimeField, _Callable):
    pass


class BooleanField(object_fields.BooleanField, _Callable):
    pass


class ListOfStringsField(object_fields.ListOfStringsField, _Callable):
    pass


class FlexibleDict(object_fields.FieldType, _Callable):
    @staticmethod
    def coerce(obj, attr, value):
        if isinstance(value, six.string_types):
            value = ast.literal_eval(value)
        return dict(value)


class FlexibleDictField(object_fields.AutoTypedField, _Callable):
    AUTO_TYPE = FlexibleDict()

    # TODO(lucasagomes): In our code we've always translated None to {},
    # this method makes this field to work like this. But probably won't
    # be accepted as-is in the oslo_versionedobjects library
    def _null(self, obj, attr):
        if self.nullable:
            return {}
        super(FlexibleDictField, self)._null(obj, attr)


class MACAddress(object_fields.FieldType):
    @staticmethod
    def coerce(obj, attr, value):
        return utils.validate_and_normalize_mac(value)


class MACAddressField(object_fields.AutoTypedField, _Callable):
    AUTO_TYPE = MACAddress()
