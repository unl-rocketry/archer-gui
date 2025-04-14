## 2025, UNL Aerospace Club
## Licensed under the GNU General Public License version 3
#
# Program to calculate angles for a dish given two GPS coordinates
#
# Lots of useful formulas for things used here:
# https://www.movable-type.co.uk/scripts/latlong.html

from typing import Any, Optional
import customtkinter
from tkintermapview import TkinterMapView
import serial
from threading import Thread
import json
import signal

## LOCAL IMPORTS ##
from rotator import Rotator
from utils import GPSPoint

# Spaceport:    32.940058,  -106.921903
# Texas Place:  31.046083,  -103.543556
# Lincoln:      40.82320,    -96.69693
DEFAULT_LAT = 40.82320
DEFAULT_LON = -96.69693

# Global variable storing rocket packet data
ROCKET_PACKET_CONT = None

class App(customtkinter.CTk):

    APP_NAME = "ARCHER/AROWSS - UNL Aerospace"
    WIDTH = 1024
    HEIGHT = 768

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self.rotator = Rotator("/dev/ttyUSB1")
        except IOError:
            self.rotator = None

        self.title(App.APP_NAME)
        self.geometry(str(self.WIDTH) + "x" + str(self.HEIGHT))
        self.minsize(App.WIDTH, App.HEIGHT)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # The ground station position
        self.ground_marker: Optional[Any] = None
        self.ground_position = GPSPoint(0, 0, 0)

        # Rocket position
        self.air_marker: Optional[Any] = None
        self.air_position = GPSPoint(0, 0, 0)

        # ============ create two CTkFrames ============

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame_left = customtkinter.CTkFrame(master=self, width=250, corner_radius=0, fg_color=None)
        self.frame_left.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.frame_left.grid_propagate(False)

        self.frame_right = customtkinter.CTkFrame(master=self, corner_radius=0)
        self.frame_right.grid(row=0, column=1, rowspan=1, pady=0, padx=0, sticky="nsew")

        # ============ frame_left ============

        #self.frame_left.grid_rowconfigure(5, weight=1)

        #self.button_1 = customtkinter.CTkButton(master=self.frame_left, text="Set Marker", command=self.set_marker_event)
        #self.button_1.grid(pady=(20, 0), padx=(20, 20), row=0, column=0)

        telemetry_frame = customtkinter.CTkFrame(self.frame_left, fg_color="transparent", width=250)
        telemetry_frame.grid_propagate(False)
        telemetry_frame.grid(pady=(20, 0), padx=(10, 0))

        PADDING = 15
        customtkinter.CTkLabel(telemetry_frame, text="Latitude:", font=("Noto Sans", 18)).grid(row=0, column=0, sticky="e", padx=(0, PADDING))
        self.telemetry_lat = customtkinter.CTkLabel(telemetry_frame, text="", font=("Noto Sans", 18), compound="right", justify="right", anchor="e")
        self.telemetry_lat.grid(row=0, column=1, sticky="e")
        customtkinter.CTkLabel(telemetry_frame, text="Longitude:", font=("Noto Sans", 18)).grid(row=1, column=0, sticky="e", padx=(0, PADDING))
        self.telemetry_lon = customtkinter.CTkLabel(telemetry_frame, text="", font=("Noto Sans", 18), compound="right", justify="right", anchor="e")
        self.telemetry_lon.grid(row=1, column=1, sticky="e")
        customtkinter.CTkLabel(telemetry_frame, text="Altitude:", font=("Noto Sans", 18)).grid(row=2, column=0, sticky="e", padx=(0, PADDING))
        self.telemetry_alt = customtkinter.CTkLabel(telemetry_frame, text="", font=("Noto Sans", 18), compound="right", justify="right", anchor="e")
        self.telemetry_alt.grid(row=2, column=1, sticky="e")
        customtkinter.CTkLabel(telemetry_frame, text="Elevation:", font=("Noto Sans", 18)).grid(row=3, column=0, sticky="e", padx=(0, PADDING))
        self.telemetry_elev = customtkinter.CTkLabel(telemetry_frame, text="", font=("Noto Sans", 18), compound="right", justify="right", anchor="e")
        self.telemetry_elev.grid(row=3, column=1, sticky="e")
        customtkinter.CTkLabel(telemetry_frame, text="Bearing:", font=("Noto Sans", 18)).grid(row=4, column=0, sticky="e", padx=(0, PADDING))
        self.telemetry_bear = customtkinter.CTkLabel(telemetry_frame, text="", font=("Noto Sans", 18), compound="right", justify="right", anchor="e")
        self.telemetry_bear.grid(row=4, column=1, sticky="e")

        # Ground position set
        self.ground_settings = GroundSettings(master=self.frame_left, command=self.set_ground_parameters)
        self.ground_settings.grid()

        self.map_label = customtkinter.CTkLabel(self.frame_left, text="Map Style:", anchor="w")
        self.map_label.grid(padx=(20, 20), pady=(20, 0))
        self.map_option_menu = customtkinter.CTkOptionMenu(self.frame_left, values=["Google hybrid", "Google normal", "Google satellite", "OpenStreetMap"], command=self.change_map)
        self.map_option_menu.grid(padx=(20, 20), pady=(0, 20))

        # ============ frame_right ============

        self.frame_right.grid_rowconfigure(1, weight=1)
        self.frame_right.grid_rowconfigure(0, weight=0)
        self.frame_right.grid_columnconfigure(0, weight=1)
        self.frame_right.grid_columnconfigure(1, weight=0)
        self.frame_right.grid_columnconfigure(2, weight=1)

        self.map_widget = TkinterMapView(self.frame_right, corner_radius=0)
        self.map_widget.grid(row=1, rowspan=1, column=0, columnspan=3, sticky="nswe", padx=(0, 0), pady=(0, 0))

        # Right click event handling
        self.map_widget.add_right_click_menu_command(
            label="Set Ground Position",
            command=self.right_click_ground_position,
            pass_coords=True
        )

        # Set default value
        self.map_widget.set_position(DEFAULT_LAT, DEFAULT_LON)
        self.map_widget.set_zoom(16)
        self.map_option_menu.set("Google hybrid")
        self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)

    def set_ground_parameters(self):
        try:
            lat_str = self.ground_settings.latitude.get()
            if lat_str is not None and lat_str != '':
                self.ground_position.lat = float(lat_str)

            lon_str = self.ground_settings.longitude.get()
            if lon_str is not None and lon_str != '':
                self.ground_position.lon = float(lon_str)

            alt_str = self.ground_settings.altitude.get()
            if alt_str is not None and alt_str != '':
                self.ground_position.alt = float(alt_str)
        except ValueError as e:
            print(f"Invalid value! {e}")

        if self.ground_marker is not None:
            self.ground_marker.delete()

        self.ground_marker = self.map_widget.set_marker(
            self.ground_position.lat,
            self.ground_position.lon
        )

    def set_air_position(self):

        #print("function ran yay")
        if ROCKET_PACKET_CONT is None or "gps" not in ROCKET_PACKET_CONT:
            self.after(500, self.set_air_position)
            return

        gps_lat = ROCKET_PACKET_CONT["gps"]["latitude"]
        gps_lon = ROCKET_PACKET_CONT["gps"]["longitude"]
        gps_alt = ROCKET_PACKET_CONT["gps"]["altitude"]

        self.telemetry_lat.configure(text=f"{gps_lat:.8f}")
        self.telemetry_lon.configure(text=f"{gps_lon:.8f}")
        self.telemetry_alt.configure(text=f"{gps_alt:.2f}m")

        self.air_position = GPSPoint(gps_lat, gps_lon, gps_alt)

        # Update the marker for the air side
        last_marker = self.air_marker
        self.air_marker = self.map_widget.set_marker(gps_lat, gps_lon)
        if last_marker is not None:
            last_marker.delete()

        if self.ground_position is None:
            self.after(500, self.set_air_position)
            return

        # Straight line distance between the ground positions
        #distance = self.ground_position.distance_to(self.air_position)

        # Altitude above ground station position
        altitude = self.ground_position.altitude_to(self.air_position)
        if altitude is None:
            altitude = 0.0

        horiz = self.ground_position.bearing_mag_corrected_to(self.air_position)
        vert = self.ground_position.elevation_to(self.air_position)

        if self.rotator is not None:
            self.rotator.set_position_vertical(vert)
            self.rotator.set_position_horizontal(horiz)

        self.telemetry_bear.configure(text=f"{horiz:.2f}°")
        self.telemetry_elev.configure(text=f"{vert:.2f}°")

        self.after(500, self.set_air_position)

    def right_click_ground_position(self, coords):
        if self.ground_marker is not None:
            self.ground_marker.delete()

        self.ground_position = GPSPoint(coords[0], coords[1], self.ground_position.alt)
        self.ground_marker = self.map_widget.set_marker(coords[0], coords[1])

        self.ground_settings.latitude.set(coords[0])
        self.ground_settings.longitude.set(coords[1])
        self.ground_settings.altitude.set(str(self.ground_position.alt))

    def change_map(self, new_map: str):
        match new_map:
            case "Google hybrid":
                self.map_widget.set_tile_server(
                    "https://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}&s=Ga",
                    max_zoom=22
                )
            case "Google normal":
                self.map_widget.set_tile_server(
                    "https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga",
                    max_zoom=22
                )
            case "Google satellite":
                self.map_widget.set_tile_server(
                    "https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga",
                    max_zoom=22
                )
            case "OpenStreetMap":
                self.map_widget.set_tile_server(
                    "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
                    max_zoom=22
                )

    def on_closing(self, signal=0, frame=None):
        print("Exiting!")
        self.destroy()

    def start(self):
        self.after(500, self.set_air_position)

        self.mainloop()


class GroundSettings(customtkinter.CTkFrame):
    def __init__(self, master, command, **kwargs):
        super().__init__(master, fg_color="transparent", border_width=0, **kwargs)

        self.label = customtkinter.CTkLabel(self, text="Ground Settings:", anchor="w")
        self.label.grid()

        self.latitude = LabeledTextEntry(master=self, label_text="Latitude")
        self.latitude.grid(pady=2.5, padx=5, sticky="w")

        self.longitude = LabeledTextEntry(master=self, label_text="Longitude")
        self.longitude.grid(pady=2.5, padx=5, sticky="w")

        self.altitude = LabeledTextEntry(master=self, label_text="Altitude")
        self.altitude.grid(pady=2.5, padx=5, sticky="w")

        self.button = customtkinter.CTkButton(self, text="Set Ground Settings", command=command)
        self.button.grid(pady=5)


class LabeledTextEntry(customtkinter.CTkFrame):
    """ A text entry widget with a label """

    def __init__(self, master, label_text="", placeholder_text="", **kwargs):
        super().__init__(master, **kwargs)

        self.label = customtkinter.CTkLabel(self, text=label_text, width=70)
        self.label.grid(row=0, column=0, padx=5)

        self.entry = customtkinter.CTkEntry(self, placeholder_text=placeholder_text)
        self.entry.grid(row=0, column=1)

    def get(self) -> str:
        return self.entry.get()

    def set(self, string: str):
        self.entry.delete(0, 'end')
        self.entry.insert(0, string)


def gps_loop(gps_port: str):
    try:
        gps_serial = serial.Serial(gps_port, 57600, timeout=1)
    except IOError:
        return

    while True:
        new_data = gps_serial.readline().decode("utf-8").strip()
        # print(new_data)
        try:
            new_new_data = json.loads(new_data)
            # print(new_data)
            global ROCKET_PACKET_CONT
            ROCKET_PACKET_CONT = new_new_data
            # print(ROCKET_PACKET_CONT["latitude"])
        except IOError:
            print("Failed to decode json")

        print(new_data)


if __name__ == "__main__":
    t = Thread(target=gps_loop, args=["/dev/ttyUSB0"], name="gps_thread")
    t.start()

    app = App()

    # Catch Ctl + C
    signal.signal(signal.SIGINT, app.on_closing)

    app.start()
