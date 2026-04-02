class EnergyCalc:
    def __init__(self, state, phase_count=3):
        """
        phase_count: 1 for single-phase, 3 for three-phase
        """
        self.phase_count = phase_count

        if phase_count == 3:
            self.E_L1_cal = state.get("E_L1_cal", 0)
            self.E_L2_cal = state.get("E_L2_cal", 0)
            self.E_L3_cal = state.get("E_L3_cal", 0)
            self.last_p = state.get("last_p", [0, 0, 0])
        else:  # Single phase
            self.E_L1_cal = state.get("E_L1_cal", 0)
            self.E_L2_cal = None
            self.E_L3_cal = None
            self.last_p = state.get("last_p", [0])

        self.last_time = state.get("last_time", None)

    def update(self, powers, now):
        """
        powers: list of power values [P_L1] or [P_L1, P_L2, P_L3]
        """
        if self.last_time is None:
            self.last_time = now
            self.last_p = powers
            return

        dt = (now - self.last_time) / 3600.0
        dt = min(dt, 30/3600)  # safety cap

        self.E_L1_cal += (self.last_p[0] + powers[0])/2 * dt

        if self.phase_count == 3:
            self.E_L2_cal += (self.last_p[1] + powers[1])/2 * dt
            self.E_L3_cal += (self.last_p[2] + powers[2])/2 * dt

        self.last_time = now
        self.last_p = powers

    def state(self):
        if self.phase_count == 3:
            return {
                "E_L1_cal": self.E_L1_cal,
                "E_L2_cal": self.E_L2_cal,
                "E_L3_cal": self.E_L3_cal,
                "last_time": self.last_time,
                "last_p": self.last_p
            }
        else:
            return {
                "E_L1_cal": self.E_L1_cal,
                "last_time": self.last_time,
                "last_p": self.last_p
            }