import csv, os

HEADER = [
    "timestamp","meter_id",
    "V_L1","V_L2","V_L3",
    "I_L1","I_L2","I_L3",
    "P_total","P_L1","P_L2","P_L3",
    "PF_total",
    "frequency",
    "energy_total",
    "E_L1_cal","E_L2_cal","E_L3_cal"
]

def log(file, row):
    exists = os.path.isfile(file)

    with open(file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        if not exists:
            writer.writeheader()
        writer.writerow(row)