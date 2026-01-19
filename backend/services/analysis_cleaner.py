import pandas as pd
from .utils import leer_archivo_base
import io

TAMAL_MAPPING = {
    # --- Puerco ---
    'Tamal Puerco': ('Puerco', 'Tradicional', 1),
    'Puerco': ('Puerco', 'Tradicional', 1),
    'Tamales Puerco 12pz': ('Puerco', 'Tradicional', 12),
    'Tamal Borracho Puerco': ('Puerco', 'Borracho', 1),
    'Puerco (B)': ('Puerco', 'Borracho', 1),
    'Tamal Puerco Hoja de Platano': ('Puerco', 'Hoja de Platano', 1),
    'Puerco (HP)': ('Puerco', 'Hoja de Platano', 1),

    # --- Pollo ---
    'Tamal Pollo': ('Pollo', 'Tradicional', 1),
    'Pollo': ('Pollo', 'Tradicional', 1),
    'Tamales Pollo 12pz': ('Pollo', 'Tradicional', 12),
    'Tamal Pollo Hoja de Platano': ('Pollo', 'Hoja de Platano', 1),
    'Pollo (HP)': ('Pollo', 'Hoja de Platano', 1),
    'Tamal Borracho Salsa Verde': ('Pollo Salsa Verde', 'Borracho', 1),
    'Salsa Verde (B)': ('Pollo Salsa Verde', 'Borracho', 1),
    'Tamal Borracho Mole': ('Pollo Mole', 'Borracho', 1),
    'Mole (B)': ('Pollo Mole', 'Borracho', 1),

    # --- Queso ---
    'Tamal Queso': ('Queso', 'Tradicional', 1),
    'Queso': ('Queso', 'Tradicional', 1),
    'Tamales Queso 12pz': ('Queso', 'Tradicional', 12),
    'Tamal Borracho Queso': ('Queso', 'Borracho', 1),
    'Queso (B)': ('Queso', 'Borracho', 1),

    # --- Frijol ---
    'Tamal Frijol': ('Frijol', 'Tradicional', 1),
    'Frijol': ('Frijol', 'Tradicional', 1),
    'Frijoles': ('Frijol', 'Tradicional', 1),
    'Tamales Frijoles 12pz': ('Frijol', 'Tradicional', 12),

    # --- Dulce ---
    'Tamal Dulce': ('Dulce', 'Tradicional', 1),
    'Dulce': ('Dulce', 'Tradicional', 1),
    'Tamales Dulce 12pz': ('Dulce', 'Tradicional', 12),
    
    # --- Elote ---
    'Tamal Elote': ('Elote', 'Tradicional', 1),
    'Elote': ('Elote', 'Tradicional', 1),
    'Tamales Elote 12pz': ('Elote', 'Tradicional', 12),

    # --- Bebidas Normalization ---
    'Refresco Vidrio 355ml': ('Refresco Vidrio', '355ml', 1),
    'Refresco Vidrio 355': ('Refresco Vidrio', '355ml', 1),
    'Refresco lata 355': ('Refresco Lata', '355ml', 1),
    'Refresco Lata 355ml': ('Refresco Lata', '355ml', 1),
    'Refresco Pet 600ml': ('Refresco Pet', '600ml', 1),
}

# Add Drinks or other common items here if needed to classify
BEBIDA_KEYWORDS = ['CAFÉ', 'CHAMPURRADO', 'REFRESCO', 'AGUA', 'ATOLE', 'COCA', 'SPRITE', 'FANTA', 'JUGO', 'VASO', 'VALLEFRUT', 'FUZE TEA', 'CIEL']
PAQUETE_KEYWORDS = ['PAQUETE', 'DOCENA', 'COMBO', 'CIENTO', 'PROMO', '+']

def get_product_category(product_name):
    p_upper = str(product_name).upper()
    
    # 1. Check for Package/Combo first (Priority)
    if any(k in p_upper for k in PAQUETE_KEYWORDS):
        return 'Paquete'
        
    # 2. Check for Tamales
    # Logic: If it is in mapping (and not a beverage/paquete) it's likely a Tamal, 
    # BUT we added Beverages to mapping now. So we need to be careful.
    
    # Explicit Beverage check
    if any(k in p_upper for k in BEBIDA_KEYWORDS):
        return 'Bebida'
        
    # If in mapping and NOT beverage/paquete -> Tamal
    if product_name in TAMAL_MAPPING:
        # Check if mapped name indicates beverage
        mapped = TAMAL_MAPPING[product_name]
        if 'Refresco' in mapped[0]: return 'Bebida'
        return 'Tamal'
    
    # Heuristic for Tamal if not in mapping but looks like one
    if 'TAMAL' in p_upper or 'PUERCO' in p_upper or 'POLLO' in p_upper or 'QUESO' in p_upper or 'FRIJOL' in p_upper or 'DULCE' in p_upper or 'ELOTE' in p_upper:
         return 'Tamal'

    return 'Otro'

def procesar_analisis(files_content: list):
    """
    Lógica de Filtro_Analisis_1.ipynb
    """
    df_list = []
    
    for filename, content in files_content:
        # Assuming CSVs for Analysis as per original script
        # But `leer_archivo_base` handles both.
        df = leer_archivo_base(content, filename)
        if isinstance(df, pd.ExcelFile):
            # If Excel, maybe read first sheet? Script said "archivos_csv".
            # Let's assume user might upload Excel too, read first sheet.
            df = pd.read_excel(df, sheet_name=0)
        
        if df is not None:
            df_list.append(df)

    if not df_list:
        return {}, None, None

    df = pd.concat(df_list, ignore_index=True)

    # Extract date range
    min_date = None
    max_date = None
    
    # Try to find date column (User said column C, which is index 2, or by name)
    date_col = None
    if 'Fecha' in df.columns:
        date_col = 'Fecha'
    elif len(df.columns) > 2:
        # Try column index 2 (C)
        date_col = df.columns[2]
    
    if date_col:
        try:
            # Convert to datetime to find min/max
            # Handle potential non-date values
            dates = pd.to_datetime(df[date_col], errors='coerce').dropna()
            if not dates.empty:
                min_date = dates.min().strftime('%Y-%m-%d')
                max_date = dates.max().strftime('%Y-%m-%d')
        except:
            pass

    # 3. LÓGICA DE NEGOCIO
    tamal_mapping = TAMAL_MAPPING

    if 'Producto_Final' not in df.columns:
         # Try to find similar column or fail
         return {}, None, None 

    df_clean = df[df['Producto_Final'].isin(tamal_mapping.keys())].copy()
    
    mapping_data = df_clean['Producto_Final'].map(tamal_mapping).apply(pd.Series)
    df_clean[['Guiso', 'Tipo', 'Factor']] = mapping_data
    df_clean['Unidades_Reales'] = df_clean['Cantidad'] * df_clean['Factor']

    # Tablas
    tabla_total = df_clean.groupby(['Guiso', 'Tipo'])['Unidades_Reales'].sum().reset_index()
    tabla_total.columns = ['Guiso', 'Tipo', 'Total_Unidades']
    tabla_total = tabla_total.sort_values(by='Total_Unidades', ascending=False)

    df_fuera = df_clean[df_clean['Paquete_Origen'].isna()]
    df_dentro = df_clean[df_clean['Paquete_Origen'].notna()]

    tabla_fuera = df_fuera.groupby(['Guiso', 'Tipo'])['Unidades_Reales'].sum().reset_index()
    tabla_fuera.columns = ['Guiso', 'Tipo', 'Unidades_Fuera_Paquete']
    tabla_fuera = tabla_fuera.sort_values(by='Unidades_Fuera_Paquete', ascending=False)

    tabla_dentro = df_dentro.groupby(['Guiso', 'Tipo'])['Unidades_Reales'].sum().reset_index()
    tabla_dentro.columns = ['Guiso', 'Tipo', 'Unidades_Dentro_Paquete']
    tabla_dentro = tabla_dentro.sort_values(by='Unidades_Dentro_Paquete', ascending=False)

    return {
        "TOTAL_GENERAL": tabla_total,
        "FUERA_DE_PAQUETES": tabla_fuera,
        "EN_COMBOS_Y_PAQUETES": tabla_dentro
    }, min_date, max_date
