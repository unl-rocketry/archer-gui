import serial

class Rotator():
    """ A rotator, utilizing the protocol specified here:
     https://github.com/unl-rocketry/tracker-embedded/blob/main-rust/PROTOCOL.md """


    def __init__(self, port: str, baud: int = 115200):
        # The default timeout here is 2 seconds, is that good?
        self.main_port = serial.Serial(port, baud, timeout = 2)


    def set_position_vertical(self, pos: float):
        self.main_port.write("DVER {}\n".format(pos).encode())

        result = self.main_port.readline()
        if result.startswith(b"OK"):
            raise

    def set_position_horizontal(self, pos: float):
        self.main_port.write("DHOR {}\n".format(pos).encode())

        result = self.main_port.readline()
        if result.startswith(b"OK"):
            raise

    def calibrate_vertical(self, set = False):
        """ Begin vertical calibration. This function blocks until calibration
        has finished, which can take a very long time"""
        if set:
            self.main_port.write(b"CALV SET\n")
        else:
            self.main_port.write(b"CALV\n")

        result = self.main_port.readline()
        if result.startswith(b"OK"):
            raise

    def calibrate_horizontal(self):
        self.main_port.write(b"CALH\n")

        result = self.main_port.readline()
        if result.startswith(b"OK"):
            raise

    def move_vertical(self, steps: int):
        self.main_port.write("MOVV {}\n".format(steps).encode())

        result = self.main_port.readline()
        if result.startswith(b"OK"):
            raise

    def move_horizontal(self, steps: int):
        self.main_port.write("MOVH {}\n".format(steps).encode())

        result = self.main_port.readline()
        if result.startswith(b"OK"):
            raise

    def position(self) -> tuple[float, float]:
        self.main_port.write(b"GETP\n")

        result = self.main_port.readline().split()
        if result[0] != b"OK":
            raise

        return (float(result[1]), float(result[2]))






