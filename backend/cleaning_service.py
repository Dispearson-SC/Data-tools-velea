import pandas as pd
import numpy as np
import hashlib
import re
import io
from fastapi import UploadFile

# ==========================================
# 1. UTILIDADES DE LIMPIEZA
# ==========================================

def limpiar_sucursal_sql(texto):
    if pd.isna(texto): return "DESCONOCIDA"
    t = str(texto).upper().strip()
    if "-" in t: t = t.split("-")[0]
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

def detectar_tipo_oferta(nombre, precio_total, cantidad):
    n = str(nombre).upper()
    try:
        cant = float(cantidad)
        if cant == 0: cant = 1
        p_unit = float(precio_total) / cant
    except: p_unit = 0

    if "3 DOCENA" in n or p_unit >= 300: return "PROMO 3 DOCENAS"
    es_borracho = "BORRACHO" in n
    es_hoja = "HOJA" in n and "PLATANO" in n

    if es_borracho:
        return "PAQUETE BORRACHO ($55)" if (50 <= p_unit <= 60 or "PAQUETE" in n) else "VENTA REGULAR"
    if es_hoja:
        return "PAQUETE HOJA PLATANO ($55)" if (50 <= p_unit <= 60 or "PAQUETE" in n) else "VENTA REGULAR"
    if "PAQUETE #3" in n or "5 TAMALES" in n: return "PAQUETE #3 (5 PZ)"
    if "PAQUETE" in n: return "OTRA PROMOCION"
    return "VENTA REGULAR"

# ==========================================
# 2. BÚSQUEDA DE COLUMNAS
# ==========================================

def encontrar_columna_modificador(df):
    cols_norm = [str(c).upper().strip() for c in df.columns]
    if "MODIFICADOR" in cols_norm:
        return df.columns[cols_norm.index("MODIFICADOR")]
    for i, col_name in enumerate(cols_norm):
        if "MODIFICADOR" in col_name and "PRECIO" not in col_name and "COSTO" not in col_name:
            return df.columns[i]
    return None

def encontrar_columna_es_modificador(df):
    cols_norm = [str(c).upper().strip() for c in df.columns]
    for i, col_name in enumerate(cols_norm):
        if "¿" in col_name or col_name.startswith("ES MOD") or "IS MOD" in col_name:
            if "PRECIO" not in col_name and "COSTO" not in col_name:
                return df.columns[i]
    return None

def encontrar_columna_flexible(df, keywords):
    cols_norm = [str(c).upper().replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U').strip() for c in df.columns]
    for key in keywords:
        k = key.upper()
        for i, col_real in enumerate(df.columns):
            if k in cols_norm[i]: return col_real
    return None

def leer_archivo_memoria(file_content: bytes, filename: str):
    df_final = None
    sucursal = "DESCONOCIDA"
    
    # --- MODO EXCEL ---
    if filename.endswith(('.xlsx', '.xls')):
        try:
            xls = pd.ExcelFile(io.BytesIO(file_content))
            for hoja in xls.sheet_names:
                df_temp = pd.read_excel(xls, sheet_name=hoja, header=None, nrows=50)
                header_idx = -1
                for i, row in df_temp.iterrows():
                    linea = " ".join([str(x) for x in row.values]).upper()
                    if "SUCURSAL:" in linea:
                        try: sucursal = linea.split("SUCURSAL:")[1].split(",")[0].strip()
                        except: pass
                    if "MOVIMIENTO" in linea and ("PLATILLO" in linea or "ART" in linea):
                        header_idx = i
                        break
                if header_idx != -1:
                    df_final = pd.read_excel(xls, sheet_name=hoja, skiprows=header_idx)
                    break
        except Exception as e: 
            print(f"Error Excel: {e}")

    # --- MODO CSV ---
    else:
        try:
            sep = ','
            # Detect separator from first lines
            decoded_head = file_content[:2000].decode('latin-1', errors='ignore').splitlines()
            if any(';' in l for l in decoded_head): sep = ';'
            
            # Read to find header
            str_io = io.StringIO(file_content.decode('latin-1', errors='ignore'))
            df_temp = pd.read_csv(str_io, header=None, nrows=50, sep=sep, engine='python')
            
            header_idx = -1
            for i, row in df_temp.iterrows():
                linea = " ".join([str(x) for x in row.values]).upper()
                if "SUCURSAL:" in linea:
                    try: sucursal = linea.split("SUCURSAL:")[1].split(",")[0].strip()
                    except: pass
                if "MOVIMIENTO" in linea:
                    header_idx = i
                    break
            
            if header_idx != -1:
                # Reset pointer
                str_io.seek(0)
                df_final = pd.read_csv(str_io, skiprows=header_idx, sep=sep, engine='python')
                
        except Exception as e: 
            print(f"Error CSV: {e}")

    return df_final, sucursal

def procesar_dataframe(df, sucursal_raw):
    if df is None or df.empty: return pd.DataFrame()

    col_mov = encontrar_columna_flexible(df, ["MOVIMIENTO", "FOLIO", "PDV"])
    col_plat = encontrar_columna_flexible(df, ["PLATILLO", "ARTICULO", "PRODUCTO"])
    col_prec = encontrar_columna_flexible(df, ["PRECIO", "UNITARIO"])
    col_cant = encontrar_columna_flexible(df, ["CANTIDAD", "CANT"])
    col_hora = encontrar_columna_flexible(df, ["HORA", "CAPTURA"])
    col_fecha = encontrar_columna_flexible(df, ["FECHA", "OPERACION"])
    col_desc = encontrar_columna_flexible(df, ["DESCUENTO"])

    col_mod = encontrar_columna_modificador(df)
    col_es_mod = encontrar_columna_es_modificador(df)

    if not col_mov or not col_plat:
        return pd.DataFrame()

    df[col_mov] = df[col_mov].replace(r'^\s*$', np.nan, regex=True).ffill()
    if col_fecha: df[col_fecha] = df[col_fecha].replace(r'^\s*$', np.nan, regex=True).ffill()
    if col_hora: df[col_hora] = df[col_hora].replace(r'^\s*$', np.nan, regex=True).ffill()

    datos = []
    key_temp = df[col_mov].astype(str) + "_" + df[col_plat].astype(str)
    df['Instancia'] = df.groupby(key_temp).cumcount()

    paquete_actual = "VENTA DIRECTA"

    for _, fila in df.iterrows():
        mov = fila.get(col_mov)
        if pd.isna(mov) or "TOTAL" in str(mov).upper(): continue

        es_mod = False
        if col_es_mod:
            val = str(fila.get(col_es_mod, 'No')).upper()
            es_mod = val in ['SI', 'SÍ', 'S', 'TRUE', 'YES']

        nom_plat = str(fila.get(col_plat, '')).strip()
        nom_mod = str(fila.get(col_mod, '')).strip() if col_mod else ""

        if es_mod and any(x in nom_mod.upper() for x in ["LLEVAR", "DIDI", "UBER", "RAPPI", "COMEDOR", "SIN ", "CON "]):
            continue

        if not es_mod:
            paquete_actual = nom_plat if nom_plat else "PRODUCTO DESCONOCIDO"
            prod_final = paquete_actual
            origen = "N/A"
        else:
            if nom_mod:
                prod_final = nom_mod
            else:
                prod_final = f"{paquete_actual} (DETALLE)"
            origen = paquete_actual

        precio = limpiar_monto(fila.get(col_prec, 0))
        cant = limpiar_monto(fila.get(col_cant, 0))
        desc = limpiar_monto(fila.get(col_desc, 0)) if col_desc else 0
        total = (precio * cant) - desc

        suc_limpia = limpiar_sucursal_sql(sucursal_raw)
        fecha_sql = formatear_fecha_sql(fila.get(col_fecha, "1900-01-01"))
        hora_raw = str(fila.get(col_hora, "00:00"))
        if len(hora_raw.split()) > 1: hora_raw = hora_raw.split()[-1]
        hora_sql = formatear_hora_sql(hora_raw)

        hash_id = hashlib.md5(f"{suc_limpia}{mov}{prod_final}{cant}{total}{hora_raw}{fila['Instancia']}".encode()).hexdigest()

        datos.append({
            "Sucursal": suc_limpia,
            "MovimientoPDV": mov,
            "Fecha": fecha_sql,
            "Hora_Venta": hora_sql,
            "Producto_Final": prod_final,
            "Cantidad": cant,
            "Total_Venta": total,
            "Paquete_Origen": origen,
            "Tipo_Oferta": detectar_tipo_oferta(paquete_actual, total, cant),
            "Hash": hash_id
        })

    return pd.DataFrame(datos)

async def process_upload(file: UploadFile):
    content = await file.read()
    df, sucursal = leer_archivo_memoria(content, file.filename)
    if df is None:
        raise ValueError("No se pudo leer el archivo o no se encontraron datos válidos.")
    
    df_res = procesar_dataframe(df, sucursal)
    return df_res
