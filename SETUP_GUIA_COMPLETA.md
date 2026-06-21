# 🚀 GUÍA SETUP COMPLETO - BALMACEDA MARKET POS (100% GRATIS)

## ✅ LO QUE NECESITAS

- **PostgreSQL Online** (GRATIS): Neon.tech, Railway.app, o similar
- **Streamlit** (GRATIS): Cloud o tu computadora
- **Python 3.9+** (GRATIS): Instalado en tu compu
- **Excel** (GRATIS): Que ya tienes

**COSTO MENSUAL: $0 completamente**

---

## 📋 PASO 1: Crear Base de Datos PostgreSQL Online (10 min)

### Opción A: **Neon.tech** (RECOMENDADO - Más fácil)

1. Ir a https://neon.tech
2. Clic en "Sign Up" → Crear cuenta con email
3. Crear proyecto nuevo
4. Copiar **Connection String** (se ve así):
   ```
   postgresql://user:password@host/database
   ```
5. Guardar en un archivo de texto

### Opción B: Railway.app

1. Ir a https://railway.app
2. Sign up → Connect GitHub (opcional)
3. Create → PostgreSQL
4. Ver variables de entorno:
   - DB_HOST
   - DB_USER
   - DB_PASSWORD
   - DB_NAME

### Opción C: Vercel Postgres

1. Ir a https://vercel.com/postgres
2. Create Database
3. Copiar credenciales

---

## 📊 PASO 2: Ejecutar Schema SQL (5 min)

### En Neon.tech:

1. Ir a SQL Editor en tu dashboard
2. Copiar TODO el contenido de **BALMACEDA_SCHEMA_POSTGRESQL.sql**
3. Pegarlo en el editor
4. Clic **Execute**
5. ✅ Listo! Base de datos creada

### En Railway o Vercel:

1. Ir a su SQL Editor
2. Mismo proceso
3. Ejecutar script

---

## 💻 PASO 3: Setup en tu Computadora (15 min)

### 3.1 Descargar archivos

```bash
# Crear carpeta del proyecto
mkdir balmaceda-pos
cd balmaceda-pos

# Descargar:
# 1. BALMACEDA_APP_COMPLETA.py
# 2. requirements.txt
# Guardar en carpeta balmaceda-pos
```

### 3.2 Instalar Python (si no lo tienes)

Descargar desde https://www.python.org/downloads/

```bash
# Verificar que funciona
python --version
```

### 3.3 Crear entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3.4 Instalar dependencias

```bash
pip install -r requirements.txt
```

Esperar a que termine (toma ~3 min)

---

## 🔑 PASO 4: Crear archivo .env (5 min)

Crear archivo `.env` en la carpeta `balmaceda-pos`:

```bash
# Windows: Abrir Bloc de notas
# Linux/Mac: nano .env
```

Pegar esto (cambiar con TUS credenciales):

```
DB_HOST=your-host.neon.tech
DB_NAME=neondb
DB_USER=your_user
DB_PASSWORD=your_password
DB_PORT=5432
```

**¿De dónde sacas estos datos?**
- **Neon:** Connection String → copiar host, user, password, dbname
- **Railway:** Variables de entorno en dashboard
- **Vercel:** Postgres dashboard → Connect

**IMPORTANTE:**
- ❌ NO versionar .env a GitHub (agregar a .gitignore)
- ❌ NO compartir con nadie
- ✅ Guardarlo seguro en tu compu

---

## ▶️ PASO 5: Ejecutar la APP (2 min)

```bash
# Asegúrate de estar en la carpeta balmaceda-pos
# Y tener el venv activado

streamlit run BALMACEDA_APP_COMPLETA.py
```

**Output esperado:**
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```

Abrir en navegador: http://localhost:8501

---

## 🔓 PASO 6: Login (1 min)

**Credenciales por defecto:**

```
Usuario: admin
Contraseña: 123456

O:

Usuario: vendedor
Contraseña: 123456
```

✅ **¡Listo! Sistema funcionando**

---

## 📱 FLUJO DE USO DIARIO

### **Durante el día:**

```
1. Creas Excel con ventas:
   Código | Nombre | Cantidad | Precio Unitario | Subtotal
   7501010| Det X  | 5        | 1.50            | 7.50
   7501020| Shamp Y| 3        | 2.80            | 8.40

2. Guardas Excel: VENTAS_2024-12-15.xlsx
```

### **Al final del día:**

```
1. Abres Streamlit (localhost:8501)
2. Vas a "Ventas" → "Cargar Ventas (Excel)"
3. Subes el Excel
4. Clic "Procesar Ventas"
5. ✅ Stock actualizado automático
6. Ver reportes
```

---

## 🛠️ TROUBLESHOOTING

### **"ModuleNotFoundError: No module named 'psycopg2'"**

```bash
pip install psycopg2-binary
```

### **"Connection refused" a la BD**

```
1. Verificar credenciales en .env
2. Copiar exactamente de tu proveedor
3. Verificar que BD esté activa
4. Probar conexión en https://www.pgadmin.org/
```

### **"Port 8501 already in use"**

```bash
streamlit run BALMACEDA_APP_COMPLETA.py --server.port 8502
```

### **"FATAL: too many connections"**

Neon tier gratuito limita conexiones. Solución:
- Reiniciar aplicación
- O agregarse a plan pago ($15/mes)

### **Excel no se procesa**

```
Verificar:
1. Columnas exactas: Código, Nombre, Cantidad, Precio Unitario, Subtotal
2. No mayúsculas fijas
3. Archivo es .xlsx o .csv
4. Códigos existen en BD
```

---

## 📊 ESTRUCTURA DE CARPETA

```
balmaceda-pos/
├── BALMACEDA_APP_COMPLETA.py     ← Aplicación
├── BALMACEDA_SCHEMA_POSTGRESQL.sql ← Schema (ya ejecutado)
├── requirements.txt                ← Dependencias
├── .env                           ← TUS credenciales (NO compartir)
├── .gitignore                     ← Para no versionar .env
└── venv/                          ← Ambiente virtual
```

---

## 🚀 DEPLOY EN STREAMLIT CLOUD (Opcional)

Si quieres acceder desde cualquier lugar sin ejecutar tu compu:

### 1. Subir a GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git push origin main
```

### 2. Crear cuenta Streamlit Cloud

- Ir a https://streamlit.io/cloud
- Sign up → Conectar GitHub
- Deploy: `BALMACEDA_APP_COMPLETA.py`

### 3. Agregar secrets

En Streamlit Cloud:
- Settings → Secrets
- Pegar contenido de .env

### 4. Tu URL será:
```
https://balmaceda-market-pos.streamlit.app
```

---

## 📈 MÓDULOS DISPONIBLES

**Admin:**
- 📊 Dashboard (KPIs, gráficos)
- 📦 Productos (crear, editar, buscar)
- 🛍️ Ventas (cargar Excel)
- 🚚 Compras (registrar compras)
- 📋 Inventario (ver stock, movimientos)
- 📈 Reportes (ventas, análisis, márgenes)

**Vendedor:**
- 📊 Dashboard (view-only)
- 📦 Productos (buscar)
- 🛍️ Ventas (cargar Excel)
- 📋 Inventario (consultar)

---

## 🔐 SEGURIDAD IMPORTANTE

```
❌ NUNCA:
- Compartir .env
- Guardar credenciales en código
- Poner BD password en comentarios
- Versionar .env a Git

✅ SIEMPRE:
- Guardar .env en .gitignore
- Usar variables de entorno
- Cambiar contraseñas de usuarios después
- Hacer backups de BD
```

---

## 📱 CARGAR EXCEL DE VENTAS - FORMATO EXACTO

```
Tabla en Excel:

| Código    | Nombre        | Cantidad | Precio Unitario | Subtotal |
|-----------|---------------|----------|-----------------|----------|
| 7501010   | Detergente X  | 5        | 1.50            | 7.50     |
| 7501020   | Shampoo Y     | 3        | 2.80            | 8.40     |
| 7501030   | Cloro Z       | 2        | 0.95            | 1.90     |
|           |               |          |                 | TOTAL:   |
|           |               |          |                 | 17.80    |

Notas:
- Encabezado en fila 1
- Nombres EXACTOS de columnas
- Códigos deben existir en BD
- Guardar como .xlsx
```

---

## 📞 SOPORTE

**Si algo no funciona:**

1. Verificar que venv está activado
2. Verificar .env con credenciales correctas
3. Reiniciar Streamlit: `Ctrl+C` → `streamlit run ...`
4. Limpiar cache: `streamlit cache clear`
5. Reiniciar compu (último recurso)

---

## ✨ ¿LO SIGUIENTE?

Después de que funcione:

1. **Crear tus productos** (Productos → Crear)
2. **Cargar inventario inicial** (agregar stock manualmente)
3. **Registrar primeras ventas** (cargar Excel)
4. **Ver reportes** (Reportes → Ventas)
5. **Hacer backups** de BD regularmente

---

## 🎯 CHECKLIST FINAL

- [ ] PostgreSQL online creado (Neon/Railway/Vercel)
- [ ] Schema SQL ejecutado
- [ ] Python instalado en compu
- [ ] Dependencias instaladas (pip install)
- [ ] Archivo .env creado con credenciales
- [ ] Streamlit ejecutándose (localhost:8501)
- [ ] Login funciona (admin/123456)
- [ ] Dashboard visible
- [ ] Módulos accesibles

---

**¡LISTO! Tu sistema POS está 100% operativo, sin costo mensual.**

Cualquier duda, revisar carpeta de archivos entregados.

---

**Versión:** 1.0.0 (MVP)  
**Estado:** ✅ Listo para producción  
**Costo:** $0 completamente
