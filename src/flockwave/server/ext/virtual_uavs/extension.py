from __future__ import absolute_import, division

from functools import partial
from trio import open_nursery, sleep
from typing import Callable

from flockwave.gps.vectors import (
    FlatEarthCoordinate,
    GPSCoordinate,
    FlatEarthToGPSCoordinateTransformation,
)
from flockwave.spec.ids import make_valid_object_id

from ..base import UAVExtensionBase

from .driver import VirtualUAV, VirtualUAVDriver
from .placement import place_drones


__all__ = ("construct", "dependencies")


class VirtualUAVProviderExtension(UAVExtensionBase):
    """Extension that creates one or more virtual UAVs in the server.

    Virtual UAVs circle around a given point in a given radius, with constant
    angular velocity. They are able to respond to landing and takeoff
    requests, and also handle the following commands:

    * Sending ``yo`` to a UAV makes it respond with either ``yo!``, ``yo?``
      or ``yo.``, with a mean delay of 500 milliseconds.

    * Sending ``timeout`` to a UAV makes it register the command but never
      finish its execution. Useful for testing the timeout and cancellation
      mechanism of the command execution manager of the server.
    """

    def __init__(self):
        """Constructor."""
        super(VirtualUAVProviderExtension, self).__init__()
        self._delay = 1

        self.radiation = None
        self.uavs = []
        self.uav_ids = []

    def _create_driver(self):
        return VirtualUAVDriver()

    def configure(self, configuration):
        # Get the number of UAVs to create and the format of the IDs
        count = configuration.get("count", 0)
        id_format = configuration.get("id_format", "VIRT-{0}")

        # Specify the default takeoff area
        default_takeoff_area = {"type": "grid", "spacing": 5}

        # Place the given number of drones on a circle
        home_positions = [
            FlatEarthCoordinate(x=vec.x, y=vec.y)
            for vec in place_drones(
                count, **configuration.get("takeoff_area", default_takeoff_area)
            )
        ]

        # Set the status updater thread frequency
        self.delay = configuration.get("delay", 1)

        # Get the center of the circle
        if "origin" not in configuration and "center" in configuration:
            self.log.warn("'center' is deprecated; use 'origin' instead")
            configuration["origin"] = configuration.pop("center")
        origin = configuration.get("origin")
        origin = GPSCoordinate(
            lat=origin["lat"], lon=origin["lon"], agl=origin.get("agl", 0), amsl=None
        )

        # Get the direction of the X axis
        orientation = configuration.get("orientation", 0)

        # Get the type of the coordinate system
        type = configuration.get("type", "neu")

        # Create a transformation from flat Earth to GPS
        trans = FlatEarthToGPSCoordinateTransformation(
            origin=origin, orientation=orientation, type=type
        )

        # Generate IDs for the UAVs and then create them
        self.uav_ids = [
            make_valid_object_id(id_format.format(index)) for index in range(count)
        ]
        self.uavs = [
            self._driver.create_uav(id, home=trans.to_gps(home), heading=orientation)
            for id, home in zip(self.uav_ids, home_positions)
        ]

        # Get hold of the 'radiation' extension and associate it to all our
        # UAVs
        radiation_ext = self.app.extension_manager.import_api("radiation")
        for uav in self.uavs:
            uav.radiation_ext = radiation_ext

    @property
    def delay(self):
        """Number of seconds that must pass between two consecutive
        simulated status updates to the UAVs.
        """
        return self._delay

    @delay.setter
    def delay(self, value):
        self._delay = max(float(value), 0)

    async def simulate_uav(self, uav: VirtualUAV, spawn: Callable):
        """Simulates the behaviour of a single UAV in the application.

        Parameters:
            uav: the virtual UAV to simulate
            spawn: function to call when the UAV wishes to spawn a background
                task
        """
        updater = partial(self.app.request_to_send_UAV_INF_message_for, [uav.id])

        with self.app.object_registry.use(uav):
            while True:
                # Simulate the UAV behaviour from boot time
                shutdown_reason = await uav.run_single_boot(
                    self._delay,
                    mutate=self.create_device_tree_mutation_context,
                    notify=updater,
                    spawn=spawn,
                )

                # If we need to restart, let's restart after a short delay.
                # Otherwise let's stop the loop.
                if shutdown_reason == "shutdown":
                    break
                else:
                    await sleep(0.2)

    async def worker(self, app, configuration, logger):
        """Main background task of the extension that updates the state of
        the UAVs periodically.
        """
        async with open_nursery() as nursery:
            for uav in self.uavs:
                nursery.start_soon(self.simulate_uav, uav, nursery.start_soon)


construct = VirtualUAVProviderExtension
dependencies = ()