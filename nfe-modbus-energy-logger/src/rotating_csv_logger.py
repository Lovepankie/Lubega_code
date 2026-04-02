import csv
import os
import gzip
from datetime import datetime

class RotatingCSVLogger:
    """Per-meter CSV logger with automatic rotation"""

    HEADER_3PHASE = [
        "timestamp", "meter_id", "meter_name",
        "V_L1_V", "V_L2_V", "V_L3_V",
        "I_L1_A", "I_L2_A", "I_L3_A",
        "P_total_kW", "P_L1_kW", "P_L2_kW", "P_L3_kW",
        "PF_total", "frequency_Hz",
        "energy_total_kWh",
        "E_L1_cal_kWh", "E_L2_cal_kWh", "E_L3_cal_kWh",
        "billing_marker"
    ]

    HEADER_1PHASE = [
        "timestamp", "meter_id", "meter_name",
        "V_L1_V", "I_L1_A",
        "P_total_kW", "P_L1_kW",
        "PF_total", "frequency_Hz",
        "energy_total_kWh",
        "billing_marker"
        # Note: No E_L1_cal for single-phase - meter's cumulative energy is sufficient
    ]

    def __init__(self, meter_id, meter_name, meter_type, base_dir, max_rows=50000, compress=True, log_calculated_energy=True):
        self.meter_id = meter_id
        self.meter_name = meter_name
        self.meter_type = meter_type
        self.base_dir = base_dir
        self.max_rows = max_rows
        self.compress = compress
        self.log_calculated_energy = log_calculated_energy

        # Create meter-specific directory
        self.meter_dir = os.path.join(base_dir, f"meter_{meter_id:03d}")
        os.makedirs(self.meter_dir, exist_ok=True)

        self.current_file = None
        self.current_row_count = 0

        # Choose header based on meter type
        self.header = self.HEADER_3PHASE if meter_type == '3phase' else self.HEADER_1PHASE

        # Resume latest file on startup
        self._resume_latest_file()

    def _get_filename(self, timestamp=None):
        """Generate filename with timestamp"""
        if timestamp is None:
            timestamp = datetime.now()
        date_str = timestamp.strftime("%Y-%m-%d")
        return os.path.join(self.meter_dir, f"meter_{self.meter_id:03d}_{date_str}.csv")

    def _resume_latest_file(self):
        """Find and resume the most recent CSV file on startup"""
        import glob
        pattern = os.path.join(self.meter_dir, f"meter_{self.meter_id:03d}_*.csv")
        existing_files = glob.glob(pattern)

        if existing_files:
            # Get the most recent file (by modification time)
            latest_file = max(existing_files, key=os.path.getmtime)

            # Check if existing file has correct schema (schema versioning)
            with open(latest_file, 'r') as f:
                first_line = f.readline().strip()
                existing_header = first_line.split(',')

            if existing_header != self.header:
                print(f"⚠️  Schema mismatch detected in {latest_file}")
                print(f"   Expected: {len(self.header)} columns, Found: {len(existing_header)} columns")
                print(f"   Forcing rotation to new file with updated schema")
                # Force rotation by setting current file to None
                self.current_file = None
                self.current_row_count = 0
                return  # Skip resuming old file

            # Count rows in the file
            with open(latest_file, 'r') as f:
                row_count = sum(1 for _ in f) - 1  # -1 for header

            # Always resume the latest file, regardless of row count
            self.current_file = latest_file
            self.current_row_count = row_count
            print(f"📂 Resuming {latest_file} ({row_count}/{self.max_rows} rows)")

            # If file has reached max rows, it will rotate on next log() call
            if row_count >= self.max_rows:
                print(f"⚠️  File has reached max rows, will rotate on next write")

    def _rotate_if_needed(self):
        """Check if rotation is needed and perform it"""
        if self.current_file and self.current_row_count >= self.max_rows:
            # Close current file
            print(f"🔄 Rotating log for meter {self.meter_id} (reached {self.max_rows} rows)")

            # Compress old file if enabled
            if self.compress:
                self._compress_file(self.current_file)

            # Reset for new file
            self.current_file = None
            self.current_row_count = 0

    def _compress_file(self, filepath):
        """Compress a CSV file with gzip"""
        if not os.path.exists(filepath):
            return

        gz_path = filepath + '.gz'
        with open(filepath, 'rb') as f_in:
            with gzip.open(gz_path, 'wb') as f_out:
                f_out.writelines(f_in)

        # Remove original file after compression
        os.remove(filepath)
        print(f"✅ Compressed {filepath} → {gz_path}")

    def log(self, row):
        """Write a row to the CSV (with rotation)"""
        self._rotate_if_needed()

        # If no current file, check if today's file exists first
        if self.current_file is None:
            today_file = self._get_filename()

            # If today's file already exists, resume it
            if os.path.isfile(today_file):
                with open(today_file, 'r') as f:
                    row_count = sum(1 for _ in f) - 1  # -1 for header
                self.current_file = today_file
                self.current_row_count = row_count
                print(f"📂 Resuming today's file: {today_file} ({row_count} rows)")
            else:
                # Create new file for today
                self.current_file = today_file
                self.current_row_count = 0

        # Check if file exists to determine if header is needed
        exists = os.path.isfile(self.current_file)

        # Add meter identification to row
        row_with_meta = {
            'timestamp': row['timestamp'],
            'meter_id': self.meter_id,
            'meter_name': self.meter_name,
            **{k: v for k, v in row.items() if k != 'timestamp'}
        }

        # Map data keys to header keys with units
        key_mapping = {
            'V_L1': 'V_L1_V', 'V_L2': 'V_L2_V', 'V_L3': 'V_L3_V',
            'I_L1': 'I_L1_A', 'I_L2': 'I_L2_A', 'I_L3': 'I_L3_A',
            'P_total': 'P_total_kW', 'P_L1': 'P_L1_kW', 'P_L2': 'P_L2_kW', 'P_L3': 'P_L3_kW',
            'frequency': 'frequency_Hz',
            'energy_total': 'energy_total_kWh',
            'E_L1_cal': 'E_L1_cal_kWh', 'E_L2_cal': 'E_L2_cal_kWh', 'E_L3_cal': 'E_L3_cal_kWh'
        }

        # Rename keys to match headers
        mapped_row = {}
        for key, value in row_with_meta.items():
            new_key = key_mapping.get(key, key)  # Use mapped key if exists, otherwise keep original
            mapped_row[new_key] = value

        # Clear calculated energy columns if flag is disabled (only for 3-phase meters)
        if self.meter_type == '3phase' and not self.log_calculated_energy:
            mapped_row['E_L1_cal_kWh'] = ''
            mapped_row['E_L2_cal_kWh'] = ''
            mapped_row['E_L3_cal_kWh'] = ''

        # Format numeric values to 3 decimal places (preserves trailing zeros in CSV)
        formatted_row = {}
        for key, value in mapped_row.items():
            if isinstance(value, (int, float)) and value is not None and key != 'meter_id':
                formatted_row[key] = f"{value:.3f}"
            else:
                formatted_row[key] = value

        # Write to CSV
        with open(self.current_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.header, extrasaction='ignore')
            if not exists:
                writer.writeheader()
            writer.writerow(formatted_row)

        self.current_row_count += 1
