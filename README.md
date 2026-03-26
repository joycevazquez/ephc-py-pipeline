Project title:

EPHC-PY Pipeline

Description:

An ETL pipeline that processes Paraguay's Encuesta Permanente de Hogares Continua (EPHC) survey microdata and calculates three weighted labor market indicators by department: employment rate, average income, and poverty headcount.

Data Source:

Raw microdata CSV files published quarterly by the Instituto Nacional de Estadística (INE) of Paraguay.
A variable dictionary is available on the same site.

Methodology:

The pipeline derives department codes from the ESTGEO geographic stratum variable and maps them to department names. Income columns are cleaned — removing sentinel values, standardizing decimal separators, and replacing structural zeros with NaN — and aggregated into a total income variable.
The dataset is filtered to the working-age population (15+) following the ILO standard.
Three weighted indicators are calculated using the survey expansion factor (Factor): 
1. Employment rate (employed / economically active population),
2. Average income (weighted mean among employed),
3. Poverty headcount (share of population below INE's 2024 poverty line, differentiated by urban and rural areas).

Requirements:

Python 3.8+
pandas, numpy, psycopg2-binary (install with pip)
PostgreSQL 13+
Paraguay EPHC microdata CSV (not included)
How to run:

Prerequisites

1. Install the required Python libraries:
pip install pandas numpy psycopg2-binary
2. Create a PostgreSQL database:
psql -d postgres -c "CREATE DATABASE inepy;"
3. Download the quarterly EPHC microdata CSV from the INE Paraguay website: https://www.ine.gov.py 

Place the CSV file in the same folder as pipeline.py.

4. Run the pipeline:
python pipeline.py <filepath> <urban_poverty_threshold> <rural_poverty_threshold>

Example using Q1 2025 data with INE 2024 poverty lines:
python pipeline.py '97657-REG02_EPHC_1er Trim 2025.csv' 897168 654657

5. Query the results:
psql -d inepy -c "SELECT * FROM emp_inc_pov;"
Output:

The pipeline produces a summary table with one row per department containing the employment rate (%), weighted average monthly income (guaraníes), and poverty headcount (%) for the survey quarter. Results are stored in the emp_inc_pov table in the inepy PostgreSQL database.

Limitations:

1. Income is measured at the individual level, not household per capita as INE's official methodology specifies
2. Poverty thresholds use INE 2024 values (897,168 guaraníes urban / 654,657 rural); Q1 2025 values are not yet published
3. Boquerón department is absent from the Q1 2025 sample by INE's survey design