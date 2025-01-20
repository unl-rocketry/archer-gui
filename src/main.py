import math
from typing import Tuple

## 2025, UNL Aerospace Club
## Grant Gardner, Yen Do
#
# Program to calculate angles for a dish given two GPS coordinates
#
# Lots of useful formulas for things used here:
# https://www.movable-type.co.uk/scripts/latlong.html

# CONSTANTS #
RAD_TO_DEG = 180 / math.pi
DEG_TO_RAD = math.pi / 180

def distance_from_points(
    loc1: Tuple[float, float],
    loc2: Tuple[float, float]
) -> float:
    """
    Find the straight line distance between two points assuming flat ground.

    Coordinates in degrees.

    Returns distance in meters.
    """
    earth_radius_meters = 6_378_137

    dlat_rad = (loc2[0] - loc1[0]) * DEG_TO_RAD
    dlon_rad = (loc2[1] - loc1[1]) * DEG_TO_RAD

    lat1_rad, lon1_rad = loc1[0] * DEG_TO_RAD, loc1[1] * DEG_TO_RAD
    lat2_rad, lon2_rad = loc2[0] * DEG_TO_RAD, loc2[1] * DEG_TO_RAD

    a = math.sin(dlat_rad / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon_rad / 2)**2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius_meters * c

def horizontal_angle_from_points(
    loc1: Tuple[float, float],
    loc2: Tuple[float, float]
) -> float:
    """
    Find the straight line distance between two points assuming flat ground.

    Coordinates in degrees.

    Returns horizontal angle (bearing) in degrees.
    """
    y = math.sin(loc2[1] - loc1[1]) * math.cos(loc2[0]);
    x = math.cos(loc1[0]) * math.sin(loc2[0]) - math.sin(loc1[0]) * math.cos(loc2[0]) * math.cos(loc1[1] - loc1[1]);
    angle = math.atan2(y, x);
    bearing = (angle * 180 / math.pi + 360) % 360; # in degrees

    return bearing

def angles_from_points(
    ground_position: Tuple[float, Tuple[float, float]],
    air_position: Tuple[float, Tuple[float, float]]
) -> Tuple[float, float]:
    """
    Calculates the vertical angle from 1 -> 2 from 2 points in space
    Altitude in meters
    GPS coords in degrees
    """

    # Distance in meters, and horizontal angle (azimuth)
    horizontal_distance = distance_from_points(ground_position[1], air_position[1])

    if horizontal_distance == 0:
        return (0.0, 0.0)

    # Altitude difference in meters
    altitude_delta = air_position[0] - ground_position[0]

    # Vertical angle (altitude)
    vertical_angle = math.atan(altitude_delta / horizontal_distance) * RAD_TO_DEG
    horizontal_angle = horizontal_angle_from_points(ground_position[1], air_position[1])

    return horizontal_angle, vertical_angle

def m_to_ft(meters: float) -> float:
    """ Helper function to convert meters to feet, mainly for display """
    return meters / 0.3048

def main():
    ground_position = (1381, (32.940058, -106.921903))
    air_position    = (4429, (32.940907, -106.911671))

    # Straight line distance between the ground positions
    distance = distance_from_points(ground_position[1], air_position[1])

    # Altitude above ground station position
    altitude = air_position[0] - ground_position[0]

    horiz, vert = angles_from_points(ground_position, air_position)

    print(f"  Distance: {distance:.2f}m, {m_to_ft(distance):.2f}ft")
    print(f"  Altitude: {altitude:.2f}m, {m_to_ft(altitude):.2f}ft")
    print(f"Horizontal: {horiz:.2f}° (degrees from North)")
    print(f"  Vertical: {vert:.2f}° (degrees above horizon)")

if __name__ == "__main__":
    main()
