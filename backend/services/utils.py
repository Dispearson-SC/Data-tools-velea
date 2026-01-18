import pandas as pd
import numpy as np
import re
import io

def limpiar_sucursal_sql(texto):
    if pd.isna(texto): return "DESCONOCIDA"
    t = str(texto).upper().strip()
    if "-" in t: t = t.split("-")[0]
    
    # Remove "NAN" repetitions often found in raw extraction
    t = t.replace("NAN", "").strip()
    # Clean up multiple spaces
    t = re.sub(r'\s+', ' ', t)
    
    return t.strip()

def formatear_fecha_sql(fecha_str):
    if not isinstance(fecha_str, str): return str(fecha_str)
    meses = {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
             'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
             'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'}
    s = fecha_str.lower().strip()
    match = re.search(r'(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})', s)
    if match:
        dia, mes_nombre, anio = match.groups()
        mes_num = meses.get(mes_nombre, '00')
        return f"{anio}-{mes_num}-{dia.zfill(2)}"
    return fecha_str

def formatear_hora_sql(hora_str):
    if not isinstance(hora_str, str): return "00:00"
    s = str(hora_str).strip()
    match = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', s)
    if match:
        return match.group(0)[:5]
    return "00:00"

def limpiar_monto(valor):
    if pd.isna(valor) or str(valor).strip() in ["", "-", "$-", "."]: return 0.0
    s = str(valor).replace('$', '').replace(',', '').replace(' ', '')
    try: return float(s)
    except: return 0.0

def encontrar_columna_flexible(df, keywords):
    cols_norm = [str(c).upper().replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U').strip() for c in df.columns]
    for key in keywords:
        k = key.upper()
        for i, col_real in enumerate(df.columns):
            if k in cols_norm[i]: return col_real
    return None

def leer_archivo_base(file_content: bytes, filename: str):
    """
    Lee el archivo en memoria y retorna el objeto ExcelFile o DataFrame base
    para que cada servicio lo procese como necesite.
    """
    if filename.endswith(('.xlsx', '.xls')):
        try:
            return pd.ExcelFile(io.BytesIO(file_content))
        except Exception as e:
            print(f"Error Excel: {e}")
            return None
    elif filename.endswith('.csv'):
        try:
            # Try detecting separator and encoding
            content_sample = file_content[:4096]
            sep = ','
            
            # Try decoding as UTF-8 first
            try:
                decoded_head = content_sample.decode('utf-8').splitlines()
                encoding = 'utf-8'
            except UnicodeDecodeError:
                decoded_head = content_sample.decode('latin-1').splitlines()
                encoding = 'latin-1'

            if any(';' in l for l in decoded_head): sep = ';'
            
            str_io = io.StringIO(file_content.decode(encoding, errors='replace'))
            return pd.read_csv(str_io, sep=sep, engine='python')
        except Exception as e:
            print(f"Error CSV: {e}")
            return None
    return None
