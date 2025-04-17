from typing import Optional
import serial

class RotatorException(BaseException):
    """ Base class for exceptions raised by the rotator. """


class RotatorInvalidResponse(RotatorException):
    """ A response from the rotator was invalid or did not meet expectations. """


class Rotator():
    """ A two-axis rotator, utilizing the protocol specified here:
    https://github.com/unl-rocketry/tracker-embedded/blob/main-rust/PROTOCOL.md """


    def __init__(self, port: str, baud: int = 115200):
        # The default timeout here is 2 seconds, is that good?
        self.main_port = serial.Serial(port, baud, timeout = 2)

        self.protocol_version = self.version()


    def set_position(self, pos: tuple[float, float]):
        """ Position in degrees to move to in both the vertical and horizontal axes. """
        self.set_position_vertical(pos[0])
        self.set_position_horizontal(pos[1])


    def set_position_vertical(self, pos: float):
        """ Position in degrees to move to in the vertical axis. """
        self.main_port.write(f"DVER {pos}\n".encode())
        self.__validate_parse()


    def set_position_horizontal(self, pos: float):
        """ Position in degrees to move to in the horizontal axis. """
        self.main_port.write(f"DHOR {-pos}\n".encode())
        self.__validate_parse()


    def calibrate_vertical(self, set: Optional[bool] = False):
        """ Calibrate vertical axis. """
        if set:
            self.main_port.write(b"CALV SET\n")
        else:
            self.main_port.write(b"CALV\n")
        self.__validate_parse()


    def calibrate_horizontal(self):
        """ Calibrate horizontal axis. """
        self.main_port.write(b"CALH\n")
        self.__validate_parse()


    def move_vertical(self, steps: int):
        """ Moves by the specified number of steps in the vertical axis. """
        self.main_port.write(f"MOVV {steps}\n".encode())
        self.__validate_parse()


    def move_horizontal(self, steps: int):
        """ Moves by the specified number of steps in the horizontal axis. """
        self.main_port.write(f"MOVH {steps}\n".encode())
        self.__validate_parse()


    def position(self) -> tuple[float, float]:
        """ Gets the current position for both the vertical and horizontal axes. """
        self.main_port.write(b"GETP\n")
        result = self.__validate_parse(2)

        return (float(result[0]), float(result[1]))


    def version(self) -> str:
        """ Gets the version of the protocol in use. """
        self.main_port.write(b"VERS\n")
        result = self.__validate_parse(1)
        return result[0]


    def __validate_parse(self, count_expected: Optional[int] = None) -> list:
        _echo = self.main_port.readline() # We can also verify this at some point
        response = self.main_port.readline().decode("UTF-8") # Read response info

        response_list = response.split()

        if response_list[0] == "ERR":
            raise RotatorException
        elif response_list[0] == "OK":
            pass
        else:
            raise RotatorInvalidResponse

        response_list.pop(0)

        if count_expected is not None and len(response_list) != count_expected:
            raise RotatorInvalidResponse

        return response_list


    def __dump_input(self):
        self.main_port.reset_input_buffer()
