
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
import io
import os
import shutil
import pandas as pd
from typing import List, Optional
from auth import router as auth_router, get_current_active_user, users_db, save_users
from services.sales_cleaner import process_sales_clean, extract_df_and_sucursal
from services.analysis_cleaner import procesar_analisis
from services.production_cleaner import procesar_produccion
from services.breakdown_service import process_breakdown
from services.utils import leer_archivo_base
from analysis_service import data_analysis_endpoint

app = FastAPI(title="Velea Limpieza API")

# Configuration
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# CORS
origins = [
    "http://localhost:5173", # Vite Frontend
    "http://localhost:3000",
    "https://velea.farone.cloud", # Production Domain
    "https://app.farone.cloud",   # Alternative Production Domain
    "https://farone.cloud",       # Root Domain
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

# --- PINNING FUNCTIONALITY (UPDATED) ---

@app.get("/tools/pinned-analysis")
async def get_pinned_analysis(current_user = Depends(get_current_active_user)):
    user_data = users_db.get(current_user.username)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Return both data and file info if exists
    return {
        "data": user_data.get("pinned_analysis", None),
        "file_info": user_data.get("pinned_file_info", None)
    }

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

@app.post("/tools/upload-pinned-file")
async def upload_pinned_file(
    file: UploadFile = File(...),
    current_user = Depends(get_current_active_user)
):
    try:
        user_dir = os.path.join(UPLOAD_DIR, current_user.username)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            
        file_path = os.path.join(user_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Update user DB with file info
        users_db[current_user.username]["pinned_file_info"] = {
            "filename": file.filename,
            "path": file_path,
            "uploaded_at": pd.Timestamp.now().isoformat()
        }
        save_users()
        
        return {"message": "File pinned successfully", "filename": file.filename}
    except Exception as e:
        print(f"Error uploading pinned file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload pinned file")

@app.delete("/tools/pinned-analysis")
async def unpin_analysis(current_user = Depends(get_current_active_user)):
    try:
        if current_user.username not in users_db:
             raise HTTPException(status_code=404, detail="User not found")
             
        # Clear both analysis data and file info
        users_db[current_user.username]["pinned_analysis"] = None
        users_db[current_user.username]["pinned_file_info"] = None
        
        # Optionally delete file? Maybe keep it for history or just overwrite next time.
        # Let's clean up to save space.
        user_dir = os.path.join(UPLOAD_DIR, current_user.username)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir) # Remove all user files
            
        save_users()
        return {"message": "Analysis and file unpinned successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to remove analysis")

# --- BREAKDOWN ENDPOINT ---

@app.post("/tools/breakdown")
async def breakdown_endpoint(
    files: Optional[List[UploadFile]] = File(None),
    use_pinned_file: bool = Form(False),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    sucursales: Optional[str] = Form(None), # Comma separated list
    view_mode: str = Form("daily"), # daily, weekly, monthly
    product_filter: Optional[str] = Form(None), # Comma separated list
    category_filter: Optional[str] = Form(None), # Comma separated list
    format: Optional[str] = Form(None), # csv or xlsx, if present, returns file
    current_user = Depends(get_current_active_user)
):
    try:
        files_content = []
        
        # 1. Load Files (Uploaded OR Pinned)
        if use_pinned_file:
            user_data = users_db.get(current_user.username)
            pinned_info = user_data.get("pinned_file_info")
            
            if not pinned_info or not os.path.exists(pinned_info["path"]):
                raise HTTPException(status_code=400, detail="No pinned file found. Please upload a file or pin one in Analysis.")
                
            # Read local file
            with open(pinned_info["path"], "rb") as f:
                content = f.read()
                files_content.append((pinned_info["filename"], content))
        elif files:
            for f in files:
                content = await f.read()
                files_content.append((f.filename, content))
        else:
             raise HTTPException(status_code=400, detail="No files provided.")

        # 2. Parse Filters
        sucursales_list = [s.strip() for s in sucursales.split(',')] if sucursales else None
        product_list = [p.strip() for p in product_filter.split(',')] if product_filter else None
        category_list = [c.strip() for c in category_filter.split(',')] if category_filter else None

        # 3. Process
        result = await process_breakdown(
            files_content,
            start_date=start_date,
            end_date=end_date,
            sucursales=sucursales_list,
            view_mode=view_mode,
            product_filter=product_list,
            category_filter=category_list
        )
        
        # 4. Export if format requested
        if format:
            data = result["data"]
            columns = result["columns"]
            row_key = result["row_key"]
            
            if not data:
                raise HTTPException(status_code=400, detail="No data to export")
                
            df_export = pd.DataFrame(data)
            
            # Reorder columns to match UI: Row Key + Date Columns
            final_cols = [row_key] + columns
            # Ensure columns exist in DF
            existing_cols = [c for c in final_cols if c in df_export.columns]
            df_export = df_export[existing_cols]
            
            # Filename logic
            range_str = ""
            if start_date and end_date:
                range_str = f"_{start_date}_al_{end_date}"
            elif not start_date and not end_date and "data" in result:
                 # Try to guess range from columns if they are dates
                 if columns:
                     range_str = f"_{columns[0]}_al_{columns[-1]}"

            if format == "xlsx":
                filename = f"Desglose_Ventas{range_str}.xlsx"
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_export.to_excel(writer, index=False)
                output.seek(0)
                media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                response_content = iter([output.getvalue()])
            else: # csv
                filename = f"Desglose_Ventas{range_str}.csv"
                stream = io.StringIO()
                df_export.to_csv(stream, index=False, encoding='utf-8-sig')
                media_type = "text/csv"
                response_content = iter([stream.getvalue()])

            response = StreamingResponse(response_content, media_type=media_type)
            response.headers["Content-Disposition"] = f"attachment; filename={filename}"
            return response
        
        return result

    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
