import pandas as pd
import numpy as np
import hashlib
from .utils import (
    limpiar_sucursal_sql, formatear_fecha_sql, formatear_hora_sql, 
    limpiar_monto, encontrar_columna_flexible, leer_archivo_base
)
import io

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

def procesar_dataframe_ventas(df, sucursal_raw):
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

        # Note: We clean sucursal here again, which is fine (idempotent)
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

def extract_df_and_sucursal(file_obj, filename, content_bytes=None):
    df_final = None
    sucursal = "DESCONOCIDA"
    
    if isinstance(file_obj, pd.ExcelFile):
        for hoja in file_obj.sheet_names:
            df_temp = pd.read_excel(file_obj, sheet_name=hoja, header=None, nrows=50)
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
                df_final = pd.read_excel(file_obj, sheet_name=hoja, skiprows=header_idx)
                break
    elif isinstance(file_obj, pd.DataFrame):
        # CSV case from leer_archivo_base
        df_temp = file_obj.head(50) 
        
        header_idx = -1
        for i, row in df_temp.iterrows():
            linea = " ".join([str(x) for x in row.values]).upper()
            if "SUCURSAL:" in linea:
                try: sucursal = linea.split("SUCURSAL:")[1].split(",")[0].strip()
                except: pass
            if "MOVIMIENTO" in linea:
                header_idx = i
                break
        
        if header_idx != -1 and content_bytes:
             # Re-read CSV with correct header
             sep = ','
             decoded_head = content_bytes[:2000].decode('latin-1', errors='ignore').splitlines()
             if any(';' in l for l in decoded_head): sep = ';'
             str_io = io.StringIO(content_bytes.decode('latin-1', errors='ignore'))
             df_final = pd.read_csv(str_io, skiprows=header_idx, sep=sep, engine='python')
        elif header_idx != -1:
             # Fallback if no bytes provided (shouldn't happen in our flow)
             # Slicing is risky for headers but better than nothing
             # But main flow provides bytes
             pass
    
    # APPLY CLEANING HERE for metadata consistency
    sucursal = limpiar_sucursal_sql(sucursal)
    
    return df_final, sucursal


async def process_sales_clean(files_content: list):
    """
    Recibe lista de tuplas (filename, content_bytes)
    """
    dfs = []
    for filename, content in files_content:
        base = leer_archivo_base(content, filename)
        
        # Use common extraction logic
        df, sucursal = extract_df_and_sucursal(base, filename, content_bytes=content)

        if df is not None and not df.empty:
            df_res = procesar_dataframe_ventas(df, sucursal)
            if not df_res.empty:
                dfs.append(df_res)
    
    if dfs:
        final = pd.concat(dfs).drop_duplicates(subset=['Hash'])
        final = final.sort_values(by=['Fecha', 'Sucursal', 'Hora_Venta'])
        return final
    return pd.DataFrame()
