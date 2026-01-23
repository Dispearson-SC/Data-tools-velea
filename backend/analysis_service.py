from fastapi import UploadFile, File, Depends, HTTPException, Form
from typing import List, Optional
import pandas as pd
from auth import get_current_active_user
from services.sales_cleaner import process_sales_clean
from services.utils import leer_archivo_base
from services.analysis_cleaner import TAMAL_MAPPING, get_product_category

# --- DATA ANALYSIS ENDPOINT ---
async def data_analysis_endpoint(
    files: List[UploadFile] = File(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    sucursales: Optional[str] = Form(None), # Comma separated list
    view_mode: str = Form("daily"), # daily, weekly, monthly
    product_filter: Optional[str] = Form(None), # Comma separated list of normalized names
    category_filter: Optional[str] = Form(None), # Comma separated list of categories
    current_user = Depends(get_current_active_user)
):
    try:
        clean_dfs = []
        raw_files_content = []

        # 1. Separate Clean vs Raw Files
        for f in files:
            content = await f.read()
            filename = f.filename
            
            # Try to read as DF
            try:
                base = leer_archivo_base(content, filename)
            except Exception as e:
                print(f"Error reading file {filename}: {e}")
                base = None
            
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
                # Note: We relax the check to allow minor variations or BOM issues
                
                # Normalize columns to check (upper case and stripped of non-alphanumeric if needed)
                # Helper to normalize
                def normalize_col(c):
                    return str(c).upper().strip().replace(' ', '_').replace('.', '')
                
                cols = {normalize_col(c) for c in df_check.columns}
                
                # We look for key ingredients
                has_sucursal = any('SUCURSAL' in c for c in cols)
                has_fecha = any('FECHA' in c for c in cols)
                has_total = any('TOTAL_VENTA' in c or 'TOTALVENTA' in c for c in cols)
                has_prod = any('PRODUCTO_FINAL' in c or 'PRODUCTOFINAL' in c for c in cols)
                
                if has_sucursal and has_fecha and has_total and has_prod:
                    is_clean = True
                    # Normalize column names in DF to ensure consistency
                    # Map found cols to standard names
                    new_cols = {}
                    for c in df_check.columns:
                        norm = normalize_col(c)
                        if 'SUCURSAL' in norm: new_cols[c] = 'Sucursal'
                        elif 'FECHA' in norm: new_cols[c] = 'Fecha'
                        elif 'TOTAL_VENTA' in norm or 'TOTALVENTA' in norm: new_cols[c] = 'Total_Venta'
                        elif 'PRODUCTO_FINAL' in norm or 'PRODUCTOFINAL' in norm: new_cols[c] = 'Producto_Final'
                        elif 'CANTIDAD' in norm: new_cols[c] = 'Cantidad'
                        elif 'PAQUETE_ORIGEN' in norm or 'PAQUETEORIGEN' in norm: new_cols[c] = 'Paquete_Origen'
                        else: new_cols[c] = str(c).strip()
                    
                    df_check.rename(columns=new_cols, inplace=True)
                    clean_dfs.append(df_check)
            
            if not is_clean:
                # If it's a CSV that was read as DF but not "Clean", we need to pass bytes to raw processor
                # But raw processor expects bytes.
                # If leer_archivo_base returned a DF for CSV, it means it parsed it.
                # But process_sales_clean expects (filename, bytes).
                # So we just pass original content.
                raw_files_content.append((filename, content))

        # 2. Process Raw Files if any
        if raw_files_content:
            try:
                df_processed = await process_sales_clean(raw_files_content)
                if not df_processed.empty:
                    clean_dfs.append(df_processed)
            except Exception as e:
                print(f"Error processing raw files: {e}")
                # Don't fail immediately, check if we have other data
                pass

        # 3. Combine All Data
        if not clean_dfs:
            raise HTTPException(status_code=400, detail="No valid data found in files. Please ensure you are uploading valid Wansoft Sales Reports (Excel or CSV).")
            
        df = pd.concat(clean_dfs, ignore_index=True)
        
        # Ensure Types
        df['Total_Venta'] = pd.to_numeric(df['Total_Venta'], errors='coerce').fillna(0)
        df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0)
        
        # 4. APPLY NORMALIZATION (MAPPING) & CATEGORIZATION
        # We apply the mapping to group similar products
        # If product not in mapping, we keep original name or mark as 'Otros'
        def get_normalized_info(prod_name):
            if prod_name in TAMAL_MAPPING:
                guiso, tipo, factor = TAMAL_MAPPING[prod_name]
                return f"{guiso} ({tipo})", factor
            return prod_name, 1

        # Apply mapping to get Normalized Name AND Factor
        # This fixes the calculation issue where "Tamales Puerco 12pz" was counted as 1 unit instead of 12
        df[['Producto_Normalizado', 'Factor']] = df['Producto_Final'].apply(
            lambda x: pd.Series(get_normalized_info(x))
        )
        
        # Calculate Real Units (Unidades Reales)
        df['Unidades_Reales'] = df['Cantidad'] * df['Factor']
        
        df['Categoria'] = df['Producto_Final'].apply(get_product_category)

        # Determine if sold in package
        # Logic: If Paquete_Origen is not NaN/None and not "N/A" -> Inside Package
        # Note: Check data first. Usually "N/A" or null means individual.
        def is_package(val):
            if pd.isna(val): return False
            s = str(val).upper().strip()
            return s not in ['NAN', 'NONE', 'N/A', '', 'NAT']
            
        df['En_Paquete'] = df['Paquete_Origen'].apply(is_package)
        
        # 5. Filter by Date
        if start_date and end_date:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
            mask = (df['Fecha'] >= start_date) & (df['Fecha'] <= end_date)
            df = df.loc[mask]

        # Calculate available sucursales BEFORE filtering by sucursal
        available_sucursales = sorted(df['Sucursal'].astype(str).unique().tolist())

        # 5.1 Filter by Category (Global)
        if category_filter:
            cat_list = [c.strip() for c in category_filter.split(',')]
            # Special case: If user wants to filter by "Paquete" category, they might expect to see the wrapper
            # But if they filter by "Tamal", they expect to see tamales.
            # This is straightforward row filtering.
            if "TODAS" not in cat_list and "Todas" not in cat_list:
                df = df[df['Categoria'].isin(cat_list)]
            
        # 6. Filter by Sucursal
        if sucursales:
            sucursal_list = [s.strip().upper() for s in sucursales.split(',')]
            if "TODAS" not in sucursal_list:
                df = df[df['Sucursal'].isin(sucursal_list)]
        
        # 7. Grouping Logic (Time)
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        
        # Calculate Number of Active Days (Days with sales in the filtered data)
        # This is used for Daily Average calculation
        active_days = df['Fecha'].nunique()
        if active_days == 0: active_days = 1

        if view_mode == 'weekly':
            df['Periodo'] = df['Fecha'].dt.to_period('W').apply(lambda r: r.start_time.strftime('%Y-%m-%d'))
        elif view_mode == 'monthly':
            df['Periodo'] = df['Fecha'].dt.to_period('M').apply(lambda r: r.strftime('%Y-%m'))
        else: # daily
            df['Periodo'] = df['Fecha'].dt.strftime('%Y-%m-%d')
            
        # --- AGGREGATIONS ---

        # A. Total Sales Over Time
        sales_over_time = df.groupby('Periodo')['Total_Venta'].sum().reset_index().to_dict(orient='records')
        
        # B. Product Mix (Top products) - USING NORMALIZED NAME AND EXCLUDING PACKAGES
        # We only want to see 'Real Products' (Tamales, Drinks) here, not the wrapper 'Media Docena'
        # Categories: 'Tamal', 'Bebida', 'Otro', 'Paquete'
        # We exclude 'Paquete' category for this specific chart
        # We use 'Unidades_Reales' instead of 'Cantidad' to account for 12pz packs
        df_mix = df[df['Categoria'] != 'Paquete']
        product_mix = df_mix.groupby('Producto_Normalizado')['Unidades_Reales'].sum().reset_index()
        product_mix = product_mix.sort_values('Unidades_Reales', ascending=False).head(15).to_dict(orient='records')
        
        # C. Sucursal Performance
        sucursal_perf = df.groupby('Sucursal')['Total_Venta'].sum().reset_index().to_dict(orient='records')
        
        # D. Detailed Product Table (Excluding Packages)
        # Filter out 'Paquete' category for this main table
        df_products_only = df[df['Categoria'] != 'Paquete'].copy()
        
        # We need to calculate:
        # - Unidades Totales (Sum of Unidades_Reales)
        # - Venta Normal (Sum of Unidades_Reales where En_Paquete is False)
        # - Promocion (Sum of Unidades_Reales where En_Paquete is True)
        # - Promedio Diario (Unidades Totales / Active Days)
        
        # Create helper columns for pivot
        df_products_only['Venta_Normal'] = df_products_only.apply(lambda x: x['Unidades_Reales'] if not x['En_Paquete'] else 0, axis=1)
        df_products_only['Venta_Promo'] = df_products_only.apply(lambda x: x['Unidades_Reales'] if x['En_Paquete'] else 0, axis=1)
        
        detailed_stats = df_products_only.groupby(['Producto_Normalizado', 'Categoria']).agg({
            'Unidades_Reales': 'sum',
            'Venta_Normal': 'sum',
            'Venta_Promo': 'sum'
        }).reset_index()
        
        detailed_stats.rename(columns={'Unidades_Reales': 'Unidades_Totales'}, inplace=True)
        
        # Calculate Daily Average (Factor de Venta)
        detailed_stats['Promedio_Diario'] = (detailed_stats['Unidades_Totales'] / active_days).round(2)
        
        detailed_stats = detailed_stats.sort_values('Unidades_Totales', ascending=False)
        product_table = detailed_stats.to_dict(orient='records')
        
        # D2. Package Breakdown Table
        # We want to see what is inside the packages
        # Filter for rows that ARE inside a package (En_Paquete == True) AND represent content (Categoria != Paquete)
        df_package_content = df[(df['En_Paquete'] == True) & (df['Categoria'] != 'Paquete')].copy()
        
        # Group by Package Name (Paquete_Origen) and Product
        package_stats = df_package_content.groupby(['Paquete_Origen', 'Producto_Normalizado']).agg({
            'Unidades_Reales': 'sum'
        }).reset_index()
        
        package_stats = package_stats.sort_values(['Paquete_Origen', 'Unidades_Reales'], ascending=[True, False])
        package_breakdown = package_stats.to_dict(orient='records')
        
        # E. Specific Product Trend (if filter provided)
        product_trend = []
        if product_filter:
            # Filter by Normalized Name
            # product_filter is comma separated
            prod_list = [p.strip() for p in product_filter.split(',')]
            df_prod = df[df['Producto_Normalizado'].isin(prod_list)]
            # Use Unidades_Reales for trend too
            product_trend = df_prod.groupby('Periodo')['Unidades_Reales'].sum().reset_index().to_dict(orient='records')
            # Rename for frontend compatibility (frontend expects 'Cantidad')
            for pt in product_trend:
                pt['Cantidad'] = pt['Unidades_Reales']

        # Get available sucursales and products for filters
        # available_sucursales = sorted(df['Sucursal'].astype(str).unique().tolist())
        
        # Available products grouped by category
        # List of { name: "...", category: "..." }
        unique_prods = df[['Producto_Normalizado', 'Categoria']].drop_duplicates()
        available_products = unique_prods.sort_values('Producto_Normalizado').to_dict(orient='records')
        
        data_min_date = df['Fecha'].min().strftime('%Y-%m-%d') if not df.empty else None
        data_max_date = df['Fecha'].max().strftime('%Y-%m-%d') if not df.empty else None

        return {
            "sales_over_time": sales_over_time,
            "product_mix": product_mix,
            "sucursal_performance": sucursal_perf,
            "product_table": product_table, 
            "package_breakdown": package_breakdown,
            "product_trend": product_trend,
            "available_sucursales": available_sucursales,
            "available_products": available_products,
            "data_range": {"min": data_min_date, "max": data_max_date},
            "raw_data_summary": {
                "total_sales": float(df['Total_Venta'].sum()),
                "total_items": float(df['Unidades_Reales'].sum()), 
                "transaction_count": int(len(df)),
                "active_days": int(active_days)
            }
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
