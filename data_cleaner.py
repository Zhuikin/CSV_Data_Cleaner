from __future__ import annotations
import pandas as pd
import json
from pathlib import Path
from ydata_profiling import ProfileReport

import logging.handlers

LOG_BACKUPS = 3
BASE_DIR = Path(__name__).parent

DEFAULT_CFG = {
    "input_file": "data/my_data.csv",  # done
    "output_file": "data/my_data_clean1.csv",  # done
    "delimiter_in": ",",  # done
    "delimiter_out": ",",  # done
    "input_file_profile": "profiles/input_file.html",  # done
    "output_file_profile": "profiles/output_file.html",  # done
    "summary_file": "",  # done
    "drop_repeat_headers": True,  # done
    "drop_duplicates": True,  # done
    "drop_na": True,  # done
    "clean_types": True,  # done
    "export_output_file": True,  # done
    "str_col": ["Product", "Purchase Address"],  # done
    "float_col": [],  # done
    "int_col": [],  # done
    "numeric_col": ["Order ID", "Quantity Ordered", "Price Each"],
    # done
    "datetime_col": ["Order Date"],  # done
    "datetime_format": ["%m/%d/%y %H:%M"],  # done
    "drop_col": [],  # done
    "quantile_ouliers_col": []
}


class CleanerCSV:
    """ Data processing class.

    Will read and interpret a spec file and perform taks according to
    the spec choices.
    """

    def __init__(self, config_file: Path):
        """ Intializes a CleanerCSV instance from the given specs file.

        Args:
            config_file (Path): The config file to load.
        """
        self.local_path = config_file.parent
        self.local_path.mkdir(parents=True, exist_ok=True)
        self.logfile = BASE_DIR / "data_cleaner.log"
        self.logger = logging.getLogger("CleanerCSV")
        self.logger.setLevel(logging.DEBUG)
        self.log_handler = CleanerCSV.make_log_handler(
            self.logfile, logging.DEBUG
        )
        self.logger.addHandler(self.log_handler)

        try:
            with open(
                    config_file,
                    encoding="utf-8"
            ) as f:
                self.cfg = json.load(f)
                self.cfg_file = config_file
        except FileNotFoundError:
            self.cfg = CleanerCSV.create_default_config()
            self.cfg_file = (BASE_DIR / "default_specs.json").absolute()
            self.logger.warning(f"config not found {config_file!r} "
                                f"- loading default config instead")
        except json.JSONDecodeError as e:
            self.cfg = CleanerCSV.create_default_config()
            self.cfg_file = (BASE_DIR / "default_specs.json").absolute()
            self.logger.warning(
                f"config file {config_file!r} is not valid JSON - {e} - "
                f"laoding default config instead")
        self.logger.info(f"loaded config {self.cfg_file!r}")
        user_log = self.cfg.get("summary_file", None)
        if user_log:
            user_log = BASE_DIR / user_log
            if user_log != self.logfile:
                self.logger.addHandler(
                    CleanerCSV.make_log_handler(user_log, logging.INFO)
                )

        self.input_profile = BASE_DIR / self.cfg.get("input_file_profile")
        self.output_profile = BASE_DIR / self.cfg.get("output_file_profile")
        self.df = self.csv_read()
        self.df_changed = False
        self.na_safe = False

    def release_files(self):
        """ Closes and releases the logger ressources.
        """
        self.log_handler.close()
        self.logger.removeHandler(self.log_handler)

    @classmethod
    def create_default_config(cls) -> dict:
        """ Provides a default config.

        Reads default_specs.json if it exists otherwise creates a new
        default_specs.json file

        Returns:
            dict: The defualt configuration template as a dict.
        """
        default_cfg_file = BASE_DIR / "default_specs.json"
        if default_cfg_file.exists():
            with open(default_cfg_file, encoding="utf-8") as f:
                cfg = json.load(f)
                return cfg

        # write fallback default config dict
        default = DEFAULT_CFG
        with open(
                default_cfg_file,
                mode="w",
                encoding="utf-8"
        ) as f:
            json.dump(default, f, indent=4, ensure_ascii=False)

        return default

    @classmethod
    def make_log_handler(
            cls,
            logfile: Path,
            level
    ) -> logging.handlers.RotatingFileHandler:
        """ Creates a logger object with backups of 3 previous logfiles.

        Args:
            logfile (Path): The physical location to store the log
            level: Minimum message level for the logger
        """
        logfile.parent.mkdir(parents=True, exist_ok=True)
        rollover = True if logfile.exists() else False
        lf = logging.Formatter(
            "{levelname} - {name} - {asctime} - {message}",
            style="{"
        )
        lf.datefmt = "%y-%m-%d %H%M"
        fh = logging.handlers.RotatingFileHandler(
            logfile,
            mode="w",
            backupCount=LOG_BACKUPS
        )
        fh.setFormatter(lf)
        fh.setLevel(level)
        if LOG_BACKUPS > 0 and rollover:
            fh.doRollover()

        return fh

    def csv_read(self) -> pd.DataFrame:
        """ Read the specified csv file into a dataframe
        """
        source_path = self.local_path / self.cfg.get("input_file")
        sep = self.cfg.get("delimiter_in")
        sep = sep if sep else ","
        try:
            df_source = pd.read_csv(
                source_path,
                sep=sep
            )
        except IOError as e:
            self.logger.error(f"failed to read CSV: {e}")
            raise e
        else:
            self.logger.info(f"loaded data {source_path!r}")
            return df_source

    def csv_write_clean(self):
        """ Writes the (cleaned) dataframe to a CSV file
        """
        if not self.cfg.get("export_output_file"):
            self.logger.warning(
                f"the specs file \"export_output_file\" is 'False' - "
                f"cleaned data was not stored")
            return

        file_out = self.local_path / self.cfg.get("output_file")
        file_out.parent.mkdir(parents=True, exist_ok=True)
        sep = self.cfg.get("delimiter_out")
        sep = sep if sep else ","
        try:
            self.df.to_csv(
                file_out,
                sep=sep,
                index=False
            )
        except IOError as e:
            self.logger.error(f"failed to write CSV: {e}")
            raise e
        else:
            self.logger.info(f"processed data written to {file_out!r}")

    def html_profile(self) -> str:
        """ Creates and writes a profile for the dataframe

        Will automatically choose to write input profile if the data has not
        been changed and output profile as soon as any cleaning operation
        has been run.
        """
        if not self.df_changed:
            file = self.local_path / self.cfg.get("input_file_profile")
            self.logger.info(f"profiling source data to {file!r}")
        else:
            file = self.local_path / self.cfg.get("output_file_profile")
            self.logger.info(f"cleaned data - profiling to {file!r}")
        file.parent.mkdir(parents=True, exist_ok=True)
        profile = ProfileReport(self.df)
        profile.to_file(output_file=file)
        self.logger.info(f"profiling finished")

        return file.__str__()

    def run_all_cleaners(self) -> pd.DataFrame:
        """ Calls each cleaning method in turn.

        Each cleaner reads and respects the relevant specs options.
        """
        self.clean_headers()
        self.clean_drop_dupplicates()
        self.clean_numeric_columns()
        self.clean_datetime_columns()
        self.run_astype_conversion("int")
        self.run_astype_conversion("float")
        self.run_astype_conversion("str")
        self.clean_drop_na()
        self.drop_columns()
        self.clean_quantile_outliers()

        return self.df

    def clean_headers(self):
        """ Removes re-occuring header rows.
        """
        if self.cfg.get("drop_repeat_headers"):
            self.logger.info("removing dupplicate headers")
            self.df_changed = True
            self.df.drop(
                self.df.loc[
                    self.df.eq(self.df.columns).any(axis=1)
                ].index,
                inplace=True
            )

    def clean_drop_dupplicates(self):
        """ Remove dupplicate data rows.
        """
        if self.cfg.get("drop_duplicates"):
            self.logger.info("removing dupplicate rows")
            self.df_changed = True
            self.df.drop_duplicates(keep="last", inplace=True)

    def clean_numeric_columns(self):
        """ Defines numeric column data types.
        """
        if not self.cfg.get("clean_types"):
            return

        self.df_changed = True
        for col in self.cfg.get("numeric_col"):
            self.logger.info(f"running to_numeric on column {col!r}")
            self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

    def run_astype_conversion(self, type_str: str):
        """ Runs explicit astype conversions.
        """
        if not self.cfg.get("clean_types"):
            return

        match type_str:
            case "int":
                cols_choice = self.cfg.get("int_col")
            case "float":
                cols_choice = self.cfg.get("float_col")
            case "str":
                cols_choice = self.cfg.get("str_col")
            case _:
                return
        if not cols_choice:
            return

        self.df_changed = True
        type_map = {"int": int, "float": float, "str": str}
        for col in cols_choice:
            self.logger.info(f"running astype({type_str!r}) on column {col!r}")
            try:
                self.df[col] = self.df[col].astype(
                    type_map.get(type_str, str)
                )
            except ValueError as e:
                self.logger.error(
                    f"converting column {col} to {type_str!r} failed - {e}"
                )

    def clean_datetime_columns(self):
        """ Defines datetime column data types.
        """
        cols = self.cfg.get("datetime_col")
        if not self.cfg.get("clean_types") or not cols:
            return

        forms = self.cfg.get("datetime_format")
        l_cols = len(cols)
        l_forms = len(forms)
        if l_cols != l_forms:
            self.logger.warning(
                f"spec has {l_cols!r} datetime columns but {l_forms!r} formats"
                f" - skipping datetime step")
            return self.df

        self.df_changed = True
        for col, form in zip(cols, forms):
            self.logger.info(
                f"running to_datetime on column {col!r} using {form!r}"
            )
            self.df[col] = pd.to_datetime(
                self.df[col],
                format=form,
                errors="coerce"
            )

    def clean_drop_na(self):
        """ Removes rows containing NaN entries.
        """
        if not self.cfg.get("drop_na"):
            return

        self.logger.info("dropping NaN and NaT rows")
        self.df_changed = True
        self.df.dropna(axis="index", how="all", inplace=True)


    def clean_quantile_outliers(self):
        """ Clears outliers using IQR
        """
        q_o_cols = self.cfg.get("quantile_ouliers_col")
        if not q_o_cols:
            return

        for col in q_o_cols:
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q1 - Q3
            min_valid = Q1 - 1.5 * IQR
            max_valid = Q3 + 1.5 * IQR

            valid_rows = (
                (self.df[col] >= min_valid) &
                (self.df[col] <= max_valid)
            )

            self.df = self.df[valid_rows]

    def drop_columns(self):
        """ Drop specified column(s) from the dataframe.
        """
        columns = self.cfg.get("drop_col")
        if not columns:
            return

        self.logger.info(f"dropping columns form the dataframe {columns=}")
        for col in columns:
            try:
                self.df.drop(labels=col, axis="columns", inplace=True)
            except KeyError as e:
                self.logger.warning(
                    f"column {col!r} not in the dataframe - {e}")

    def __repr__(self) -> str:
        return f"CleanerCSV(config_file={self.cfg_file!r})"

    def __str__(self) -> str:
        return "\n".join([f"{i}: {self.cfg.get(i)}" for i in self.cfg.keys()])
