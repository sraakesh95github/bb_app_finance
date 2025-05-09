import pandas as pd

class HandleTradeData:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = self.load_trades()
        self.df = self.df.dropna(how='all') # Drop rows with all NaN values
        self.clean_amount_column(self.df) # Data wrangling
        self.pnl_df = self.calculate_pnl(self.df)
        self.exp_loss_df = self.get_expiration_loss()

    def load_trades(self):
        return pd.read_csv(self.file_path)

    def clean_amount_column(self, df):
        # Clean and convert Amount to float
        df['Amount'] = df['Amount'].replace('[\$,()]', '', regex=True).replace(',', '', regex=True)
        df['Amount'] = df['Amount'].apply(lambda x: f"-{x}" if '(' in str(x) else x)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        return df.copy()

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
    
    def get_expiration_loss(self):
    
        oexp_records = self.df[self.df["Trans Code"] == "OEXP"].copy()
        
        oexp_records["MatchedDescription"] = oexp_records["Description"].str.extract(r"Option Expiration for\s+(.+)$")
        
        merged_df = self.df.merge(
            oexp_records[["MatchedDescription"]],
            left_on="Description",
            right_on="MatchedDescription",
            how="inner"
        )
        
        merged_df_cleaned = self.clean_amount_column(merged_df)
        
        merged_df_cleaned["Amount"] = pd.to_numeric(merged_df_cleaned["Amount"], errors="coerce")
        oexp_df = merged_df.groupby("Instrument", as_index=False)["Amount"].sum()
        oexp_df = oexp_df.rename(columns={"Amount": "loss_amount"})

        return oexp_df
    
    def calculate_exp_loss_percentage(self):
        # Calculate the percentage of expiration loss
        total_bto_amount = self.df[self.df['Trans Code'] == 'BTO']['Amount'].sum()
        if total_bto_amount == 0:
            return 0.0
        exp_loss = self.exp_loss_df["loss_amount"].sum()
        return (exp_loss / total_bto_amount) * 100 if total_bto_amount != 0 else 0.0


    def risk_management_advice(self):
        advice = []

        # 1. Expiration losses as % of total buys
        exp_loss_pct = self.calculate_exp_loss_percentage()
        if exp_loss_pct > 20:
            advice.append("Reduce option positions held until expiration; consider setting exit rules to avoid full premium loss.")

        # 2. Max loss vs. max gain
        max_pnl = self.pnl_df['PnL'].max()
        min_pnl = self.pnl_df['PnL'].min()
        if abs(min_pnl) > max_pnl:
            advice.append("Your largest loss is greater than your largest gain. Use stop-losses or reduce position size to protect capital.")

        # 3. Concentration in few instruments
        instrument_counts = self.df['Instrument'].value_counts()
        top_instruments = instrument_counts[instrument_counts > 5]
        if len(top_instruments) == 1:
            advice.append(f"You are trading mostly in {top_instruments.index[0]}. Diversify across instruments to spread risk.")

        # 4. High ACH deposit frequency
        ach_count = len(self.df[self.df['Trans Code'] == 'ACH'])
        if ach_count > 3:
            advice.append("Frequent ACH deposits suggest you may be replenishing a losing account. Review position sizing and avoid revenge trading.")

        # 5. Net PnL
        net_pnl = self.pnl_df['PnL'].sum()
        if net_pnl < 0:
            advice.append("Your portfolio shows an overall loss. Re-evaluate your strategy and limit downside exposure per trade.")

        return advice if advice else ["Your risk appears reasonably managed. Continue monitoring for consistency and discipline."]
