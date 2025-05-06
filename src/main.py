## 2025, UNL Aerospace Club
## Licensed under the GNU General Public License version 3
#
# Program to calculate angles for a dish given two GPS coordinates
#
# Lots of useful formulas for things used here:
# https://www.movable-type.co.uk/scripts/latlong.html

import pathlib
from typing import Any, Callable, Optional, Union
import customtkinter
import tomlkit
from tkintermapview import TkinterMapView
import serial
import serial.tools.list_ports
from threading import Event, Thread
import json
import signal
import tkinter as tk
import datetime

## LOCAL IMPORTS ##
from rotator import Rotator
from rotator_command import RotatorCommandWindow
from utils import GPSPoint, crc8
###################

ROCKET_PACKET_CONT = None
"""Global variable storing rocket packet data"""


class App(customtkinter.CTk):
    APP_NAME = "ARCHER/AROWSS - UNL Aerospace"
    WIDTH = 1024
    HEIGHT = 768

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title(App.APP_NAME)
        self.geometry(str(self.WIDTH) + "x" + str(self.HEIGHT))
        self.minsize(App.WIDTH, App.HEIGHT)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # ============ create two CTkFrames ============

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame_left = customtkinter.CTkFrame(
            master=self, width=400, corner_radius=0, fg_color=None
        )
        self.frame_left.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.frame_left.grid_propagate(False)

        self.frame_right = customtkinter.CTkFrame(master=self, corner_radius=0)
        self.frame_right.grid(row=0, column=1, rowspan=1, pady=0, padx=0, sticky="nsew")

        # ============ frame_left ============

        self.frame_left.grid_columnconfigure(0, weight=1)

        # Telemetry display
        self.telemetry = Telemetry(self.frame_left, command=self.set_ground_parameters)
        self.telemetry.grid(pady=20)

        # Ground position settings
        self.ground_settings = GroundSettings(
            self.frame_left, command=self.set_ground_parameters
        )
        self.ground_settings.grid()

        customtkinter.CTkLabel(
            self.frame_left, text="Port Settings:", anchor="w", font=("Noto Sans", 18)
        ).grid(pady=(20, 5))

        self.rotator_port_menu = LabeledSelectMenu(
            self.frame_left, label_text="Rotator Port"
        )
        self.rotator_port_menu.grid(pady=(0, 10))
        self.rfd_port_menu = LabeledSelectMenu(self.frame_left, label_text="RFD Port")
        self.rfd_port_menu.grid(pady=(0, 10))
        customtkinter.CTkButton(
            self.frame_left, text="Rescan Ports", command=self.rescan_ports
        ).grid()

        self.set_buttons_frame = customtkinter.CTkFrame(
            self.frame_left, corner_radius=0, fg_color="transparent"
        )
        self.set_buttons_frame.grid()
        customtkinter.CTkButton(
            self.set_buttons_frame, text="Set RFD", width=50, command=self.set_telemetry
        ).grid(pady=10, padx=5, column=0, row=0)
        customtkinter.CTkButton(
            self.set_buttons_frame,
            text="Set Rotator",
            width=50,
            command=self.set_rotator,
        ).grid(pady=10, padx=5, column=1, row=0)

        self.rotator_command_window_button = customtkinter.CTkButton(
            self.frame_left,
            text="Rotator Commands",
            command=lambda: RotatorCommandWindow(self.rotator),
        )
        self.rotator_command_window_button.grid(pady=10)

        # Map style settings
        customtkinter.CTkLabel(
            self.frame_left, text="Map Settings:", anchor="w", font=("Noto Sans", 18)
        ).grid(pady=(20, 5))
        self.map_option_menu = LabeledSelectMenu(
            self.frame_left,
            label_text="Map Style",
            values=[
                "Google hybrid",
                "Google normal",
                "Google satellite",
                "OpenStreetMap",
            ],
            command=self.change_map,
        )
        self.map_option_menu.grid(padx=(20, 20), pady=(0, 20))

        # ============ frame_right ============

        self.frame_right.grid_rowconfigure(1, weight=1)
        self.frame_right.grid_rowconfigure(0, weight=0)
        self.frame_right.grid_columnconfigure(0, weight=1)
        self.frame_right.grid_columnconfigure(1, weight=0)
        self.frame_right.grid_columnconfigure(2, weight=1)

        self.map_widget = TkinterMapView(self.frame_right, corner_radius=0)
        self.map_widget.grid(
            row=1,
            rowspan=1,
            column=0,
            columnspan=3,
            sticky="nswe",
            padx=(0, 0),
            pady=(0, 0),
        )

        # Right click event handling
        self.map_widget.add_right_click_menu_command(
            label="Set Ground Position",
            command=self.right_click_ground_position,
            pass_coords=True,
        )

    def set_ports(self):
        self.set_rotator()
        self.set_telemetry()

    def set_rotator(self):
        rotator_port = self.rotator_port_menu.get()
        if rotator_port != "Select…":
            rotator_port = rotator_port.split(maxsplit=1)[0]
            try:
                self.rotator = Rotator(rotator_port)
                print(f"Rotator protocol v{self.rotator.protocol_version}")
            except:  # noqa: E722
                print("Rotator failed to initalize!")

    def set_telemetry(self):
        if self.rfd_event is not None:
            self.rfd_event.set()

        rfd_port = self.rfd_port_menu.get()
        if rfd_port != "Select…":
            rfd_port = rfd_port.split(maxsplit=1)[0]
            self.rfd_event = Event()
            t = Thread(
                target=gps_loop, args=[rfd_port, self.rfd_event], name="gps_thread"
            )
            t.start()
            print("RFD Setup")

    def rescan_ports(self):
        """Rescan and update the serial ports"""
        self.rotator_port_menu.option_menu.configure(state="disabled")
        self.rfd_port_menu.option_menu.configure(state="disabled")

        self.port_list = list(
            filter(
                lambda p: "/dev/ttyS" not in p,
                map(lambda p: str(p), serial.tools.list_ports.comports()),
            )
        )
        self.port_list.insert(0, "Select…")

        self.rotator_port_menu.set_values(self.port_list)
        self.rfd_port_menu.set_values(self.port_list)

        self.rotator_port_menu.option_menu.configure(state="normal")
        self.rfd_port_menu.option_menu.configure(state="normal")

    def set_ground_parameters(self):
        try:
            lat_str = self.ground_settings.latitude.get()
            if lat_str is not None and lat_str != "":
                self.ground_position.lat = float(lat_str)
                self.ground_pos_toml["latitude"] = float(lat_str)

            lon_str = self.ground_settings.longitude.get()
            if lon_str is not None and lon_str != "":
                self.ground_position.lon = float(lon_str)
                self.ground_pos_toml["longitude"] = float(lon_str)

            alt_str = self.ground_settings.altitude.get()
            if alt_str is not None and alt_str != "":
                self.ground_position.alt = float(alt_str)
                self.ground_pos_toml["altitude"] = float(alt_str)

            tomlkit.dump(
                self.ground_pos_toml,
                open("ground_location.toml", "w", encoding="utf-8"),
            )
        except ValueError as e:
            print(f"Invalid value! {e}")

        if self.ground_marker is not None:
            self.ground_marker.set_position(
                self.ground_position.lat, self.ground_position.lon
            )
        else:
            self.ground_marker = self.map_widget.set_marker(
                self.ground_position.lat, self.ground_position.lon
            )

    def right_click_ground_position(self, coords):
        if self.ground_marker is not None:
            self.ground_marker.set_position(coords[0], coords[1])
        else:
            self.ground_marker = self.map_widget.set_marker(coords[0], coords[1])

        self.ground_position = GPSPoint(coords[0], coords[1], self.ground_position.alt)

        self.ground_settings.latitude.set(coords[0])
        self.ground_pos_toml["latitude"] = float(coords[0])
        self.ground_settings.longitude.set(coords[1])
        self.ground_pos_toml["longitude"] = float(coords[1])
        self.ground_settings.altitude.set(str(self.ground_position.alt))

        tomlkit.dump(
            self.ground_pos_toml, open("ground_location.toml", "w", encoding="utf-8")
        )

    def set_air_position(self):
        # print("function ran yay")
        if ROCKET_PACKET_CONT is None or "gps" not in ROCKET_PACKET_CONT:
            self.after(500, self.set_air_position)
            return

        if ROCKET_PACKET_CONT["gps"] is None:
            self.after(500, self.set_air_position)
            return

        try:
            gps_lat = ROCKET_PACKET_CONT["gps"]["latitude"]
            gps_lon = ROCKET_PACKET_CONT["gps"]["longitude"]
            gps_alt = ROCKET_PACKET_CONT["gps"]["altitude"]
        except Exception as e:
            print(f"Not all fields available: {e}")
            self.after(500, self.set_air_position)
            return

        self.telemetry.lat.configure(text=f"{gps_lat:.8f}")
        self.telemetry.lon.configure(text=f"{gps_lon:.8f}")
        self.telemetry.alt.configure(text=f"{gps_alt:.2f}m")

        self.air_position = GPSPoint(gps_lat, gps_lon, gps_alt)

        # Update the marker for the air side
        if self.air_marker is not None:
            self.air_marker.set_position(gps_lat, gps_lon)
        else:
            self.air_marker = self.map_widget.set_marker(gps_lat, gps_lon)

        if self.ground_position is None:
            self.after(500, self.set_air_position)
            return

        # Straight line distance between the ground positions
        distance = self.ground_position.distance_to(self.air_position)

        # Altitude above ground station position
        altitude = self.ground_position.altitude_to(self.air_position)
        if altitude is None:
            altitude = 0.0

        horiz = self.ground_position.bearing_mag_corrected_to(self.air_position)
        vert = self.ground_position.elevation_to(self.air_position)

        if self.rotator is not None:
            self.rotator.set_position_vertical(vert)
            self.rotator.set_position_horizontal(horiz)

        self.telemetry.rot_az.configure(text=f"{horiz:.1f}°")
        self.telemetry.rot_alt.configure(text=f"{vert:.1f}°")
        self.telemetry.dist.configure(text=f"{distance:.1f}")
        self.telemetry.gr_alt.configure(text=f"{altitude:.1f}")

        self.after(500, self.set_air_position)

    def change_map(self, new_map: str):
        match new_map:
            case "Google hybrid":
                self.map_widget.set_tile_server(
                    "https://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}&s=Ga",
                    max_zoom=22,
                )
            case "Google normal":
                self.map_widget.set_tile_server(
                    "https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga",
                    max_zoom=22,
                )
            case "Google satellite":
                self.map_widget.set_tile_server(
                    "https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga",
                    max_zoom=22,
                )
            case "OpenStreetMap":
                self.map_widget.set_tile_server(
                    "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", max_zoom=22
                )

    def on_closing(self, signal=0, frame=None):
        print("Exiting!")

        tomlkit.dump(
            self.ground_pos_toml, open("ground_location.toml", "w", encoding="utf-8")
        )

        if self.rfd_event is not None:
            self.rfd_event.set()

        self.destroy()

    def start(self):
        self.rescan_ports()

        # By default the rotator is None
        self.rotator = None
        # RFD thread event
        self.rfd_event = None

        #
        if pathlib.Path("./ground_location.toml").is_file():
            self.ground_pos_toml = tomlkit.load(
                open("ground_location.toml", "r", encoding="utf-8")
            )
        else:
            self.ground_pos_toml = tomlkit.TOMLDocument()
            self.ground_pos_toml.add("latitude", 0)  # type: ignore
            self.ground_pos_toml.add("longitude", 0)  # type: ignore
            self.ground_pos_toml.add("altitude", 0)  # type: ignore
            print(self.ground_pos_toml)
            tomlkit.dump(
                self.ground_pos_toml,
                open("ground_location.toml", "w+", encoding="utf-8"),
            )

        default_lat = float(self.ground_pos_toml.item("latitude"))  # type: ignore
        default_lon = float(self.ground_pos_toml.item("longitude"))  # type: ignore
        default_alt = float(self.ground_pos_toml.item("altitude"))  # type: ignore

        # Set default value
        self.map_widget.set_position(default_lat, default_lon)
        self.map_widget.set_zoom(16)
        self.map_option_menu.set("Google hybrid")
        self.map_widget.set_tile_server(
            "https://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22
        )

        # The ground station position
        self.ground_marker = None
        self.ground_position = GPSPoint(default_lat, default_lon, default_alt)
        self.ground_settings.latitude.set(str(default_lat))
        self.ground_settings.longitude.set(str(default_lon))
        self.ground_settings.altitude.set(str(default_alt))
        self.set_ground_parameters()

        # Rocket position
        self.air_marker = None
        self.air_position = GPSPoint(0, 0, 0)

        self.after(500, self.set_air_position)

        self.mainloop()


class Telemetry(customtkinter.CTkFrame):
    def __init__(self, master, command, **kwargs):
        super().__init__(master, fg_color="transparent", border_width=0, **kwargs)

        customtkinter.CTkLabel(
            self, text="Telemetry:", anchor="w", font=("Noto Sans", 18)
        ).grid(columnspan=4, pady=(0, 5))

        sep = tk.Frame(self, bg="#474747", height=1, bd=0)
        sep.grid(row=1, columnspan=4, sticky="ew")

        customtkinter.CTkLabel(self, text="Latitude:").grid(row=2, column=0, padx=10)
        self.lat = customtkinter.CTkLabel(self, width=200, text="...", anchor="w")
        self.lat.grid(row=2, column=1, columnspan=4)

        customtkinter.CTkLabel(self, text="Longitude:").grid(row=3, column=0, padx=10)
        self.lon = customtkinter.CTkLabel(self, width=200, text="...", anchor="w")
        self.lon.grid(row=3, column=1, columnspan=4)

        customtkinter.CTkLabel(self, text="Altitude:").grid(row=4, column=0, padx=10)
        self.alt = customtkinter.CTkLabel(self, width=200, text="...", anchor="w")
        self.alt.grid(row=4, column=1, columnspan=4)

        sep = tk.Frame(self, bg="#474747", height=1, bd=0)
        sep.grid(row=5, columnspan=4, sticky="ew")

        customtkinter.CTkLabel(self, text="Elevation:").grid(row=6, column=0, padx=10)
        self.rot_alt = customtkinter.CTkLabel(self, width=50, text="...", anchor="w")
        self.rot_alt.grid(row=6, column=1)

        customtkinter.CTkLabel(self, text="Bearing:").grid(row=6, column=2, padx=10)
        self.rot_az = customtkinter.CTkLabel(self, width=50, text="...", anchor="w")
        self.rot_az.grid(row=6, column=3)

        customtkinter.CTkLabel(self, text="Distance:").grid(row=7, column=0, padx=10)
        self.dist = customtkinter.CTkLabel(self, width=50, text="...", anchor="w")
        self.dist.grid(row=7, column=1)

        customtkinter.CTkLabel(self, text="Ground Alt:").grid(row=7, column=2, padx=10)
        self.gr_alt = customtkinter.CTkLabel(self, width=50, text="...", anchor="w")
        self.gr_alt.grid(row=7, column=3)

        sep = tk.Frame(self, bg="#474747", height=1, bd=0)
        sep.grid(row=8, columnspan=4, sticky="ew")


class GroundSettings(customtkinter.CTkFrame):
    def __init__(self, master, command, **kwargs):
        super().__init__(master, fg_color="transparent", border_width=0, **kwargs)

        customtkinter.CTkLabel(
            self, text="Ground Settings:", anchor="w", font=("Noto Sans", 18)
        ).grid(pady=(0, 5))

        self.latitude = LabeledTextEntry(self, label_text="Latitude")
        self.latitude.grid(pady=2.5, padx=5, sticky="w")

        self.longitude = LabeledTextEntry(self, label_text="Longitude")
        self.longitude.grid(pady=2.5, padx=5, sticky="w")

        self.altitude = LabeledTextEntry(self, label_text="Altitude")
        self.altitude.grid(pady=2.5, padx=5, sticky="w")

        self.button = customtkinter.CTkButton(
            self, text="Set Ground Settings", command=command
        )
        self.button.grid(pady=(5, 0))


class LabeledSelectMenu(customtkinter.CTkFrame):
    def __init__(
        self,
        master,
        label_text: str = "",
        values: Optional[list] | None = None,
        command: Union[Callable[[str], Any], None] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.label = customtkinter.CTkLabel(self, text=label_text, anchor="w")
        self.label.grid(row=0, column=0, padx=10)

        self.option_menu = customtkinter.CTkOptionMenu(
            self,
            values=values,
            command=command,
            width=150,
            dynamic_resizing=False,
        )
        self.option_menu.grid(row=0, column=1)

    def set_values(self, values: list[str]):
        self.option_menu.configure(values=values)
        self.option_menu.set(values[0])

    def set(self, value: str):
        self.option_menu.set(value)

    def get(self) -> str:
        return self.option_menu.get()


class LabeledTextEntry(customtkinter.CTkFrame):
    """A text entry widget with a label"""

    def __init__(self, master, label_text="", placeholder_text="", **kwargs):
        super().__init__(master, **kwargs)

        self.label = customtkinter.CTkLabel(self, text=label_text, width=70, anchor="e")
        self.label.grid(row=0, column=0, padx=5)

        self.entry = customtkinter.CTkEntry(self, placeholder_text=placeholder_text)
        self.entry.grid(row=0, column=1)

    def get(self) -> str:
        return self.entry.get()

    def set(self, string: str):
        self.entry.delete(0, "end")
        self.entry.insert(0, string)


def gps_loop(gps_port: str, event: Event):
    try:
        gps_serial = serial.Serial(gps_port, 57600, timeout=1)
    except IOError as e:
        print(f"Failed to start GPS loop: {e}")
        return

    print("Started GPS loop")

    # Ignoring the errors in this is OK because it must not crash!
    while not event.is_set():
        try:
            new_data = gps_serial.readline().decode("utf-8").strip()
        except Exception as e:
            print(f"Failed to read telemetry: {e}")
            continue

        if len(new_data) == 0:
            continue

        try:
            received_crc, received_json = new_data.split(maxsplit=1)
            received_crc = int(received_crc)
        except Exception as e:
            print(f"Splitting failed: {e}")
            continue

        # Calculate CRC from the data
        calculated_crc = None
        try:
            calculated_crc = crc8(received_json.encode("utf-8"))
        except Exception as e:
            print(f"Could not calculate new CRC: {e}")
            continue

        # Compare CRCs if they exist and work
        if calculated_crc != received_crc:
            print(f"CRCs do not match ({calculated_crc} != {received_crc})")
            continue
        else:
            print(f"CRCs match ({calculated_crc} == {received_crc})")

        # Load the data as JSON and add it to the packet
        try:
            decoded_data = json.loads(received_json)
            global ROCKET_PACKET_CONT
            ROCKET_PACKET_CONT = decoded_data
            print(decoded_data)
            try:
                timestamp = datetime.datetime.now().isoformat()

                with open("packet_log.txt", "a") as packetlog:
                    packetlog.write(timestamp)
                    packetlog.write(",")
                    packetlog.write(received_json)
                    packetlog.write("\n")
            except Exception as e:
                print(f"Saving to txt failed: {e}")
        except Exception as e:
            print(f"Failed to decode json: {e}")

    # Close the serial port
    gps_serial.close()


if __name__ == "__main__":
    app = App()

    # Catch Ctl + C
    signal.signal(signal.SIGINT, app.on_closing)

    app.start()
