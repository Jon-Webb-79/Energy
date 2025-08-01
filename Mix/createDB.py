import sys
import sqlite3
import pandas as pd

# ==========================================================================================
# ==========================================================================================

# File:    createDB.py
# Date:    July 31, 2025
# Author:  Jonathan A. Webb
# Purpose: Reads in data from an excel file downloaded from the nei website and loads its 
#          information into a SQlite file
# NOTE: All data in the excel file comes from this web site.
# https://www.eia.gov/totalenergy/data/browser/index.php?tbl=T01.02#/?f=M&start=197301&end=202504&charted=1-2-3-4-6-13

# ==========================================================================================
# ==========================================================================================
# Insert Code here


class ReadExcel:
    """
    Reads and preprocesses energy production data from an Excel file.

    This class loads an Excel spreadsheet containing monthly primary energy
    production values, renames relevant columns, standardizes missing values,
    and converts data types as needed.

    Attributes
    ----------
    df_subset : pd.DataFrame
        A cleaned and remapped subset of the Excel data with standardized column names
        and all numeric values converted to floats. The 'Date' column is preserved.
    """
    def __init__(self, file_name: str):
        """
        Initialize the ReadExcel object by reading and transforming the Excel file.

        Parameters
        ----------
        file_name : str
            Path to the Excel file to be read.
        """
        df = self._read_excel_file(file_name)
        self.df_subset = self._remap_dataFrame(df)

# ------------------------------------------------------------------------------------------ 

    def _read_excel_file(self, file_name: str) -> pd.DataFrame:
        """
        Read the raw Excel file and extract the relevant header and data rows.

        Assumes that the column headers are located at row 10 and the units
        row at 11 is skipped. The first column is renamed to 'Date'.

        Parameters
        ----------
        file_name : str
            Path to the Excel file.

        Returns
        -------
        pd.DataFrame
            A raw DataFrame containing the full dataset with the first column
            renamed to 'Date'. Exits the program if the file is not found.
        """
        try:
            df = pd.read_excel(file_name, sheet_name=0, skiprows=[11], header=10)
            df = df.rename(columns={df.columns[0]: "Date"})
            return df
        except FileNotFoundError:
            print(f"Error: The file '{file_name}' was not found.")
            sys.exit(1)
        return df

# ------------------------------------------------------------------------------------------

    def _remap_dataFrame(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Extract and clean a subset of energy source columns from the full DataFrame.

        Renames columns to simplified labels, replaces non-numeric values (e.g. 
        'Not Available') with 0.0, and ensures all values are floats.

        Parameters
        ----------
        data_frame : pd.DataFrame
            The raw DataFrame read from the Excel file.

        Returns
        -------
        pd.DataFrame
            A cleaned DataFrame with standardized column names and numeric values.
        """
        columns_mapping = {
            "Coal Production": "Coal",
            "Natural Gas (Dry) Production": "GasDry",
            "Natural Gas Plant Liquids Production": "GasLiquid",
            "Crude Oil Production": "CrudeOil",
            "Nuclear Electric Power Production": "Nuclear",
            "Hydroelectric Power Production": "Hydro",
            "Geothermal Energy Production": "Geothermal",
            "Solar Energy Production": "Solar",
            "Wind Energy Production": "Wind",
            "Biomass Energy Production": "Biomass"
        }
        df_subset = data_frame[["Date"] + list(columns_mapping.keys())]
        df_subset = df_subset.rename(columns=columns_mapping)

        for col in df_subset.columns:
            if col != "Date":
                df_subset[col] = pd.to_numeric(df_subset[col], errors="coerce").fillna(0.0)
        return df_subset


# ========================================================================================== 
# ==========================================================================================


class UpdateSQLite(ReadExcel):
    """
    A class that extends ReadExcel to update a SQLite database with energy production data.

    This class connects to a SQLite database, drops any existing 'Mix' table,
    creates a new one with standardized schema, and populates it using the
    cleaned data from the ReadExcel parent class.

    Attributes
    ----------
    db_name : str
        Name of the SQLite database file.
    conn : sqlite3.Connection
        SQLite connection object.
    cursor : sqlite3.Cursor
        Cursor object for executing SQL statements.
    """
    def __init__(self, file_name: str, db_name: str = "Energy.db"):
        """
        Initialize the UpdateSQLite object and populate the database.

        Parameters
        ----------
        file_name : str
            Path to the Excel file to be read and processed.
        db_name : str, optional
            Name of the SQLite database file to create or update (default is "Energy.db").
        """
        super().__init__(file_name)
        self.db_name = db_name 
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

        self._drop_table()
        self._create_newTable()
        self._insert_data()

        self.conn.commit()
        self.conn.close()

# ------------------------------------------------------------------------------------------

    def _drop_table(self) -> None:
        """
        Drop the 'Mix' table from the SQLite database if it exists.
        """
        self.cursor.execute("DROP TABLE IF EXISTS Mix")
# ------------------------------------------------------------------------------------------ 

    def _create_newTable(self) -> None:
        """
        Create a new 'Mix' table in the SQLite database with columns for
        energy production by source, including a primary key 'Date' column.
        """
        self.cursor.execute("""
            CREATE TABLE EnergyMix (
                Date TEXT PRIMARY KEY,
                Coal REAL,
                GasDry REAL,
                GasLiquid REAL,
                CrudeOil REAL,
                Nuclear REAL,
                Hydro REAL,
                Geothermal REAL,
                Solar REAL,
                Wind REAL,
                Biomass REAL
            )
        """)
# ------------------------------------------------------------------------------------------ 

    def _insert_data(self) -> None:
        """
        Insert the cleaned energy data into the 'Mix' table of the SQLite database.

        This method uses the df_subset attribute inherited from ReadExcel and
        writes it to the SQLite database using Pandas' to_sql method.
        """
        if self.df_subset is not None:
            self.df_subset.to_sql("EnergyMix", self.conn, if_exists="append", index=False)
            print("SQLite table 'EnergyMix' updated successfully.")

# ========================================================================================== 
# ========================================================================================== 


def main() -> None:
    UpdateSQLite("Mix.xlsx")    

# ========================================================================================== 
# ========================================================================================== 

if __name__ == "__main__":
    main()

# ========================================================================================== 
# ========================================================================================== 
# eof
