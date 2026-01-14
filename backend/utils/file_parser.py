import pandas as pd
import io

def parse_file_preview(file_path: str, file_type: str) -> dict:
    """Parse file and return preview data"""
    try:
        if file_type == 'csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        return {
            'columns': df.columns.tolist(),
            'row_count': len(df),
            'sample_data': df.head(5).to_dict('records')
        }
    except Exception as e:
        return {'error': str(e), 'columns': [], 'row_count': 0, 'sample_data': []}

def parse_file_to_records(file_path: str, file_type: str) -> tuple:
    """Parse file and return records as list of dicts"""
    try:
        if file_type == 'csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Convert to records
        records = df.fillna('').to_dict('records')
        
        # Clean each record
        for record in records:
            for key in record:
                if isinstance(record[key], float) and pd.isna(record[key]):
                    record[key] = ''
                elif isinstance(record[key], (int, float)):
                    record[key] = str(record[key])
        
        return records, df.columns.tolist()
    except Exception as e:
        return [], []
