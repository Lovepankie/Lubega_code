import joblib
from pathlib import Path

_FEATURES_PATH = Path(__file__).parent.parent / "model" / "features.pkl"


def engineer_features(reading: dict) -> dict:
    """Return a dict of all 20 model features from one raw poll reading."""
    I_L1 = float(reading['I_L1'])
    I_L2 = float(reading['I_L2'])
    I_L3 = float(reading['I_L3'])
    V_L1 = float(reading['V_L1'])
    V_L2 = float(reading['V_L2'])
    V_L3 = float(reading['V_L3'])
    I_total = I_L1 + I_L2 + I_L3

    return {
        # raw (9)
        'I_L1':      I_L1,
        'I_L2':      I_L2,
        'I_L3':      I_L3,
        'V_L1':      V_L1,
        'V_L2':      V_L2,
        'V_L3':      V_L3,
        'P_total':   float(reading['P_total']),
        'PF_total':  float(reading['PF_total']),
        'frequency': float(reading['frequency']),
        # engineered (11)
        'I_imbalance': max(I_L1, I_L2, I_L3) - min(I_L1, I_L2, I_L3),
        'V_imbalance': max(V_L1, V_L2, V_L3) - min(V_L1, V_L2, V_L3),
        'I_L1_zero':   1 if I_L1 < 0.01 else 0,
        'I_L2_zero':   1 if I_L2 < 0.01 else 0,
        'I_L3_zero':   1 if I_L3 < 0.01 else 0,
        'V_L1_zero':   1 if V_L1 < 10 else 0,
        'V_L2_zero':   1 if V_L2 < 10 else 0,
        'V_L3_zero':   1 if V_L3 < 10 else 0,
        'PF_zero':     1 if float(reading['PF_total']) < 0.05 else 0,
        'I_total':     I_total,
        'P_per_I':     float(reading['P_total']) / (I_total + 0.001),
    }


def verify_features(feat_dict: dict) -> bool:
    """Check that feat_dict keys exactly match the trained model's feature list."""
    expected = joblib.load(_FEATURES_PATH)
    missing = [k for k in expected if k not in feat_dict]
    extra   = [k for k in feat_dict if k not in expected]
    if missing or extra:
        raise ValueError(f"Feature mismatch — missing: {missing}, extra: {extra}")
    return True
