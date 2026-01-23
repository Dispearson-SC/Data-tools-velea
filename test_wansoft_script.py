import asyncio
import sys
import pandas as pd
import io
import base64
from playwright.async_api import async_playwright

# Config
SUBSIDIARY_START = 8447
SUBSIDIARY_END = 8458
EXCLUDED_IDS = [8457]
REPORT_URL = "https://www.wansoft.net/Wansoft.Web/Reports/ExportSalesDetailReport"
LOGIN_URL = "https://www.wansoft.net/Wansoft.Web/"

async def run_download_test():
    print("Iniciando prueba de descarga Wansoft (Script Directo)")
    username = "auditoria@eltamalgourmet.com"
    password = "P4170.rar"
    start_date = "2026-01-19"
    end_date = "2026-01-22"

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True) # Change to False if you want to see it
        context = await browser.new_context()
        page = await context.new_page()

        try:
            print(f"Navegando a {LOGIN_URL}...")
            await page.goto(LOGIN_URL)
            await page.wait_for_timeout(3000)

            print(f"Intentando login con {username}...")
            await page.fill('#UserName', username)
            await page.fill('#Password', password)
            await page.click('input[type="submit"]')
            
            await page.wait_for_load_state('networkidle')
            
            if "Login" in page.url:
                print("ERROR: Login fallido. Seguimos en la página de login.")
                try:
                    error = await page.inner_text('.validation-summary-errors')
                    print(f"Mensaje de error: {error}")
                except: pass
                return

            print("Login exitoso! Obteniendo cookies...")
            cookies = await context.cookies()
            
            # Start Download Loop
            print("Iniciando descargas...")
            for sub_id in range(SUBSIDIARY_START, SUBSIDIARY_END + 1):
                if sub_id in EXCLUDED_IDS:
                    continue
                
                print(f"Descargando ID {sub_id}...")
                
                try:
                    result = await page.evaluate(f"""async () => {{
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
                    }}""")

                    if result.get("error"):
                        print(f"Error HTTP {result['error']} en ID {sub_id}")
                        continue
                    
                    b64_str = result.get('fileBase64') or result.get('FileContents') or result.get('Data')
                    
                    if b64_str:
                        print(f"Exito! Recibidos {len(b64_str)} caracteres de Base64.")
                    else:
                        print(f"Error: No se encontró contenido Base64 en la respuesta.")
                        print(f"Keys recibidas: {list(result.keys())}")

                except Exception as e:
                    print(f"Excepción en descarga {sub_id}: {e}")
                
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Error general: {e}")
        finally:
            await browser.close()
            print("Navegador cerrado.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_download_test())
