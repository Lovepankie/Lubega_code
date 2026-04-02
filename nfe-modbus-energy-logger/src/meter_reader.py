class BaseMeterReader:
    """Base class for meter-specific reading logic"""

    def __init__(self, meter_id, meter_name):
        self.meter_id = meter_id
        self.meter_name = meter_name

    def read(self, client):
        """Read all registers for this meter type"""
        raise NotImplementedError


class ThreePhaseMeterReader(BaseMeterReader):
    """Three-phase meter (current implementation)"""

    REGISTERS = {
        'voltage': (0x2006, 3),      # 3 phases
        'current': (0x200C, 3),      # 3 phases
        'power': (0x2012, 4),        # total + 3 phases
        'power_factor': (0x2020, 1),
        'frequency': (0x2044, 1),
        'energy': (0x4000, 1)
    }

    def read(self, client):
        V = client.read_input_float(0x2006, 3, self.meter_id)
        I = client.read_input_float(0x200C, 3, self.meter_id)
        P = client.read_input_float(0x2012, 4, self.meter_id)
        PF = client.read_input_float(0x2020, 1, self.meter_id)
        F = client.read_input_float(0x2044, 1, self.meter_id)
        E = client.read_input_float(0x4000, 1, self.meter_id)

        if not all([V, I, P, PF, F, E]):
            return None

        # Three-phase DTSU666 scaling: V /10, I,F /100, P,PF /1000, E no scaling
        # IEEE 754 floats store scaled integers (e.g., 2309.0 → 230.9V)
        return {
            'V_L1': round(V[0]/10, 3), 'V_L2': round(V[1]/10, 3), 'V_L3': round(V[2]/10, 3),
            'I_L1': round(I[0]/100, 3), 'I_L2': round(I[1]/100, 3), 'I_L3': round(I[2]/100, 3),
            'P_total': round(P[0]/1000, 3), 'P_L1': round(P[1]/1000, 3), 'P_L2': round(P[2]/1000, 3), 'P_L3': round(P[3]/1000, 3),
            'PF_total': round(PF[0]/1000, 3),
            'frequency': round(F[0]/100, 3),
            'energy_total': round(E[0], 3),
            'phases': [round(P[1]/1000, 3), round(P[2]/1000, 3), round(P[3]/1000, 3)]  # For energy calc
        }


class SinglePhaseMeterReader(BaseMeterReader):
    """Single-phase DDSU666 meter (from manual)

    Note: Single-phase meters don't need calculated energy since
    the meter's cumulative energy (energy_total) is already accurate.
    """

    REGISTERS = {
        'voltage': (0x2000, 1),      # Single phase
        'current': (0x2002, 1),      # Single phase
        'power': (0x2004, 1),        # Single value
        'power_factor': (0x200A, 1),
        'frequency': (0x200E, 1),
        'energy': (0x4000, 1)
    }

    def read(self, client):
        V = client.read_input_float(0x2000, 1, self.meter_id)
        I = client.read_input_float(0x2002, 1, self.meter_id)
        P = client.read_input_float(0x2004, 1, self.meter_id)
        PF = client.read_input_float(0x200A, 1, self.meter_id)
        F = client.read_input_float(0x200E, 1, self.meter_id)
        E = client.read_input_float(0x4000, 1, self.meter_id)

        if not all([V, I, P, PF, F, E]):
            return None

        # Single-phase DDSU666: Power is already in kW via Modbus (LCD shows W for readability)
        # IEEE 754 floats store actual values (e.g., 230.9V, 0.069kW = 69W on LCD)
        return {
            'V_L1': round(V[0], 3), 'V_L2': None, 'V_L3': None,
            'I_L1': round(I[0], 3), 'I_L2': None, 'I_L3': None,
            'P_total': round(P[0], 3), 'P_L1': round(P[0], 3), 'P_L2': None, 'P_L3': None,  # Already in kW
            'PF_total': round(PF[0], 3),
            'frequency': round(F[0], 3),
            'energy_total': round(E[0], 3),
            'phases': None  # No energy calculation needed for single-phase
        }


def create_meter_reader(meter_config):
    """Factory function"""
    if meter_config['type'] == '3phase':
        return ThreePhaseMeterReader(meter_config['id'], meter_config['name'])
    elif meter_config['type'] == '1phase':
        return SinglePhaseMeterReader(meter_config['id'], meter_config['name'])
    else:
        raise ValueError(f"Unknown meter type: {meter_config['type']}")
