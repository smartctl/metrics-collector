import os
import pandas as pd
from datetime import datetime
import pyarrow.parquet as pq

class FileStats:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_format = file_path.split('.')[-1]
        
        # Check if the file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{file_path} does not exist.")
        
        self._data = None  # Cached data

    @property
    def df(self):
        if self._data is None:
            if self.file_format == "csv":
                self._data = pd.read_csv(self.file_path)
            elif self.file_format == "parquet":
                self._data = pd.read_parquet(self.file_path)
            else:
                raise ValueError(f"Unsupported file format: {self.file_format}")
        return self._data

    def get_size(self):
        return os.path.getsize(self.file_path)

    def get_location(self):
        return os.path.abspath(self.file_path)

    def get_num_columns(self):
        return len(self.df.columns)

    def get_num_rows(self):
        return len(self.df)

    def get_column_names(self):
        return list(self.df.columns)

    def get_date_created(self):
        timestamp = os.path.getctime(self.file_path)
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    def get_compression(self):
        if self.file_format == "parquet":
            # Using PyArrow to detect compression
            meta_data = pq.read_metadata(self.file_path)
            
            # Get the compression from the first column chunk of the first row group
            compression = meta_data.row_group(0).column(0).compression
            return compression if compression else None
        else:
            return None

    def summarize(self):
        stats = {
            "File Location": self.get_location(),
            "File Format": self.file_format,
            "Size (bytes)": self.get_size(),
            "Number of Columns": self.get_num_columns(),
            "Number of Rows": self.get_num_rows(),
            "Date Created": self.get_date_created(),
            "Compression Type": self.get_compression() if self.file_format == "parquet" else "N/A",
            "colume name": self.get_column_names()
        }
        return stats

    def print_summary(self):
        summary = self.summarize()
        for key, value in summary.items():
            print(f"{key}: {value}")
