from collections import deque

class FifteenMinuteAggregator:
    """Buffers meter reads and aggregates to 15-minute intervals"""

    def __init__(self, log_interval=900):
        self.log_interval = log_interval  # 900 seconds = 15 minutes
        self.buffer = deque()
        self.last_log_time = None

    def add_reading(self, reading, timestamp):
        """Add a reading to the buffer"""
        self.buffer.append((timestamp, reading))

        # Initialize on first reading
        if self.last_log_time is None:
            self.last_log_time = timestamp

    def should_log(self, current_time):
        """Check if it's time to log aggregated data"""
        if self.last_log_time is None:
            return False

        return (current_time - self.last_log_time) >= self.log_interval

    def get_aggregated(self, calc_energy_state):
        """
        Aggregate buffered readings into a single log entry.

        For 15-minute window:
        - Voltage, Current, PF, Freq: Average
        - Power: Average
        - Energy (calc): Use final values from EnergyCalc
        - Energy (meter): Use final value from meter
        """
        if not self.buffer:
            return None

        # Extract all readings
        readings = [r for _, r in self.buffer]

        # Average numerical fields (skip None values for single-phase)
        def avg_field(field_name):
            values = [r[field_name] for r in readings if r.get(field_name) is not None]
            if not values:
                return None
            avg = sum(values) / len(values)
            return round(avg, 3)  # Round to 3 decimal places

        aggregated = {
            'V_L1': avg_field('V_L1'),
            'V_L2': avg_field('V_L2'),
            'V_L3': avg_field('V_L3'),
            'I_L1': avg_field('I_L1'),
            'I_L2': avg_field('I_L2'),
            'I_L3': avg_field('I_L3'),
            'P_total': avg_field('P_total'),
            'P_L1': avg_field('P_L1'),
            'P_L2': avg_field('P_L2'),
            'P_L3': avg_field('P_L3'),
            'PF_total': avg_field('PF_total'),
            'frequency': avg_field('frequency'),
            'energy_total': round(readings[-1]['energy_total'], 3),  # Round final meter reading
        }

        # Add calculated energy from EnergyCalc state
        aggregated.update({
            'E_L1_cal': calc_energy_state.get('E_L1_cal', 0),
            'E_L2_cal': calc_energy_state.get('E_L2_cal'),
            'E_L3_cal': calc_energy_state.get('E_L3_cal'),
        })

        return aggregated

    def clear_buffer(self, new_log_time):
        """Clear buffer after logging"""
        self.buffer.clear()
        self.last_log_time = new_log_time
