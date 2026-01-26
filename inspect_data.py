import pandas as pd

file_name = '서울특별시 강남구_주정차위반단속위치현황_20240320.csv'

try:
    df = pd.read_csv(file_name, encoding='cp949')
    print("Columns:", df.columns.tolist())
    print("\n[단속장소 Column Info]")
    print(df['단속장소'].dtype)
    print("\n[First 20 unique values]")
    print(df['단속장소'].unique()[:20])
    print("\n[Sample 10 rows]")
    print(df[['단속동', '단속장소']].sample(10))
    
    # Check if they look like floats
    print("\n[Are there float-looking values?]")
    is_float = df['단속장소'].apply(lambda x: isinstance(x, float))
    print(df[is_float]['단속장소'].head())

    print("\n[Are there purely numeric strings?]")
    # convert to string first to avoid error on float/nan
    is_numeric = df['단속장소'].astype(str).str.match(r'^\d+$')
    print(df[is_numeric]['단속장소'].head())
    print(f"Count of purely numeric values: {df[is_numeric]['단속장소'].count()}")

    print("\n[Are there scientific notation looking strings?]")
    is_sci = df['단속장소'].astype(str).str.match(r'^\d+\.\d+E\+\d+$')
    print(df[is_sci]['단속장소'].head())


except Exception as e:
    print(e)
