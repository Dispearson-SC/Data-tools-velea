from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import pandas as pd
from typing import List, Optional
from auth import router as auth_router, get_current_active_user, users_db, save_users
from services.sales_cleaner import process_sales_clean, extract_df_and_sucursal
from services.analysis_cleaner import procesar_analisis
from services.production_cleaner import procesar_produccion
from services.utils import leer_archivo_base
from analysis_service import data_analysis_endpoint

app = FastAPI(title="Velea Limpieza API")

# CORS
origins = [
    "http://localhost:5173", # Vite Frontend
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"message": "Velea Limpieza API is running"}

# --- QUICK SCAN ---
@app.post("/tools/scan")
async def scan_files(
    files: List[UploadFile] = File(...),
    current_user = Depends(get_current_active_user)
):
    results = []
    for file in files:
        content = await file.read()
        filename = file.filename
        
        info = {
            "filename": filename,
            "sucursal": "Desconocida",
            "rango_fechas": "No detectado"
        }
        
        try:
            # 1. Detect Sucursal using Sales Logic (most common)
            # We use extract_df_and_sucursal from sales_cleaner as it has the logic
            # But we need to pass a file object, not bytes if possible, or adapt logic.
            # extract_df_and_sucursal takes (file_obj, filename)
            
            base = leer_archivo_base(content, filename)
            
            if base is not None:
                # Get Sucursal
                _, sucursal = extract_df_and_sucursal(base, filename, content_bytes=content)
                info["sucursal"] = sucursal
                
                # Get Date Range (C4 in 'Detalle de ventas')
                # Only for Excel files as per request
                if isinstance(base, pd.ExcelFile):
                    sheet_name = None
                    # Find 'Detalle de ventas' or similar (2nd sheet usually)
                    for name in base.sheet_names:
                        if "DETALLE" in name.upper() and "VENTAS" in name.upper():
                            sheet_name = name
                            break
                    
                    if not sheet_name and len(base.sheet_names) > 1:
                        sheet_name = base.sheet_names[1] # Default to 2nd sheet
                    
                    if sheet_name:
                        try:
                            # Read specific cell C4 (row 3, col 2)
                            # We read a small chunk around it
                            df_meta = pd.read_excel(base, sheet_name=sheet_name, header=None, skiprows=3, nrows=1, usecols="C")
                            if not df_meta.empty:
                                val = df_meta.iloc[0, 0]
                                if pd.notna(val):
                                    info["rango_fechas"] = str(val).strip()
                        except Exception as e:
                            print(f"Error reading C4: {e}")

        except Exception as e:
            print(f"Scan error for {filename}: {e}")
            
        results.append(info)
        
    return results

# --- SALES CLEANER ---
@app.post("/tools/clean-sales")
async def clean_sales_endpoint(
    files: List[UploadFile] = File(...), 
    format: Optional[str] = Form("csv"),
    current_user = Depends(get_current_active_user)
):
    try:
        files_content = []
        for f in files:
            content = await f.read()
            files_content.append((f.filename, content))
            
        df_result = await process_sales_clean(files_content)
        
        if df_result.empty:
            raise HTTPException(status_code=400, detail="No valid data found in files")
            
        # Calculate Date Range for Filename
        min_date = "Inicio"
        max_date = "Fin"
        try:
            if 'Fecha' in df_result.columns:
                dates = pd.to_datetime(df_result['Fecha'], errors='coerce').dropna()
                if not dates.empty:
                    min_date = dates.min().strftime('%Y-%m-%d')
                    max_date = dates.max().strftime('%Y-%m-%d')
        except: pass

        if format == "xlsx":
            filename = f"Ventas limpias {min_date} al {max_date}.xlsx"
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_result.to_excel(writer, index=False)
            output.seek(0)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            response_content = iter([output.getvalue()])
        else:
            filename = f"Ventas limpias {min_date} al {max_date}.csv"
            stream = io.StringIO()
            df_result.to_csv(stream, index=False, encoding='utf-8-sig')
            media_type = "text/csv"
            response_content = iter([stream.getvalue()])

        response = StreamingResponse(response_content, media_type=media_type)
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ANALYSIS CLEANER ---
@app.post("/tools/clean-analysis")
async def clean_analysis_endpoint(
    files: List[UploadFile] = File(...),
    format: Optional[str] = Form("xlsx"), # Default to Excel as it has multiple sheets
    current_user = Depends(get_current_active_user)
):
    try:
        files_content = []
        for f in files:
            content = await f.read()
            files_content.append((f.filename, content))
            
        results, min_d, max_d = procesar_analisis(files_content)
        
        if not results:
             raise HTTPException(status_code=400, detail="No valid data found for analysis")

        # Filename logic
        range_str = ""
        if min_d and max_d:
            range_str = f" {min_d} al {max_d}"
        
        if format == "csv":
            # For CSV, we can only return one sheet or a zip. 
            # Given the requirement, let's return the "TOTAL_GENERAL" sheet or concatenated?
            # Usually analysis implies the multi-sheet report. 
            # If user forces CSV, let's return the main 'TOTAL_GENERAL' table.
            filename = f"Reporte de ventas{range_str}.csv"
            stream = io.StringIO()
            # If TOTAL_GENERAL exists
            if "TOTAL_GENERAL" in results:
                results["TOTAL_GENERAL"].to_csv(stream, index=False, encoding='utf-8-sig')
            else:
                # Fallback to first available
                list(results.values())[0].to_csv(stream, index=False, encoding='utf-8-sig')
            
            media_type = "text/csv"
            response_content = iter([stream.getvalue()])
        else:
            filename = f"Reporte de ventas{range_str}.xlsx"
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for sheet_name, df in results.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            output.seek(0)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            response_content = iter([output.getvalue()])

        response = StreamingResponse(response_content, media_type=media_type)
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- PRODUCTION CLEANER ---
@app.post("/tools/clean-production")
async def clean_production_endpoint(
    files: List[UploadFile] = File(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    format: Optional[str] = Form("csv"),
    current_user = Depends(get_current_active_user)
):
    try:
        files_content = []
        for f in files:
            content = await f.read()
            files_content.append((f.filename, content))
            
        df_result = procesar_produccion(files_content)
        
        if df_result.empty:
            raise HTTPException(status_code=400, detail="No valid production data found")
            
        # Filename logic
        range_str = ""
        if start_date and end_date:
            range_str = f" {start_date} al {end_date}"
        
        if format == "xlsx":
            filename = f"Produccion del Periodo{range_str}.xlsx"
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_result.to_excel(writer, index=False)
            output.seek(0)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            response_content = iter([output.getvalue()])
        else:
            filename = f"Produccion del Periodo{range_str}.csv"
            stream = io.StringIO()
            df_result.to_csv(stream, index=False, encoding='utf-8-sig')
            media_type = "text/csv"
            response_content = iter([stream.getvalue()])

        response = StreamingResponse(response_content, media_type=media_type)
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Register Analysis Endpoint
app.post("/tools/data-analysis")(data_analysis_endpoint)

# --- PINNING FUNCTIONALITY ---
@app.get("/tools/pinned-analysis")
async def get_pinned_analysis(current_user = Depends(get_current_active_user)):
    user_data = users_db.get(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
        
    return user_data.get("pinned_analysis", None)

@app.post("/tools/pin-analysis")
async def pin_analysis(
    data: dict = Body(...),
    current_user = Depends(get_current_active_user)
):
    try:
        if current_user.username not in users_db:
             raise HTTPException(status_code=404, detail="User not found")
             
        users_db[current_user.username]["pinned_analysis"] = data
        save_users()
        return {"message": "Analysis pinned successfully"}
    except Exception as e:
        print(f"Error pinning analysis: {e}")
        raise HTTPException(status_code=500, detail="Failed to save analysis")

@app.delete("/tools/pinned-analysis")
async def unpin_analysis(current_user = Depends(get_current_active_user)):
    try:
        if current_user.username not in users_db:
             raise HTTPException(status_code=404, detail="User not found")
             
        users_db[current_user.username]["pinned_analysis"] = None
        save_users()
        return {"message": "Analysis unpinned successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to remove analysis")
