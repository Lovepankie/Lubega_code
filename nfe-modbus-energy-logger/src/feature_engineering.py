import pickle
from pathlib import Path

_FEATURES_PATH = Path(__file__).parent.parent / "model" / "features.pkl"

def engineer_features(row) -> dict:
    """Return a dict of all 20 model features from one aggregated CSV row."""
    i_l1, i_l2, i_l3 = float(row['i_l1']), float(row['i_l2']), float(row['i_l3'])
    v_l1, v_l2, v_l3 = float(row['v_l1']), float(row['v_l2']), float(row['v_l3'])
    i_total = i_l1 + i_l2 + i_l3

    return {
        # raw (9)
        'i_l1':      i_l1,
        'i_l2':      i_l2,
        'i_l3':      i_l3,
        'v_l1':      v_l1,
        'v_l2':      v_l2,
        'v_l3':      v_l3,
        'p_total':   float(row['p_total']),
        'pf_total':  float(row['pf_total']),
        'frequency': float(row['frequency']),
        # engineered (11)
        'i_imbalance': max(i_l1, i_l2, i_l3) - min(i_l1, i_l2, i_l3),
        'v_imbalance': max(v_l1, v_l2, v_l3) - min(v_l1, v_l2, v_l3),
        'i_l1_zero':   1 if i_l1 < 0.01 else 0,
        'i_l2_zero':   1 if i_l2 < 0.01 else 0,
        'i_l3_zero':   1 if i_l3 < 0.01 else 0,
        'v_l1_zero':   1 if v_l1 < 10 else 0,
        'v_l2_zero':   1 if v_l2 < 10 else 0,
        'v_l3_zero':   1 if v_l3 < 10 else 0,
        'pf_zero':     1 if float(row['pf_total']) < 0.05 else 0,
        'i_total':     i_total,
        'p_per_i':     float(row['p_total']) / (i_total + 0.001),
    }


def verify_features(feat_dict: dict) -> bool:
    """Check that feat_dict keys exactly match the trained model's feature list."""
    with open(_FEATURES_PATH, 'rb') as f:
        expected = pickle.load(f)
    missing = [k for k in expected if k not in feat_dict]
    extra   = [k for k in feat_dict if k not in expected]
    if missing or extra:
        raise ValueError(f"Feature mismatch — missing: {missing}, extra: {extra}")
    return True


if __name__ == '__main__':
    import pandas as pd
    from pathlib import Path

    # Quick smoke test: load first CSV in docs/ and print features
    csv_files = sorted(Path(__file__).parent.parent.parent.glob('docs/*.csv'))
    if not csv_files:
        csv_files = sorted(Path(__file__).parent.parent.glob('**/*.csv'))

    if not csv_files:
        print("No CSV found to test with.")
    else:
        df = pd.read_csv(csv_files[0])
        row = df.iloc[0]
        features = engineer_features(row)
        print(f"Testing with: {csv_files[0].name}")
        print(f"Feature count: {len(features)}")
        for k, v in features.items():
            print(f"  {k:20s} = {v}")
        verify_features(features)
        print("\nAll 20 features present and verified against features.pkl.")
