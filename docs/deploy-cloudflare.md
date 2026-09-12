# Despliegue estático anterior: archivado

La migración a Dash reemplaza la aplicación React y retira su configuración de Vite/Wrangler. La decisión vigente está en [ADR 0003](adr/0003-python-dash-hub.md).

El hub se ejecuta como un servicio Python con Dash y FastAPI en Uvicorn. Su contenedor incluye la interfaz, assets locales y API; consultar [despliegue del hub](despliegue-backend.md) y [desarrollo local](desarrollo.md).

Esta migración del repositorio no publica un sitio ni modifica DNS, secretos, cuentas o recursos existentes de Cloudflare. Los antiguos comandos de compilación y publicación estática ya no forman parte del proyecto.
