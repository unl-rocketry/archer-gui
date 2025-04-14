import serial

class Rotator():
    """ A rotator, utilizing the protocol specified here:
     https://github.com/unl-rocketry/tracker-embedded/blob/main-rust/PROTOCOL.md """


    def __init__(self, port: str, baud: int = 115200):
        # The default timeout here is 2 seconds, is that good?
        self.main_port = serial.Serial(port, baud, timeout = 2)


    def set_position_vertical(self, pos: float):
        self.main_port.write("DVER {}\n".format(pos).encode())
        self.main_port.flush()


    def set_position_horizontal(self, pos: float):
        self.main_port.write("DHOR {}\n".format(-pos).encode())
        self.main_port.flush()


    def calibrate_vertical(self, set = False):
        """ Begin vertical calibration. This function blocks until calibration
        has finished, which can take a very long time"""
        if set:
            self.main_port.write(b"CALV SET\n")
            self.main_port.flush()
        else:
            self.main_port.write(b"CALV\n")
            self.main_port.flush()


    def calibrate_horizontal(self):
        self.main_port.write(b"CALH\n")
        self.main_port.flush()


    def move_vertical(self, steps: int):
        self.main_port.write("MOVV {}\n".format(steps).encode())
        self.main_port.flush()


    def move_horizontal(self, steps: int):
        self.main_port.write("MOVH {}\n".format(steps).encode())
        self.main_port.flush()


    def position(self) -> tuple[float, float]:
        self.__dump_input()
        self.main_port.write(b"GETP\n")

        self.main_port.readline()
        result = self.main_port.readline().split()

        if len(result) < 3:
            return (0.0, 0.0)

        return (float(result[1]), float(result[2]))

    def __dump_input(self):
        self.main_port.reset_input_buffer()






