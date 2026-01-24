
import pandas as pd
import os
from typing import List, Optional, Tuple
from services.utils import leer_archivo_base
from services.sales_cleaner import process_sales_clean
from services.analysis_cleaner import TAMAL_MAPPING, get_product_category

async def process_breakdown(
    files_content: List[Tuple[str, bytes]],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sucursales: Optional[List[str]] = None,
    view_mode: str = 'daily', # daily, weekly, monthly
    product_filter: Optional[List[str]] = None,
    category_filter: Optional[List[str]] = None
):
    # 1. Load Data (Handle both Raw and Clean files)
    print(f"DEBUG: Processing breakdown with {len(files_content)} files")
    
    clean_dfs = []
    raw_files_content = []

    for filename, content in files_content:
        try:
            base = leer_archivo_base(content, filename)
            df_check = None
            
            if isinstance(base, pd.ExcelFile):
                try:
                    df_check = pd.read_excel(base, sheet_name=0)
                except:
                    pass
            elif isinstance(base, pd.DataFrame):
                df_check = base
            
            is_clean = False
            if df_check is not None and not df_check.empty:
                # Check for "Cleaned" signature columns
                # 'Sucursal', 'Fecha', 'Total_Venta', 'Producto_Final'
                required_cols = {'SUCURSAL', 'FECHA', 'TOTAL_VENTA', 'PRODUCTO_FINAL'}
                cols = {str(c).upper().strip() for c in df_check.columns}
                
                if required_cols.issubset(cols):
                    is_clean = True
                    # Normalize column names in DF to ensure consistency
                    df_check.columns = [str(c).strip() for c in df_check.columns]
                    clean_dfs.append(df_check)
                    print(f"DEBUG: File {filename} detected as CLEANED")
            
            if not is_clean:
                raw_files_content.append((filename, content))
                print(f"DEBUG: File {filename} treated as RAW")
        except Exception as e:
            print(f"Error reading file {filename}: {e}")

    # Process Raw Files if any
    if raw_files_content:
        df_processed = await process_sales_clean(raw_files_content)
        print(f"DEBUG: process_sales_clean returned df with shape {df_processed.shape}")
        if not df_processed.empty:
            clean_dfs.append(df_processed)

    if not clean_dfs:
        print("DEBUG: No valid data found (clean or raw)")
        return {}, [], []
        
    df = pd.concat(clean_dfs, ignore_index=True)
    print(f"DEBUG: Final Combined DF shape: {df.shape}")

    # 2. Pre-processing (same as analysis_service)
    df['Total_Venta'] = pd.to_numeric(df['Total_Venta'], errors='coerce').fillna(0)
    df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0)
    
    # Normalization
    def get_normalized_info(prod_name):
        if prod_name in TAMAL_MAPPING:
            guiso, tipo, factor = TAMAL_MAPPING[prod_name]
            return f"{guiso} ({tipo})", factor
        return prod_name, 1

    df[['Producto_Normalizado', 'Factor']] = df['Producto_Final'].apply(
        lambda x: pd.Series(get_normalized_info(x))
    )
    
    print(f"DEBUG: Sample Normalized: {df['Producto_Normalizado'].head().tolist()}")

    df['Unidades_Reales'] = df['Cantidad'] * df['Factor']
    df['Categoria'] = df['Producto_Final'].apply(get_product_category)
    
    # 3. Filtering
    print(f"DEBUG: Filters - Start: {start_date}, End: {end_date}, Suc: {sucursales}, Cat: {category_filter}, Prod: {product_filter}")

    if start_date and end_date:
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        mask = (df['Fecha'] >= start_date) & (df['Fecha'] <= end_date)
        df = df.loc[mask]
        print(f"DEBUG: After date filter: {df.shape}")
        
    # Calculate available sucursales BEFORE filtering by sucursal
    available_sucursales = sorted(df['Sucursal'].unique().tolist())

    if sucursales:
        sucursal_list = [s.strip().upper() for s in sucursales]
        if "TODAS" not in sucursal_list:
            df = df[df['Sucursal'].isin(sucursal_list)]
            print(f"DEBUG: After sucursal filter: {df.shape}")
            
    if category_filter:
        if "TODAS" not in category_filter and "Todas" not in category_filter:
             df = df[df['Categoria'].isin(category_filter)]
             print(f"DEBUG: After category filter: {df.shape}")

    # Calculate available products BEFORE filtering by product
    # But AFTER Category/Sucursal filters, so we only show relevant products
    available_products = sorted(df['Producto_Normalizado'].unique().tolist())

    if product_filter:
        df = df[df['Producto_Normalizado'].isin(product_filter)]
        print(f"DEBUG: After product filter: {df.shape}")

    # 4. Grouping by Time
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    
    if view_mode == 'weekly':
        df['Periodo'] = df['Fecha'].dt.to_period('W').apply(lambda r: r.start_time.strftime('%Y-%m-%d'))
    elif view_mode == 'monthly':
        df['Periodo'] = df['Fecha'].dt.to_period('M').apply(lambda r: r.strftime('%Y-%m'))
    else: # daily
        df['Periodo'] = df['Fecha'].dt.strftime('%Y-%m-%d')

    # 5. Pivot Table Logic (TRANSPOSED)
    # We want: Producto_Normalizado | Periodo1 | Periodo2 ...
    # But first, let's pivot normally then transpose logic or just pivot differently.
    
    # New structure request:
    # Rows: Productos
    # Columns: Fechas (Periodos)
    # Filter by Sucursal (if multiple selected, maybe sum them or show multiple? User said "tabla por sucursal o sucursales")
    # Interpretation: If multiple sucursales, sum them up for the view? Or have "Sucursal" as a column?
    # User said: "la tabla sea por sucursal o sucursales, los productos esten en la parte izquierda, y en la parte superior esten las fechas"
    # This implies a Matrix: Rows=Products, Cols=Dates.
    # What about Sucursal? Usually this means Aggregated by selected sucursales.
    # If we want to split by sucursal, we'd need multiple tables or a hierarchical column index.
    # Let's assume Aggregation of selected sucursales for now (Total of selected).
    
    # Pivot: Index=Product, Columns=Periodo, Values=Sum(Unidades)
    pivot_df = df.pivot_table(
        index='Producto_Normalizado',
        columns='Periodo',
        values='Unidades_Reales',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    
    # Sort Products (Rows) by Priority Order
    # Define priority groups
    priority_order = [
        # Tradicionales
        "Puerco (Tradicional)", "Pollo (Tradicional)", "Frijol (Tradicional)", "Queso (Tradicional)", "Dulce (Tradicional)",
        # Hoja de Plátano
        "Pollo (Hoja de Platano)", "Puerco (Hoja de Platano)",
        # Borrachos
        "Pollo Salsa Verde (Borracho)", "Puerco (Borracho)", "Queso (Borracho)", "Pollo Mole (Borracho)",
        # Bebidas, Extras y Paquetes (Nuevo Orden Solicitado)
        "Refresco Vidrio (355ml)",
        "Refresco Lata (355ml)",
        "Refresco Pet (600ml)",
        "1 tamal borracho + 1 refresco",
        "1 tamal hp  + refresco",
        "5 tamales tradicionales + 1 refresco",
        "Cafe vaso",
        "Café vaso", # Added variant just in case
        "Ciel 1 lto.",
        "Ciel 600 ml",
        "Ciento",
        "Docena Mixta",
        "EMPANADA CAJETA Y NUEZ",
        "EMPANADA PIÑA",
        "Fuze Tea",
        "Media Docena",
        "Medio Ciento",
        "PAN DULCE",
        "Promo 3 Docenas",
        
        "Vallefrut",
        "Vaso de salsa 1/2 litro"
    ]
    
    # Create a categorical type for sorting
    # We need all unique products from data + priority list to ensure coverage
    unique_products = pivot_df['Producto_Normalizado'].unique().tolist()
    
    # Helper to get sort index
    def get_sort_index(prod_name):
        if prod_name in priority_order:
            return priority_order.index(prod_name)
        if prod_name == "Tamal Elote":
            return 9999 # Last
        return 100 + (unique_products.index(prod_name) if prod_name in unique_products else 0) # Middle (Alphabetical ideally but this works)

    # Sort logic
    pivot_df['sort_key'] = pivot_df['Producto_Normalizado'].apply(get_sort_index)
    
    # Secondary sort: Alphabetical for non-priority items
    pivot_df = pivot_df.sort_values(['sort_key', 'Producto_Normalizado'])
    pivot_df = pivot_df.drop(columns=['sort_key'])
    
    # Columns are now Periodos (Dates)
    # Get Date columns (excluding Producto_Normalizado)
    date_columns = [c for c in pivot_df.columns if c != 'Producto_Normalizado']
    # Sort dates
    date_columns.sort()
    
    # Reorder columns: Product first, then Dates
    final_cols = ['Producto_Normalizado'] + date_columns
    pivot_df = pivot_df[final_cols]
    
    # Convert to dict
    data = pivot_df.to_dict(orient='records')
    
    # Available options for UI (calculated earlier)
    # available_sucursales = sorted(df['Sucursal'].unique().tolist())
    # available_products = sorted(df['Producto_Normalizado'].unique().tolist())
    
    return {
        "data": data,
        "columns": date_columns, # Now sending Dates as columns
        "row_key": "Producto_Normalizado", # Frontend needs to know what key to use for first col
        "available_sucursales": available_sucursales,
        "available_products": available_products
    }
