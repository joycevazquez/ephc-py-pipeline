import pandas as pd
import numpy as np
import psycopg2

def extract(filepath):
    df = pd.read_csv(filepath, encoding = 'utf-8-sig', sep = ';')
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.replace(r'^\s*$', np.nan, regex=True)
    df = df.replace('99999999999', np.nan, regex=True)

    return df

def transform(df):

    # Creating new column based on the first digit of the ESTGEO. Last two digits indicates rural or urban zone of the department.
    # 0 for Asuncion.
    df['DPTO'] = df['ESTGEO'].apply(lambda x: 0 if x == 1 else x // 10)

    # Mapping department names to their corresponding codes.
    dpto_names = {
        0: 'Asunción',
        1: 'Concepción',
        2: 'San Pedro',
        3: 'Cordillera',
        4: 'Guairá',
        5: 'Caaguazú',
        6: 'Caazapá',
        7: 'Itapúa',
        8: 'Misiones',
        9: 'Paraguarí',
        10: 'Alto Paraná',
        11: 'Central',
        12: 'Ñeembucú',
        13: 'Amambay',
        14: 'Canindeyú',
        15: 'Pdte Hayes'
    }

    df['DPTO_NAMES'] = df['DPTO'].map(dpto_names)

    income_cols = [
    'E01AIMDE',
    'E01BIMDE',
    'E01CIMDE',
    'E01DDE',
    'E01EDE',
    'E01FDE',
    'E01GDE',
    'E01HDE',
    'E01IDE',
    'E01JDE',
    'E01KDE',
    'E01LDE',
    'E01MDE',
    'E01KJDE'
    ]

    # Replacing local thousands separators by standardized ones and changing to numeric type.
    for col in income_cols:
        df[col] = df[col].str.replace(',', '.')
        df[col] = pd.to_numeric(df[col], errors = 'coerce')

    # Replacing 0s with NaN in income columns
    df[income_cols] = df[income_cols].replace(0, np.nan)

    # Creating a total_income column to sum all types of income
    df['TOTAL_INCOME'] = df[income_cols].sum(axis = 1)

    
    # Creating a mask for income columns where all of their values are NaN. Then applying that mask to the df, and setting the total_income values to NaN when the mask applies (no income in any column whatsoever).
    all_nan_mask = df[income_cols].isna().all(axis = 1)
    df.loc[all_nan_mask, 'TOTAL_INCOME'] = np.nan

    # The standard INE uses for the EPHC is 15 years old, that's also the international ILO standard for labor force surveys.
    df_workingage = df[df['P02'] >= 15].copy()
    
    # Calculating employment rate:
    emp_rate = df_workingage[df_workingage['PEAA'] == '1'].groupby('DPTO_NAMES')['Factor'].sum() / df_workingage[(df_workingage['PEAA'] == '1') | (df_workingage['PEAA'] == '2')].groupby('DPTO_NAMES')['Factor'].sum() * 100.0

    # Calculating the weighted average income by department: starting with creating an intermediate column that multiplies total_income * factor
    df_workingage['TOTAL_INCOME_BY_FACTOR'] = df_workingage['TOTAL_INCOME'] * df_workingage['Factor']

    # Calculating average income
    avg_income = df_workingage[df_workingage['PEAA'] == '1'].groupby('DPTO_NAMES')['TOTAL_INCOME_BY_FACTOR'].sum() / df_workingage[df_workingage['PEAA'] == '1'].groupby('DPTO_NAMES')['Factor'].sum()

    # Poverty threshold values for urban and rural areas
    URBAN_POVERTY_THRESHOLD = 897168
    RURAL_POVERTY_THRESHOLD = 654657

    # Creating a mask for urban and rural poverty rows, and then uniting both
    is_poor_urban_mask = (df_workingage['AREA'] == 1) & (df_workingage['TOTAL_INCOME'] < URBAN_POVERTY_THRESHOLD)
    is_poor_rural_mask = (df_workingage['AREA'] == 6) & (df_workingage['TOTAL_INCOME'] < RURAL_POVERTY_THRESHOLD)
    is_poor_mask = is_poor_rural_mask | is_poor_urban_mask

    # Calculating the poverty headcount
    poverty_headcount = (df_workingage.loc[is_poor_mask].groupby('DPTO_NAMES')['Factor'].sum() / df_workingage.groupby('DPTO_NAMES')['Factor'].sum() * 100.0).sort_values(ascending = False)

    # Uniting all three indicators
    emp_inc_pov = pd.concat([emp_rate, avg_income, poverty_headcount], axis = 1)
    emp_inc_pov.columns = ['Employment Rate', 'Average Income', 'Poverty Headcount']

    return emp_inc_pov

def load(summary):
    connection = psycopg2.connect(
        dbname = 'inepy',
        user = 'joycevazquez',
        host = 'localhost',
        port = '5432')

    cursor = connection.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS emp_inc_pov (" \
                "dpto_name TEXT PRIMARY KEY, " \
                "emp_rate FLOAT NOT NULL, " \
                "avg_income FLOAT NOT NULL, " \
                "pov_headcount FLOAT NOT NULL)")
    
    for row in summary.itertuples():
        cursor.execute(""" 
            INSERT INTO emp_inc_pov (dpto_name, emp_rate, avg_income, pov_headcount)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (dpto_name) DO UPDATE
                SET emp_rate = EXCLUDED.emp_rate,
                    avg_income = EXCLUDED.avg_income,
                    pov_headcount = EXCLUDED.pov_headcount
            """, (row.Index, row._1, row._2, row._3))

    connection.commit()
    cursor.close()
    connection.close()

if __name__ == '__main__':
    df = extract('97657-REG02_EPHC_1er Trim 2025.csv')
    summary = transform(df)
    load(summary)