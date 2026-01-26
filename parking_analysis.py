import pandas as pd
import os

def main():
    file_name = '서울특별시 강남구_주정차위반단속위치현황_20240320.csv'
    df = pd.read_csv(file_name, encoding='cp949')

    # Check columns
    required_columns = ['단속일시', '단속동', '단속장소']
    for col in required_columns:
        if col not in df.columns:
            print(f"Error: Column '{col}' not found in the dataset.")
            print("Available columns:", df.columns.tolist())
            return

    # Drop rows with missing values in required columns
    df = df.dropna(subset=required_columns)

    # Convert '단속일시' to datetime, coerce errors (turns invalid dates into NaT)
    df['단속일시'] = pd.to_datetime(df['단속일시'], errors='coerce')
    
    # Check if any rows were dropped
    nat_count = df['단속일시'].isna().sum()
    if nat_count > 0:
        print(f"Warning: {nat_count} rows contain invalid timestamps and will be dropped.")
        df = df.dropna(subset=['단속일시'])
    
    # Create '단속시간' (hour)
    # Using .dt.hour to get the hour
    hours = df['단속일시'].dt.hour
    
    # Function to map hour to time period
    def get_time_period(hour):
        if 0 <= hour < 6:
            return '0시~6시(야간)'
        elif 6 <= hour < 12:
            return '6시~12시(오전)'
        elif 12 <= hour < 18:
            return '12시~18시(오후)'
        else: # 18 <= hour < 24
            return '18시~24시(저녁)'

    df['시간대'] = hours.apply(get_time_period)
    
    # Create '단속위치' (단속동 + 단속장소)
    df['단속위치'] = df['단속동'].astype(str) + " " + df['단속장소'].astype(str)

    # Create the DataFrame (Pivot Table / GroupBy)
    # Rows: 단속위치, Cols: 시간대
    # We want counts.
    result_df = df.pivot_table(index='단속위치', columns='시간대', aggfunc='size', fill_value=0)
    
    # Reorder columns explicitly to match the requested order if needed
    col_order = ['0시~6시(야간)', '6시~12시(오전)', '12시~18시(오후)', '18시~24시(저녁)']
    # Filter columns that actually exist in the data (just in case no data for some period)
    existing_cols = [c for c in col_order if c in result_df.columns]
    result_df = result_df[existing_cols]

    print("\n[Resulting DataFrame (First 5 rows)]")
    print(result_df.head())
    
    print("-" * 50)
    
    # Analysis
    
    # 1. Time period with most enforcement (Column sum)
    # Summing across rows for each column
    time_counts = result_df.sum(axis=0)
    most_freq_time = time_counts.idxmax()
    most_freq_time_count = time_counts.max()
    
    print(f"1. 가장 단속이 많이 일어난 시간대: {most_freq_time} ({most_freq_time_count}건)")

    # 2. Location with most enforcement (Row sum)
    # Summing across columns for each row
    location_counts = result_df.sum(axis=1)
    most_freq_loc = location_counts.idxmax()
    most_freq_loc_count = location_counts.max()
    
    print(f"2. 가장 단속이 많이 일어난 구역: {most_freq_loc} ({most_freq_loc_count}건)")

if __name__ == "__main__":
    main()
