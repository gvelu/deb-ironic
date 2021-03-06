.. _enrollment:

Enrollment
==========

After all the services have been properly configured, you should enroll your
hardware with the Bare Metal service, and confirm that the Compute service sees
the available hardware. The nodes will be visible to the Compute service once
they are in the ``available`` provision state.

.. note::
   After enrolling nodes with the Bare Metal service, the Compute service
   will not be immediately notified of the new resources. The Compute service's
   resource tracker syncs periodically, and so any changes made directly to the
   Bare Metal service's resources will become visible in the Compute service
   only after the next run of that periodic task.
   More information is in the :ref:`troubleshooting` section.

.. note::
   Any bare metal node that is visible to the Compute service may have a
   workload scheduled to it, if both the ``power`` and ``deploy`` interfaces
   pass the ``validate`` check.
   If you wish to exclude a node from the Compute service's scheduler, for
   instance so that you can perform maintenance on it, you can set the node to
   "maintenance" mode.
   For more information see the :ref:`maintenance_mode` section.

Choosing a driver
-----------------

When enrolling a node, the most important information to supply is *driver*.
This can be either a *classic driver* or a *hardware type* - see
:doc:`enabling-drivers` for the difference. The ``driver-list`` command can
be used to list all drivers (of both types) enabled on all hosts:

.. code-block:: console

    ironic driver-list
    +---------------------+-----------------------+
    | Supported driver(s) | Active host(s)        |
    +---------------------+-----------------------+
    | ipmi                | localhost.localdomain |
    | pxe_ipmitool        | localhost.localdomain |
    +---------------------+-----------------------+

Starting with API version 1.31 (and ``python-ironicclient`` 1.13), you can
also list only classic or only dynamic drivers:

.. code-block:: console

    ironic --ironic-api-version 1.31 driver-list -t dynamic
    +---------------------+-----------------------+
    | Supported driver(s) | Active host(s)        |
    +---------------------+-----------------------+
    | ipmi                | localhost.localdomain |
    +---------------------+-----------------------+

The specific driver to use should be picked based on actual hardware
capabilities and expected features. See `driver-specific documentation`_
for more hints on that.

Each driver has a list of *driver properties* that need to be specified via
the node's ``driver_info`` field, in order for the driver to operate on node.
This list consists of the properties of the hardware interfaces that the driver
uses. These driver properties are available with the ``driver-properties``
command:

.. code-block:: console

    $ ironic driver-properties pxe_ipmitool
    +----------------------+-------------------------------------------------------------------------------------------------------------+
    | Property             | Description                                                                                                 |
    +----------------------+-------------------------------------------------------------------------------------------------------------+
    | ipmi_address         | IP address or hostname of the node. Required.                                                               |
    | ipmi_password        | password. Optional.                                                                                         |
    | ipmi_username        | username; default is NULL user. Optional.                                                                   |
    | ...                  | ...                                                                                                         |
    | deploy_kernel        | UUID (from Glance) of the deployment kernel. Required.                                                      |
    | deploy_ramdisk       | UUID (from Glance) of the ramdisk that is mounted at boot time. Required.                                   |
    +----------------------+-------------------------------------------------------------------------------------------------------------+

The properties marked as required must be supplied either during node creation
or shortly after. Some properties may only be required for certain features.

.. _driver-specific documentation: https://docs.openstack.org/developer/ironic/deploy/drivers.html

Note on API versions
--------------------

Starting with API version 1.11, the Bare Metal service added a new initial
provision state of ``enroll`` to its state machine. When this or later API
version is used, new nodes get this state instead of ``available``.

Existing automation tooling that use an API version lower than 1.11 are not
affected, since the initial provision state is still ``available``.
However, using API version 1.11 or above may break existing automation tooling
with respect to node creation.

The default API version used by (the most recent) python-ironicclient is 1.9,
but it may change in the future and should not be relied on.

In the examples below we will use version 1.11 of the Bare metal API.
This gives us the following advantages:

* Explicit power credentials validation before leaving the ``enroll`` state.
* Running node cleaning before entering the ``available`` state.
* Not exposing half-configured nodes to the scheduler.

To set the API version for all commands, you can set the environment variable
``IRONIC_API_VERSION``. For the OpenStackClient baremetal plugin, set
the ``OS_BAREMETAL_API_VERSION`` variable to the same value. For example:

.. code-block:: console

    $ export IRONIC_API_VERSION=1.11
    $ export OS_BAREMETAL_API_VERSION=1.11

Enrollment process
------------------

Creating a node
~~~~~~~~~~~~~~~

This section describes the main steps to enroll a node and make it available
for provisioning. Some steps are shown separately for illustration purposes,
and may be combined if desired.

#. Create a node in the Bare Metal service with the ``node-create`` command.
   At a minimum, you must specify the driver name (for example,
   ``pxe_ipmitool``, ``agent_ipmitool`` or ``ipmi``).

   This command returns the node UUID along with other information
   about the node. The node's provision state will be ``enroll``:

   .. code-block:: console

    $ export IRONIC_API_VERSION=1.11
    $ ironic node-create -d pxe_ipmitool
    +--------------+--------------------------------------+
    | Property     | Value                                |
    +--------------+--------------------------------------+
    | uuid         | dfc6189f-ad83-4261-9bda-b27258eb1987 |
    | driver_info  | {}                                   |
    | extra        | {}                                   |
    | driver       | pxe_ipmitool                         |
    | chassis_uuid |                                      |
    | properties   | {}                                   |
    | name         | None                                 |
    +--------------+--------------------------------------+

    $ ironic node-show dfc6189f-ad83-4261-9bda-b27258eb1987
    +------------------------+--------------------------------------+
    | Property               | Value                                |
    +------------------------+--------------------------------------+
    | target_power_state     | None                                 |
    | extra                  | {}                                   |
    | last_error             | None                                 |
    | maintenance_reason     | None                                 |
    | provision_state        | enroll                               |
    | uuid                   | dfc6189f-ad83-4261-9bda-b27258eb1987 |
    | console_enabled        | False                                |
    | target_provision_state | None                                 |
    | provision_updated_at   | None                                 |
    | maintenance            | False                                |
    | power_state            | None                                 |
    | driver                 | pxe_ipmitool                         |
    | properties             | {}                                   |
    | instance_uuid          | None                                 |
    | name                   | None                                 |
    | driver_info            | {}                                   |
    | ...                    | ...                                  |
    +------------------------+--------------------------------------+

   A node may also be referred to by a logical name as well as its UUID.
   A name can be assigned to the node during creating by adding the ``-n``
   option to the ``node-create`` command or by updating an existing node with
   the ``node-update`` command. See `Logical Names`_ for examples.

#. Starting with API version 1.31 (and ``python-ironicclient`` 1.13), you can
   pick which hardware interface to use with nodes that use hardware types.
   Each interface is represented by a node field called ``<IFACE>_interface``
   where ``<IFACE>`` in the interface type, e.g. ``boot``. See
   :doc:`enabling-drivers` for details on hardware interfaces.

   An interface can be set either separately:

   .. code-block:: console

    $ ironic --ironic-api-version 1.31 node-update $NODE_UUID replace \
        deploy_interface=direct \
        raid_interface=agent

   or set during node creation:

   .. code-block:: console

    $ ironic --ironic-api-version 1.31 node-create -d ipmi \
        --deploy-interface direct \
        --raid-interface agent

   It's an error to try changing this field for a node with a *classic driver*,
   and setting node's driver to classic one causes these fields to be set
   to ``None`` automatically.

#. Update the node ``driver_info`` with the required driver properties, so that
   the Bare Metal service can manage the node:

   .. code-block:: console

    $ ironic node-update $NODE_UUID add \
        driver_info/ipmi_username=$USER \
        driver_info/ipmi_password=$PASS \
        driver_info/ipmi_address=$ADDRESS

   .. note::
      If IPMI is running on a port other than 623 (the default). The port must
      be added to ``driver_info`` by specifying the ``ipmi_port`` value.
      Example:

      .. code-block:: console

       $ ironic node-update $NODE_UUID add driver_info/ipmi_port=$PORT_NUMBER

   You may also specify all ``driver_info`` parameters during node
   creation by passing the **-i** option multiple times:

   .. code-block:: console

     $ ironic node-create -d pxe_ipmitool \
         -i ipmi_username=$USER \
         -i ipmi_password=$PASS \
         -i ipmi_address=$ADDRESS

   See `Choosing a driver`_ above for details on driver properties.

#. Update the node's properties to match the bare metal flavor you created
   when :doc:`configure-nova-flavors`:

   .. code-block:: console

    $ ironic node-update $NODE_UUID add \
        properties/cpus=$CPU_COUNT \
        properties/memory_mb=$RAM_MB \
        properties/local_gb=$DISK_GB \
        properties/cpu_arch=$ARCH

   As above, these can also be specified at node creation by passing the **-p**
   option to ``node-create`` multiple times:

   .. code-block:: console

     $ ironic node-create -d pxe_ipmitool \
         -i ipmi_username=$USER \
         -i ipmi_password=$PASS \
         -i ipmi_address=$ADDRESS \
         -p cpus=$CPU_COUNT \
         -p memory_mb=$RAM_MB \
         -p local_gb=$DISK_GB \
         -p cpu_arch=$ARCH

   These values can also be discovered during `Hardware Inspection`_.

   .. warning::
      The value provided for the ``local_gb`` property must match the size of
      the root device you're going to deploy on. By default
      **ironic-python-agent** picks the smallest disk which is not smaller
      than 4 GiB.

      If you override this logic by using root device hints (see
      :ref:`root-device-hints`), the ``local_gb`` value should match the size
      of picked target disk.

   .. TODO(dtantsur): cover resource classes

#. As mentioned in the :ref:`flavor-creation` section, you should specify
   a deploy kernel and ramdisk compatible with the node's driver, for example:

   .. code-block:: console

    $ ironic node-update $NODE_UUID add \
        driver_info/deploy_kernel=$DEPLOY_VMLINUZ_UUID \
        driver_info/deploy_ramdisk=$DEPLOY_INITRD_UUID

#. You must also inform the Bare Metal service of the network interface cards
   which are part of the node by creating a port with each NIC's MAC address.
   These MAC addresses are passed to the Networking service during instance
   provisioning and used to configure the network appropriately:

   .. code-block:: console

    $ ironic port-create -n $NODE_UUID -a $MAC_ADDRESS

#. If you wish to perform more advanced scheduling of the instances based on
   hardware capabilities, you may add metadata to each node that will be
   exposed to the the Compute scheduler (see: `ComputeCapabilitiesFilter`_).
   A full explanation of this is outside of the scope of this document. It can
   be done through the special ``capabilities`` member of node properties:

   .. code-block:: console

    $ ironic node-update $NODE_UUID add \
        properties/capabilities=key1:val1,key2:val2

   Some capabilities can also be discovered during `Hardware Inspection`_.

Validating node information
~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. To check if Bare Metal service has the minimum information necessary for
   a node's driver to be functional, you may ``validate`` it:

   .. code-block:: console

    $ ironic node-validate $NODE_UUID
    +------------+--------+--------+
    | Interface  | Result | Reason |
    +------------+--------+--------+
    | console    | True   |        |
    | deploy     | True   |        |
    | management | True   |        |
    | power      | True   |        |
    +------------+--------+--------+

   If the node fails validation, each driver interface will return information
   as to why it failed:

   .. code-block:: console

    $ ironic node-validate $NODE_UUID
    +------------+--------+-------------------------------------------------------------------------------------------------------------------------------------+
    | Interface  | Result | Reason                                                                                                                              |
    +------------+--------+-------------------------------------------------------------------------------------------------------------------------------------+
    | console    | None   | not supported                                                                                                                       |
    | deploy     | False  | Cannot validate iSCSI deploy. Some parameters were missing in node's instance_info. Missing are: ['root_gb', 'image_source']        |
    | management | False  | Missing the following IPMI credentials in node's driver_info: ['ipmi_address'].                                                     |
    | power      | False  | Missing the following IPMI credentials in node's driver_info: ['ipmi_address'].                                                     |
    +------------+--------+-------------------------------------------------------------------------------------------------------------------------------------+

   When using the Compute Service with the Bare Metal service, it is safe to
   ignore the deploy interface's validation error due to lack of image
   information. You may continue the enrollment process. This information will
   be set by the Compute Service just before deploying, when an instance is
   requested:

   .. code-block:: console

    $ ironic node-validate $NODE_UUID
    +------------+--------+------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Interface  | Result | Reason                                                                                                                                                           |
    +------------+--------+------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | console    | True   |                                                                                                                                                                  |
    | deploy     | False  | Cannot validate image information for node because one or more parameters are missing from its instance_info. Missing are: ['ramdisk', 'kernel', 'image_source'] |
    | management | True   |                                                                                                                                                                  |
    | power      | True   |                                                                                                                                                                  |
    +------------+--------+------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Making node available for deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order for nodes to be available for deploying workloads on them, nodes
must be in the ``available`` provision state. To do this, nodes
created with API version 1.11 and above must be moved from the ``enroll`` state
to the ``manageable`` state and then to the ``available`` state.
This section can be safely skipped, if API version 1.10 or earlier is used
(which is the case by default).

After creating a node and before moving it from its initial provision state of
``enroll``, basic power and port information needs to be configured on the node.
The Bare Metal service needs this information because it verifies that it is
capable of controlling the node when transitioning the node from ``enroll`` to
``manageable`` state.

To move a node from ``enroll`` to ``manageable`` provision state:

.. code-block:: console

    $ ironic --ironic-api-version 1.11 node-set-provision-state $NODE_UUID manage
    $ ironic node-show $NODE_UUID
    +------------------------+--------------------------------------------------------------------+
    | Property               | Value                                                              |
    +------------------------+--------------------------------------------------------------------+
    | ...                    | ...                                                                |
    | provision_state        | manageable                                                         | <- verify correct state
    | uuid                   | 0eb013bb-1e4b-4f4c-94b5-2e7468242611                               |
    | ...                    | ...                                                                |
    +------------------------+--------------------------------------------------------------------+

.. note:: Since it is an asynchronous call, the response for
          ``ironic node-set-provision-state`` will not indicate whether the
          transition succeeded or not. You can check the status of the
          operation via ``ironic node-show``. If it was successful,
          ``provision_state`` will be in the desired state. If it failed,
          there will be information in the node's ``last_error``.

When a node is moved from the ``manageable`` to ``available`` provision
state, the node will go through automated cleaning if configured to do so (see
:ref:`configure-cleaning`).

To move a node from ``manageable`` to ``available`` provision state:

.. code-block:: console

    $ ironic --ironic-api-version 1.11 node-set-provision-state $NODE_UUID provide
    $ ironic node-show $NODE_UUID
    +------------------------+--------------------------------------------------------------------+
    | Property               | Value                                                              |
    +------------------------+--------------------------------------------------------------------+
    | ...                    | ...                                                                |
    | provision_state        | available                                                          | < - verify correct state
    | uuid                   | 0eb013bb-1e4b-4f4c-94b5-2e7468242611                               |
    | ...                    | ...                                                                |
    +------------------------+--------------------------------------------------------------------+

For more details on the Bare Metal service's state machine, see the
`state machine <http://docs.openstack.org/developer/ironic/dev/states.html>`_
documentation.

.. _ComputeCapabilitiesFilter: http://docs.openstack.org/developer/nova/devref/filter_scheduler.html?highlight=computecapabilitiesfilter

Logical names
-------------

A node may also be referred to by a logical name as well as its UUID.
Names can be assigned either during its creation by adding the ``-n``
option to the ``node-create`` command or by updating an existing node with
the ``node-update`` command.

Node names must be unique, and conform to:

- rfc952_
- rfc1123_
- wiki_hostname_

The node is named 'example' in the following examples:

.. code-block:: console

    $ ironic node-create -d agent_ipmitool -n example

or

.. code-block:: console

    $ ironic node-update $NODE_UUID add name=example


Once assigned a logical name, a node can then be referred to by name or
UUID interchangeably:

.. code-block:: console

    $ ironic node-create -d agent_ipmitool -n example
    +--------------+--------------------------------------+
    | Property     | Value                                |
    +--------------+--------------------------------------+
    | uuid         | 71e01002-8662-434d-aafd-f068f69bb85e |
    | driver_info  | {}                                   |
    | extra        | {}                                   |
    | driver       | agent_ipmitool                       |
    | chassis_uuid |                                      |
    | properties   | {}                                   |
    | name         | example                              |
    +--------------+--------------------------------------+

    $ ironic node-show example
    +------------------------+--------------------------------------+
    | Property               | Value                                |
    +------------------------+--------------------------------------+
    | target_power_state     | None                                 |
    | extra                  | {}                                   |
    | last_error             | None                                 |
    | updated_at             | 2015-04-24T16:23:46+00:00            |
    | ...                    | ...                                  |
    | instance_info          | {}                                   |
    +------------------------+--------------------------------------+

.. _rfc952: http://tools.ietf.org/html/rfc952
.. _rfc1123: http://tools.ietf.org/html/rfc1123
.. _wiki_hostname: http://en.wikipedia.org/wiki/Hostname


Hardware Inspection
-------------------

The Bare Metal service supports hardware inspection that simplifies enrolling
nodes - please see `inspection`_ for details.

.. _`inspection`: http://docs.openstack.org/developer/ironic/deploy/inspection.html

Tenant Networks and Port Groups
-------------------------------

See `Multitenancy in Bare Metal service`_ and
`Port groups configuration in Bare Metal service`_.

.. _`Multitenancy in Bare Metal service`: http://docs.openstack.org/developer/ironic/deploy/multitenancy.html
.. _`Port groups configuration in Bare Metal service`: http://docs.openstack.org/developer/ironic/deploy/portgroups.html
