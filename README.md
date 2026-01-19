# Velea Data Tools

Sistema integral para análisis de ventas, procesamiento de datos y gestión de producción para Velea Limpieza.

## Stack Tecnológico

- **Frontend**: React, TypeScript, TailwindCSS, Vite
- **Backend**: Python, FastAPI, Pandas
- **Containerización**: Docker, Docker Compose

## Requisitos

- Docker y Docker Compose
- Git

## Instalación y Despliegue (Dockploy / Docker)

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/Dispearson-SC/Data-tools-velea.git
   cd Data-tools-velea
   ```

2. Configurar variables de entorno:
   ```bash
   cp .env.example .env
   # Editar .env con tus claves reales
   ```

3. Construir y levantar contenedores:
   ```bash
   docker-compose up -d --build
   ```

4. Acceder a la aplicación:
   - Frontend: `http://localhost:80` (o el puerto configurado)
   - Backend API: `http://localhost:8000`
   - Documentación API: `http://localhost:8000/docs`

## Estructura del Proyecto

```
.
├── backend/            # API FastAPI y lógica de procesamiento
│   ├── services/       # Módulos de limpieza de datos
│   ├── Dockerfile
│   └── main.py
├── frontend/           # SPA React
│   ├── src/
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── .env.example
```

## Características

- **Análisis de Ventas**: Procesamiento de reportes CSV/Excel.
- **Desglose de Ventas**: Reportes detallados por producto y sucursal.
- **Producción**: Cálculo de necesidades de producción basado en inventarios.
- **Seguridad**: Autenticación JWT y roles de usuario.

## Licencia

Propiedad de Velea Limpieza. Todos los derechos reservados.
