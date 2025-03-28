import serial

class Rotator():
    """ A rotator, utilizing the protocol specified here:
     https://github.com/unl-rocketry/tracker-embedded/blob/main-rust/PROTOCOL.md """

    def __init__(self, port: str, baud: int = 115200):
        # The default timeout here is 2 seconds, is that good?
        self.main_port = serial.Serial(port, baud, timeout = 2)
