# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Interface for Dynamips virtual Frame-Relay switch module.
http://github.com/GNS3/dynamips/blob/master/README.hypervisor#L642
"""

import os
from ..dynamips_error import DynamipsError

import logging
log = logging.getLogger(__name__)


class FrameRelaySwitch(object):
    """
    Dynamips Frame Relay switch.

    :param hypervisor: Dynamips hypervisor instance
    :param name: name for this switch
    """

    _instances = []

    def __init__(self, hypervisor, name):

        # find an instance identifier (0 < id <= 4096)
        self._id = 0
        for identifier in range(1, 4097):
            if identifier not in self._instances:
                self._id = identifier
                self._instances.append(self._id)
                break

        if self._id == 0:
            raise DynamipsError("Maximum number of instances reached")

        self._hypervisor = hypervisor
        self._name = '"' + name + '"'  # put name into quotes to protect spaces
        self._hypervisor.send("frsw create {}".format(self._name))

        log.info("Frame Relay switch {name} [id={id}] has been created".format(name=self._name,
                                                                               id=self._id))

        self._hypervisor.devices.append(self)
        self._nios = {}
        self._mapping = {}

    @classmethod
    def reset(cls):
        """
        Resets the instance count and the allocated instances list.
        """

        cls._instances.clear()

    @property
    def id(self):
        """
        Returns the unique ID for this Frame Relay switch.

        :returns: id (integer)
        """

        return self._id

    @property
    def name(self):
        """
        Returns the current name of this Frame Relay switch.

        :returns: Frame Relay switch name
        """

        return self._name[1:-1]  # remove quotes

    @name.setter
    def name(self, new_name):
        """
        Renames this Frame Relay switch.

        :param new_name: New name for this switch
        """

        new_name = '"' + new_name + '"'  # put the new name into quotes to protect spaces
        self._hypervisor.send("frsw rename {name} {new_name}".format(name=self._name,
                                                                     new_name=new_name))

        log.info("Frame Relay switch {name} [id={id}]: renamed to {new_name}".format(name=self._name,
                                                                                     id=self._id,
                                                                                     new_name=new_name))

        self._name = new_name

    @property
    def hypervisor(self):
        """
        Returns the current hypervisor.

        :returns: hypervisor instance
        """

        return self._hypervisor

    def list(self):
        """
        Returns all Frame Relay switches instances.

        :returns: list of all Frame Relay switches
        """

        return self._hypervisor.send("frsw list")

    @property
    def nios(self):
        """
        Returns all the NIOs member of this Frame Relay switch.

        :returns: nio list
        """

        return self._nios

    @property
    def mapping(self):
        """
        Returns port mapping

        :returns: mapping list
        """

        return self._mapping

    def delete(self):
        """
        Deletes this Frame Relay switch.
        """

        self._hypervisor.send("frsw delete {}".format(self._name))

        log.info("Frame Relay switch {name} [id={id}] has been deleted".format(name=self._name,
                                                                               id=self._id))
        self._hypervisor.devices.remove(self)
        self._instances.remove(self._id)

    def has_port(self, port):
        """
        Checks if a port exists on this Frame Relay switch.

        :returns: boolean
        """

        if port in self._nios:
            return True
        return False

    def add_nio(self, nio, port):
        """
        Adds a NIO as new port on Frame Relay switch.

        :param nio: NIO instance to add
        :param port: port to allocate for the NIO
        """

        if port in self._nios:
            raise DynamipsError("Port {} isn't free".format(port))

        log.info("Frame Relay switch {name} [id={id}]: NIO {nio} bound to port {port}".format(name=self._name,
                                                                                              id=self._id,
                                                                                              nio=nio,
                                                                                              port=port))

        self._nios[port] = nio

    def remove_nio(self, port):
        """
        Removes the specified NIO as member of this Frame Relay switch.

        :param port: allocated port

        :returns: the NIO that was bound to the allocated port
        """

        if port not in self._nios:
            raise DynamipsError("Port {} is not allocated".format(port))

        nio = self._nios[port]
        log.info("Frame Relay switch {name} [id={id}]: NIO {nio} removed from port {port}".format(name=self._name,
                                                                                                  id=self._id,
                                                                                                  nio=nio,
                                                                                                  port=port))

        del self._nios[port]
        return nio

    def map_vc(self, port1, dlci1, port2, dlci2):
        """
        Creates a new Virtual Circuit connection (unidirectional).

        :param port1: input port
        :param dlci1: input DLCI
        :param port2: output port
        :param dlci2: output DLCI
        """

        if port1 not in self._nios:
            raise DynamipsError("Port {} is not allocated".format(port1))

        if port2 not in self._nios:
            raise DynamipsError("Port {} is not allocated".format(port2))

        nio1 = self._nios[port1]
        nio2 = self._nios[port2]

        self._hypervisor.send("frsw create_vc {name} {input_nio} {input_dlci} {output_nio} {output_dlci}".format(name=self._name,
                                                                                                                 input_nio=nio1,
                                                                                                                 input_dlci=dlci1,
                                                                                                                 output_nio=nio2,
                                                                                                                 output_dlci=dlci2))

        log.info("Frame Relay switch {name} [id={id}]: VC from port {port1} DLCI {dlci1} to port {port2} DLCI {dlci2} created".format(name=self._name,
                                                                                                                                      id=self._id,
                                                                                                                                      port1=port1,
                                                                                                                                      dlci1=dlci1,
                                                                                                                                      port2=port2,
                                                                                                                                      dlci2=dlci2))

        self._mapping[(port1, dlci1)] = (port2, dlci2)

    def unmap_vc(self, port1, dlci1, port2, dlci2):
        """
        Deletes a Virtual Circuit connection (unidirectional).

        :param port1: input port
        :param dlci1: input DLCI
        :param port2: output port
        :param dlci2: output DLCI
        """

        if port1 not in self._nios:
            raise DynamipsError("Port {} is not allocated".format(port1))

        if port2 not in self._nios:
            raise DynamipsError("Port {} is not allocated".format(port2))

        nio1 = self._nios[port1]
        nio2 = self._nios[port2]

        self._hypervisor.send("frsw delete_vc {name} {input_nio} {input_dlci} {output_nio} {output_dlci}".format(name=self._name,
                                                                                                                 input_nio=nio1,
                                                                                                                 input_dlci=dlci1,
                                                                                                                 output_nio=nio2,
                                                                                                                 output_dlci=dlci2))

        log.info("Frame Relay switch {name} [id={id}]: VC from port {port1} DLCI {dlci1} to port {port2} DLCI {dlci2} deleted".format(name=self._name,
                                                                                                                                      id=self._id,
                                                                                                                                      port1=port1,
                                                                                                                                      dlci1=dlci1,
                                                                                                                                      port2=port2,
                                                                                                                                      dlci2=dlci2))
        del self._mapping[(port1, dlci1)]

    def start_capture(self, port, output_file, data_link_type="DLT_FRELAY"):
        """
        Starts a packet capture.

        :param port: allocated port
        :param output_file: PCAP destination file for the capture
        :param data_link_type: PCAP data link type (DLT_*), default is DLT_FRELAY
        """

        if port not in self._nios:
            raise DynamipsError("Port {} is not allocated".format(port))

        nio = self._nios[port]

        data_link_type = data_link_type.lower()
        if data_link_type.startswith("dlt_"):
            data_link_type = data_link_type[4:]

        if nio.input_filter[0] is not None and nio.output_filter[0] is not None:
            raise DynamipsError("Port {} has already a filter applied".format(port))

        try:
            os.makedirs(os.path.dirname(output_file))
        except FileExistsError:
            pass
        except OSError as e:
            raise DynamipsError("Could not create captures directory {}".format(e))

        nio.bind_filter("both", "capture")
        nio.setup_filter("both", "{} {}".format(data_link_type, output_file))

        log.info("Frame relay switch {name} [id={id}]: starting packet capture on {port}".format(name=self._name,
                                                                                                 id=self._id,
                                                                                                 port=port))

    def stop_capture(self, port):
        """
        Stops a packet capture.

        :param port: allocated port
        """

        if port not in self._nios:
            raise DynamipsError("Port {} is not allocated".format(port))

        nio = self._nios[port]
        nio.unbind_filter("both")
        log.info("Frame relay switch {name} [id={id}]: stopping packet capture on {port}".format(name=self._name,
                                                                                                 id=self._id,
                                                                                                 port=port))
