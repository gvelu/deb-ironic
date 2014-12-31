.. _vendor-passthru:

==============
Vendor Methods
==============

This document is a quick tutorial on writing vendor specific methods to
a driver.

The first thing to note is that the Ironic API supports two vendor
endpoints: A driver vendor passthru and a node vendor passthru.

* The driver vendor passthru allows drivers to expose a custom top-level
  functionality which is not specific to a Node. For example, let's say
  the driver `pxe_ipmitool` exposed a method called `authentication_types`
  that would return what are the authentication types supported. It could
  be accessed via the Ironic API like:

::

  GET http://<address>:<port>/v1/drives/pxe_ipmitool/vendor_passthru/authentication_types

* The node vendor passthru allows drivers to expose custom functionality
  on per-node basis. For example the same driver `pxe_ipmitool` exposing a
  method called `send_raw` that would send raw bytes to the BMC, the method
  also receives a parameter called `raw_bytes` which the value would be
  the bytes to be sent. It could be accessed via the Ironic API like:

::

  POST {'raw_bytes': '0x01 0x02'} http://<address>:<port>/v1/nodes/<node UUID>/vendor_passthru/send_raw


Writing Vendor Methods
======================

Writing a custom vendor method in Ironic should be simple. The first thing
to do is write a class inheriting from the `VendorInterface`_ class:

.. code-block:: python

  class ExampleVendor(VendorInterface)

      def get_properties(self):
          return {}

      def validate(self, task, **kwargs):
          pass

The `get_properties` is a method that all driver interfaces have, it
should return a dictionary of <property>:<description> telling in the
description whether that property is required or optional so the node
can be manageable by that driver. For example, a required property for a
`ipmi` driver would be `ipmi_address` which is the IP address or hostname
of the node. We are returning an empty dictionary in our example to make
it simpler.

The `validate` method is responsible for validating the parameters passed
to the vendor methods. Ironic will not introspect into what is passed
to the drivers, it's up to the developers writing the vendor method to
validate that data.

Let's extend the `ExampleVendor` class to support two methods, the
`authentication_types` which will be exposed on the driver vendor
passthru endpoint; And the `send_raw` method that will be exposed on
the node vendor passthru endpoint:

.. code-block:: python

  class ExampleVendor(VendorInterface)

      def get_properties(self):
          return {}

      def validate(self, task, method, **kwargs):
          if method == 'send_raw':
              if 'raw_bytes' not in kwargs:
                  raise MissingParameterValue()

      @base.driver_passthru(['GET'], async=False)
      def authentication_types(self, context **kwargs):
          return {"types": ["NONE", "MD5", "MD2"]}

      @base.passthru(['POST'])
      def send_raw(self, task, **kwargs):
          raw_bytes = kwargs.get('raw_bytes')
          ...

That's it!

Writing a node or driver vendor passthru method is pretty much the
same, the only difference is how you decorate the methods and the first
parameter of the method (ignoring self). A method decorated with the
`@passthru` decorator should expect a Task object as first parameter and
a method decorated with the `@driver_passthru` decorator should expect
a Context object as first parameter.

Both decorators accepts the same parameters:

* http_methods: A list of what the HTTP methods supported by that vendor
  function. To know what HTTP method that function was invoked with, a
  `http_method` parameter will be present in the `kwargs`. Supported HTTP
  methods are *POST*, *PUT*, *GET* and *PATCH*.

* method: By default the method name is the name of the python function,
  if you want to use a different name this parameter is where this name
  can be set. For example:

.. code-block:: python

  @passthru(['PUT'], method="alternative_name")
  def name(self, task, **kwargs):
      ...

* description: A string containing a nice description about what that
  method is suppose to do. Defaults to "" (empty string).

.. _VendorInterface: ../api/ironic.drivers.base.html#ironic.drivers.base.VendorInterface

* async: A boolean value to determine whether this method should run
  asynchronously or synchronously. Defaults to True (Asynchronously).

.. WARNING::
   Please avoid having a synchronous method for slow/long-running
   operations **or** if the method does talk to a BMC; BMCs are flaky
   and very easy to break.
