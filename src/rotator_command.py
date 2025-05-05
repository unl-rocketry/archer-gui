from typing import Optional
import customtkinter


## LOCAL IMPORTS ##
from rotator import MovementCommand as mvc, Rotator
###################

class RotatorCommandWindow(customtkinter.CTkToplevel):
    def __init__(self, rotator: Optional[Rotator]):
        super().__init__()

        self.title("Rotator Commands")
        #self.geometry(str(self.WIDTH) + "x" + str(self.HEIGHT))
        #self.minsize(self.WIDTH, self.HEIGHT)

        self.rotator = rotator

        customtkinter.CTkLabel(self, text="Calibrate:", anchor="w", font=("Noto Sans", 18)).grid(pady=(0, 5))

        self.frame_top = customtkinter.CTkFrame(master=self, corner_radius=0, fg_color="transparent")
        self.frame_top.grid(sticky="nsew", ipady=10)
        self.frame_top.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.calv_button = customtkinter.CTkButton(self.frame_top, text="Vertical", width=100, command=self.calibrate_vertical)
        self.calv_button.grid(pady=10, padx=20, row=0, column=0, sticky="w")
        self.calv_set_button = customtkinter.CTkButton(self.frame_top, text="Set", width=100, command=self.calibrate_vertical(True))
        self.calv_set_button.grid(pady=10, padx=20, row=0, column=1, sticky="w")
        self.calh_button = customtkinter.CTkButton(self.frame_top, text="Horizontal", width=100, command=self.calibrate_horizontal)
        self.calh_button.grid(pady=10, padx=70, row=1, columnspan=2, sticky="ew")

        customtkinter.CTkLabel(self, text="Controls:", anchor="w", font=("Noto Sans", 18)).grid(pady=(0, 5))

        self.f_ctrl = customtkinter.CTkFrame(master=self, corner_radius=0)
        self.f_ctrl.grid(sticky="nsew", ipadx=10, ipady=10)
        self.f_ctrl.grid_columnconfigure(0, weight=1)
        self.f_ctrl.grid_columnconfigure(1, weight=1)
        self.f_ctrl.grid_columnconfigure(2, weight=1)
        self.f_ctrl.grid_columnconfigure(3, weight=1)
        self.f_ctrl.grid_rowconfigure(0, weight=1)
        self.f_ctrl.grid_rowconfigure(4, weight=1)

        self.up_button = customtkinter.CTkButton(self.f_ctrl, text="UP", width=50, command=lambda : self.movc([mvc.UP]))
        self.up_button.grid(column=1, row=1, padx=5, pady=5, sticky="ew")
        self.left_button = customtkinter.CTkButton(self.f_ctrl, text="LEFT", width=50, command=lambda : self.movc([mvc.LEFT]))
        self.left_button.grid(column=0, row=2, padx=10, pady=5, sticky="ew")
        self.right_button = customtkinter.CTkButton(self.f_ctrl, text="RIGHT", width=50, command=lambda : self.movc([mvc.RIGHT]))
        self.right_button.grid(column=2, row=2, padx=10, pady=5, sticky="ew")
        self.down_button = customtkinter.CTkButton(self.f_ctrl, text="DOWN", width=50, command=lambda : self.movc([mvc.DOWN]))
        self.down_button.grid(column=1, row=3, padx=5, pady=5, sticky="ew")

        self.down_button = customtkinter.CTkButton(self.f_ctrl, text="STOP", width=50, command=lambda : self.movc([mvc.STOP_VERTICAL, mvc.STOP_HORIZONTAL]))
        self.down_button.grid(column=1, row=2, padx=5, pady=5, sticky="ew")

    def calibrate_vertical(self, Set: Optional[bool] = False):
        if self.rotator is not None:
            if Set:
                self.rotator.calibrate_vertical(Set)
            else:
                self.rotator.calibrate_vertical()


    def calibrate_horizontal(self):
        if self.rotator is not None:
            self.rotator.calibrate_horizontal()

    def movc(self, commands: list[mvc]):
        if self.rotator is not None:
            for command in commands:
                self.rotator.move(command)
