import serial
import sys

import utils


def main(arguments: list[str]):
    if len(arguments) < 2:
        print("Not enough arguments! Need: <serial port> <command value>")
        return

    try:
        gps_serial = serial.Serial(
            arguments[0],
            57600,
            timeout=1
        )
    except IOError as e:
        print(f"Failed to start GPS loop: {e}")
        return

    command: int = int(arguments[1])
    calculated_crc = utils.crc8(bytes([command]))

    gps_serial.write(bytes([command, calculated_crc, 0x20]))


if __name__ == "__main__":
    main(sys.argv[1:])
