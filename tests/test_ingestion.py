import pandas as pd
import pytest
import io
from moffit.ingestion.paysim_loader import PaySimLoader

# 50-row inline fixture representing PaySim CSV data
csv_data = """step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,isFraud,isFlaggedFraud
2,PAYMENT,7418.09,C1003,4541.89,-2876.2,M2001,6766.99,6766.99,0,0
10,DEBIT,327.51,C1001,4450.9,4778.41,M2008,6020.19,6020.19,0,0
9,DEBIT,2212.2,C1009,5636.0,7848.2,M2000,7588.07,7588.07,0,0
3,DEBIT,3409.1,C1002,4384.74,7793.84,M2005,1022.1,1022.1,0,0
7,PAYMENT,3596.2,C1005,12114.15,8517.95,M2000,7297.32,7297.32,0,0
9,PAYMENT,9731.43,C1006,1668.12,-8063.31,M2004,8294.05,8294.05,0,0
10,CASH_OUT,5777.75,C1001,1011.91,-4765.84,M2003,7730.68,13508.43,0,0
2,TRANSFER,8666.17,C1006,5631.67,-3034.5,M2010,8341.1,17007.27,0,0
3,CASH_OUT,3559.15,C1010,5412.86,1853.71,M2010,6480.35,10039.5,0,0
10,TRANSFER,5346.06,C1003,3351.71,-1994.35,M2006,2699.48,8045.54,0,0
9,TRANSFER,6849.3,C1000,4658.06,-2191.24,M2000,8050.46,14899.76,0,0
7,CASH_OUT,671.22,C1009,17539.72,16868.5,M2005,2126.27,2797.49,0,0
8,DEBIT,8847.98,C1010,9231.15,18079.13,M2004,1396.3,1396.3,0,0
9,CASH_IN,2634.79,C1009,8625.83,11260.62,M2009,3994.01,3994.01,0,0
4,TRANSFER,5100.17,C1001,15140.06,10039.89,M2001,1528.41,6628.58,0,0
3,DEBIT,5968.13,C1006,7694.22,13662.35,M2007,5291.14,5291.14,0,0
9,PAYMENT,6806.03,C1001,13666.04,6860.01,M2008,7508.78,7508.78,0,0
6,PAYMENT,2942.07,C1002,9129.1,6187.03,M2004,9718.88,9718.88,0,0
3,CASH_IN,9127.15,C1010,6039.05,15166.2,M2010,5076.63,5076.63,0,0
4,TRANSFER,3745.4,C1002,10833.64,7088.24,M2008,9184.93,12930.33,0,0
10,CASH_OUT,4891.17,C1001,18589.06,13697.89,M2004,2394.52,7285.69,0,0
4,CASH_IN,9470.02,C1001,14664.96,24134.98,M2001,9779.84,9779.84,0,0
9,TRANSFER,1292.63,C1007,18942.29,17649.66,M2002,2650.57,3943.20,0,0
10,DEBIT,9643.99,C1008,15129.78,24773.77,M2003,7129.49,7129.49,0,0
7,CASH_OUT,4386.62,C1008,9084.57,4697.95,M2003,2246.97,6633.59,0,0
6,PAYMENT,5887.2,C1003,11809.96,5922.76,M2000,709.93,709.93,0,0
1,TRANSFER,683.33,C1000,17206.74,16523.41,M2001,5141.56,5824.89,0,0
5,DEBIT,2150.23,C1002,14494.72,16644.95,M2009,5762.12,5762.12,0,0
4,DEBIT,8076.9,C1003,1977.08,10053.98,M2010,4310.51,4310.51,0,0
7,DEBIT,4675.58,C1000,13499.95,18175.53,M2010,984.18,984.18,0,0
7,CASH_OUT,8007.92,C1001,5048.26,-2959.66,M2003,5362.86,13370.78,0,0
3,DEBIT,1843.05,C1007,5071.15,6914.2,M2001,4431.31,4431.31,0,0
9,PAYMENT,515.38,C1008,16736.95,16221.57,M2001,9263.67,9263.67,0,0
4,TRANSFER,4070.08,C1007,4353.57,283.49,M2006,9024.43,13094.51,0,0
3,DEBIT,31.53,C1006,5377.54,5409.07,M2007,2852.49,2852.49,0,0
9,DEBIT,1556.42,C1004,4432.25,5988.67,M2000,5791.8,5791.8,0,0
9,PAYMENT,7482.28,C1000,1097.83,-6384.45,M2007,5028.5,5028.5,0,0
9,TRANSFER,578.23,C1008,1694.22,1115.99,M2002,685.21,1263.44,0,0
2,TRANSFER,4043.72,C1009,4999.69,955.97,M2009,397.42,4441.14,0,0
2,DEBIT,6577.16,C1009,10503.38,17080.54,M2004,2042.59,2042.59,0,0
6,TRANSFER,2663.49,C1002,13466.64,10803.15,M2004,4572.25,7235.74,0,0
2,PAYMENT,4588.27,C1009,19922.32,15334.05,M2001,5376.34,5376.34,0,0
9,CASH_OUT,1333.24,C1005,17629.2,16295.96,M2003,3695.27,5028.51,0,0
3,DEBIT,8339.11,C1004,12272.39,20611.5,M2010,5289.41,5289.41,0,0
9,CASH_OUT,9318.24,C1001,18784.71,9466.47,M2002,2644.66,11962.9,0,0
2,CASH_IN,1562.92,C1004,12136.11,13699.03,M2005,2035.97,2035.97,0,0
5,CASH_IN,4890.43,C1000,1936.74,6827.17,M2006,8293.48,8293.48,0,0
1,PAYMENT,3342.23,C1002,12778.56,9436.33,M2004,1615.82,1615.82,0,0
8,CASH_IN,7059.62,C1008,292.43,7352.05,M2001,9450.51,9450.51,0,0
3,CASH_IN,369.92,C1005,11691.94,12061.86,M2002,4297.87,4297.87,0,0
"""

@pytest.fixture
def sample_csv_file(tmp_path):
    file_path = tmp_path / "paysim_sample.csv"
    file_path.write_text(csv_data)
    return str(file_path)

@pytest.fixture
def loader():
    return PaySimLoader()

@pytest.fixture
def normalized_df(loader, sample_csv_file):
    raw_df = loader.load_csv(sample_csv_file)
    return loader.normalize(raw_df)

def test_load_csv(loader, sample_csv_file):
    df = loader.load_csv(sample_csv_file)
    assert len(df) == 50
    assert "step" in df.columns
    assert "nameOrig" in df.columns

def test_normalize(loader, sample_csv_file):
    raw_df = loader.load_csv(sample_csv_file)
    df = loader.normalize(raw_df)

    expected_cols = [
        "step", "tx_type", "amount", "sender_id", "sender_balance_before",
        "sender_balance_after", "receiver_id", "receiver_balance_before",
        "receiver_balance_after", "is_fraud", "is_flagged"
    ]
    for col in expected_cols:
        assert col in df.columns

    assert df["step"].dtype == int
    assert df["amount"].dtype == float
    assert df["is_fraud"].dtype == bool

def test_filter_by_account(loader, normalized_df):
    account_id = "C1001"
    filtered_df = loader.filter_by_account(normalized_df, account_id)

    for idx, row in filtered_df.iterrows():
        assert row["sender_id"] == account_id or row["receiver_id"] == account_id

    # Count manually
    count = sum(1 for line in csv_data.strip().split("\n")[1:] if "C1001" in line.split(",")[3] or "C1001" in line.split(",")[6])
    assert len(filtered_df) == count

def test_filter_by_timerange(loader, normalized_df):
    start, end = 3, 5
    filtered_df = loader.filter_by_timerange(normalized_df, start, end)

    assert len(filtered_df) > 0
    for idx, row in filtered_df.iterrows():
        assert start <= row["step"] <= end

def test_get_account_history(loader, normalized_df):
    account_id = "C1001"
    history = loader.get_account_history(normalized_df, account_id)

    assert "sent" in history
    assert "received" in history
    assert "total_sent" in history
    assert "total_received" in history
    assert "tx_count" in history

    # Assert types
    assert isinstance(history["total_sent"], float)
    assert isinstance(history["total_received"], float)
    assert isinstance(history["tx_count"], int)

    # Check logic
    sent_amount = history["sent"]["amount"].sum()
    received_amount = history["received"]["amount"].sum()
    assert history["total_sent"] == sent_amount
    assert history["total_received"] == received_amount
    assert history["tx_count"] == len(history["sent"]) + len(history["received"])
