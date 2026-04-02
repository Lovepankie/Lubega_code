import subprocess
import re

class MBPollClient:
    def __init__(self, port):
        self.port = port

    def _run(self, cmd):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return None
            return result.stdout
        except:
            return None

    def _parse(self, output):
        matches = re.findall(r"\[\d+\]:\s+([-\d\.eE]+)", output)
        return [float(v) for v in matches] if matches else None

    def read_input_float(self, address, count, slave):
        cmd = [
            "mbpoll", "-m", "rtu", "-b", "9600", "-P", "none", "-s", "2",
            "-t", "3:float", "-B", "-0",
            "-r", hex(address), "-c", str(count),
            self.port, "-a", str(slave), "-1"
        ]
        out = self._run(cmd)
        return self._parse(out) if out else None

    def read_holding_float(self, address, count, slave):
        cmd = [
            "mbpoll", "-m", "rtu", "-b", "9600", "-P", "none", "-s", "2",
            "-t", "4:float", "-B", "-0",
            "-r", hex(address), "-c", str(count),
            self.port, "-a", str(slave), "-1"
        ]
        out = self._run(cmd)
        return self._parse(out) if out else None