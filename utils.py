import pandas as pd

class HandleTradeData:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = self.load_trades()
        self.clean_amount_column() # Data wrangling
        self.pnl_df = self.calculate_pnl(self.df)

    def load_trades(self):
        return pd.read_csv(self.file_path)

    def clean_amount_column(self):
        # Clean and convert Amount to float
        self.df['Amount'] = self.df['Amount'].replace('[\$,()]', '', regex=True).replace(',', '', regex=True)
        self.df['Amount'] = self.df['Amount'].apply(lambda x: f"-{x}" if '(' in str(x) else x)
        self.df['Amount'] = pd.to_numeric(self.df['Amount'], errors='coerce')

    def calculate_pnl(self, df):
        
        # Calculate PnL per instrument
        pnl = df.groupby('Instrument').apply(
            lambda g: g[g['Trans Code'] == 'STC']['Amount'].sum() - g[g['Trans Code'] == 'BTO']['Amount'].sum()
        ).reset_index(name='PnL')

        self.pnl_df = pnl
        return pnl

    def get_amount_for_instrument(self, instrument):

        print("Instrument: " + instrument)
        instrument_pnl = self.pnl_df[self.pnl_df['Instrument'] == instrument]
        if instrument_pnl.empty:
            return 0.0
        return instrument_pnl['PnL']

    def get_max_amount_for_instrument(self):
        return self.pnl_df['PnL'].max()

    def calculate_ach_transactions_sum(self):

        ach_transactions = self.df[self.df['Trans Code'] == 'ACH']
        return ach_transactions['Amount'].sum()

        
