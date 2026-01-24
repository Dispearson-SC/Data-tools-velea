import asyncio
import base64
import io
import pandas as pd
from playwright.async_api import async_playwright
from typing import List, Tuple
import traceback

# --- CONFIGURACIÓN ---
SUBSIDIARY_START = 8447
SUBSIDIARY_END = 8458
EXCLUDED_IDS = [8457]
REPORT_URL = "https://www.wansoft.net/Wansoft.Web/Reports/ExportSalesDetailReport"
LOGIN_URL = "https://www.wansoft.net/Wansoft.Web/"

async def get_wansoft_session_cookies(username, password):
    """
    Inicia sesión en Wansoft usando Playwright y devuelve las cookies.
    """
    print(f"[WANSOFT] Iniciando navegador para login de usuario: {username}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1. Login
            print(f"[WANSOFT] Navegando a {LOGIN_URL}")
            await page.goto(LOGIN_URL)
            await page.wait_for_timeout(3000) # Espera de seguridad
            
            print("[WANSOFT] Llenando credenciales...")
            await page.fill('#UserName', username)
            await page.fill('#Password', password)
            await page.click('input[type="submit"]')
            
            print("[WANSOFT] Esperando navegación post-login...")
            await page.wait_for_load_state('networkidle')
            
            # Verificar si entramos (checkeo simple)
            current_url = page.url
            print(f"[WANSOFT] URL actual post-login: {current_url}")
            
            if "Login" in current_url:
                # Intenta ver si hay mensaje de error
                try:
                    error_msg = await page.inner_text('.validation-summary-errors')
                    print(f"[WANSOFT] Mensaje de error en página: {error_msg}")
                except:
                    pass
                raise Exception("Login fallido. Verifica credenciales (sigues en página de Login).")

            cookies = await context.cookies()
            print(f"[WANSOFT] Login exitoso. Cookies obtenidas: {len(cookies)}")
            return cookies
            
        except Exception as e:
            print(f"[WANSOFT] Error en login: {e}")
            traceback.print_exc()
            raise e
        finally:
            await browser.close()

async def download_reports_raw(cookies, start_date, end_date, progress_callback=None) -> List[Tuple[str, bytes]]:
    """
    Descarga los reportes iterando por ID y devuelve una lista de (filename, bytes).
    progress_callback: function(message, percent)
    """
    print(f"[WANSOFT] Iniciando descarga de reportes {start_date} a {end_date}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Cargamos cookies
        context = await browser.new_context()
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        # Navegamos a cualquier pagina dentro del dominio para activar cookies antes del fetch
        if progress_callback: progress_callback("Conectando al servidor de reportes...", 5)
        print("[WANSOFT] Navegando al home para activar cookies...")
        await page.goto(LOGIN_URL) 
        
        downloaded_files = []
        
        # Calculate total steps for progress
        total_subs = SUBSIDIARY_END - SUBSIDIARY_START + 1
        processed_count = 0

        for sub_id in range(SUBSIDIARY_START, SUBSIDIARY_END + 1):
            processed_count += 1
            current_progress = 10 + int((processed_count / total_subs) * 80) # 10% to 90%
            
            if sub_id in EXCLUDED_IDS:
                print(f"[WANSOFT] Skipping ID {sub_id} (Excluido)")
                if progress_callback: progress_callback(f"Omitiendo sucursal excluida ({sub_id})...", current_progress)
                continue
                
            print(f"[WANSOFT] Descargando ID: {sub_id}...")
            if progress_callback: progress_callback(f"Descargando sucursal ID {sub_id}...", current_progress)
            
            try:
                # Ejecutar fetch en el contexto del navegador
                result = await page.evaluate(f"""async () => {{
                    try {{
                        const params = new URLSearchParams();
                        params.append('subsidiaryId', '{sub_id}');
                        params.append('startDate', '{start_date}');
                        params.append('endDate', '{end_date}');

                        const res = await fetch('{REPORT_URL}', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                'X-Requested-With': 'XMLHttpRequest'
                            }},
                            body: params
                        }});
                        
                        if (!res.ok) return {{ error: res.status, statusText: res.statusText }};
                        return await res.json();
                    }} catch (err) {{
                        return {{ error: 'JS Exception', details: err.toString() }};
                    }}
                }}""")
                
                if result.get("error"):
                    print(f"[WANSOFT] Error HTTP/JS {result['error']} en ID {sub_id}: {result.get('statusText') or result.get('details')}")
                    continue

                # Extraer Base64
                b64_str = result.get('fileBase64') or result.get('FileContents') or result.get('Data')
                
                if b64_str:
                    file_bytes = base64.b64decode(b64_str)
                    filename = f"Reporte_{sub_id}_{start_date}_{end_date}.xlsx"
                    downloaded_files.append((filename, file_bytes))
                    print(f"[WANSOFT] ID {sub_id} descargado correctamente. Bytes: {len(file_bytes)}")
                else:
                    print(f"[WANSOFT] No se encontró base64 válido para ID {sub_id}. Keys encontradas: {list(result.keys())}")

            except Exception as e:
                print(f"[WANSOFT] Error descargando ID {sub_id}: {e}")
                traceback.print_exc()
            
            # Pequeña pausa para no saturar
            await asyncio.sleep(0.5)
            
        await browser.close()
        return downloaded_files
