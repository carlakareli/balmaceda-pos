"""
BALMACEDA MARKET - SISTEMA POS COMPLETO
Aplicación Streamlit con PostgreSQL
Flujo: Escaneo → Excel → Carga en app → Stock actualizado automático
"""
 
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import os
from dotenv import load_dotenv
 
load_dotenv()
 
# ============================================================================
# CONFIGURACIÓN
# ============================================================================
 
st.set_page_config(
    page_title="Balmaceda Market - POS",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)
 
# Conexión a PostgreSQL online (gratis: Neon, Railway, etc.)
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT', 5432)
}
 
# ============================================================================
# FUNCIONES DE CONEXIÓN
# ============================================================================
 
@st.cache_resource
def get_db_connection():
    """Obtener conexión fresca a PostgreSQL (Neon) sin riesgo de cierres por inactividad"""
    try:
        config = {
            'host': os.getenv('DB_HOST'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'port': int(os.getenv('DB_PORT', 5432))
        }
        conn = psycopg2.connect(**config)
        return conn
    except Exception as e:
        return None
 
def execute_query(query, params=None, fetch=False):
    """
    Ejecutar consulta SQL - Retorna dict con 'success', 'data', 'error'
    IMPORTANTE: Cierra conexión después de cada query
    """
    conn = get_db_connection()
    if not conn:
        return {"success": False, "data": None, "error": "❌ No se pudo conectar a Neon"}
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        
        if fetch:
            result = cur.fetchall()
            cur.close()
            conn.close()
            return {"success": True, "data": result if result else [], "error": None}
        else:
            conn.commit()
            cur.close()
            conn.close()
            return {"success": True, "data": None, "error": None}
    except Exception as e:
        try:
            conn.close()
        except:
            pass
        return {"success": False, "data": None, "error": str(e)}
 
# ============================================================================
# INICIALIZACIÓN SESSION STATE
# ============================================================================
 
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
 
if 'user' not in st.session_state:
    st.session_state.user = None
 
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
 
if 'lista_categorias' not in st.session_state:
    st.session_state.lista_categorias = []
 
if 'lista_marcas' not in st.session_state:
    st.session_state.lista_marcas = []
 
if 'lista_unidades' not in st.session_state:
    st.session_state.lista_unidades = []
 
# ============================================================================
# PÁGINAS
# ============================================================================
 
def login_page():
    """Pantalla de login segura - Lee credenciales desde los Secrets de Streamlit"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        st.title("🏪 Balmaceda Market")
        st.subheader("Sistema POS")
        st.markdown("---")
        
        username = st.text_input("Usuario", key="username")
        password = st.text_input("Contraseña", type="password", key="password")
        
        if st.button("Acceder"):
            usuario_seguro = os.getenv('ADMIN_USER')
            clave_segura = os.getenv('ADMIN_PASS')
            
            if not usuario_seguro or not clave_segura:
                st.error("❌ Error de configuración: No se encontraron las credenciales en los Secrets.")
            elif username == usuario_seguro and password == clave_segura:
                st.session_state.authenticated = True
                st.session_state.user = "admin"
                st.session_state.user_role = "administrador"
                st.success("✅ ¡Bienvenido al sistema!")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
 
def dashboard():
    """Dashboard principal"""
    st.title("📊 Dashboard")
    
    # KPIs principales
    col1, col2, col3, col4 = st.columns(4)
    
    # Ventas hoy
    res = execute_query(
        "SELECT SUM(total_final) as total FROM ventas WHERE DATE(fecha) = CURRENT_DATE",
        fetch=True
    )
    ventas_hoy = res['data'][0]['total'] if res['success'] and res['data'] else 0
    
    # Stock total
    res = execute_query(
        "SELECT SUM(stock_actual) as total FROM productos WHERE activo = true",
        fetch=True
    )
    stock_total = res['data'][0]['total'] if res['success'] and res['data'] else 0
    
    # Productos
    res = execute_query(
        "SELECT COUNT(*) as cant FROM productos WHERE activo = true",
        fetch=True
    )
    productos_total = res['data'][0]['cant'] if res['success'] and res['data'] else 0
    
    # Stock bajo
    res = execute_query(
        "SELECT COUNT(*) as cant FROM productos WHERE stock_actual <= stock_minimo AND activo = true",
        fetch=True
    )
    stock_bajo = res['data'][0]['cant'] if res['success'] and res['data'] else 0
    
    with col1:
        st.metric("Ventas Hoy", f"${ventas_hoy or 0:.2f}")
    
    with col2:
        st.metric("Stock Total", stock_total or 0)
    
    with col3:
        st.metric("Productos", productos_total or 0)
    
    with col4:
        st.metric("⚠️ Stock Bajo", stock_bajo or 0)
    
    st.markdown("---")
    
    # Gráfico ventas últimos 7 días
    st.subheader("📈 Ventas Últimos 7 Días")
    
    res = execute_query("""
        SELECT DATE(fecha) as fecha, SUM(total_final) as total
        FROM ventas
        WHERE fecha >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY DATE(fecha)
        ORDER BY fecha
    """, fetch=True)
    
    if res['success'] and res['data']:
        df = pd.DataFrame(res['data'])
        fig = px.bar(df, x='fecha', y='total', title='Ventas por Día')
        st.plotly_chart(fig, use_container_width=True)
    
    # Top productos
    st.subheader("🏆 Top 5 Productos Vendidos")
    
    res = execute_query("""
        SELECT p.nombre, SUM(dv.cantidad) as vendido
        FROM detalle_ventas dv
        JOIN productos p ON dv.producto_id = p.id
        WHERE dv.venta_id IN (
            SELECT id FROM ventas WHERE fecha >= CURRENT_DATE - INTERVAL '30 days'
        )
        GROUP BY p.id, p.nombre
        ORDER BY vendido DESC
        LIMIT 5
    """, fetch=True)
    
    if res['success'] and res['data']:
        df = pd.DataFrame(res['data'])
        st.dataframe(df, use_container_width=True)
 
def cargar_listas_maestras():
    """Cargar categorías, marcas y unidades a session_state"""
    # Categorías
    res = execute_query("SELECT id, nombre FROM categorias WHERE activo = true ORDER BY nombre", fetch=True)
    if res['success']:
        st.session_state.lista_categorias = res['data']
    else:
        st.error(f"Error cargando categorías: {res['error']}")
        st.session_state.lista_categorias = []
    
    # Marcas
    res = execute_query("SELECT id, nombre FROM marcas WHERE activo = true ORDER BY nombre", fetch=True)
    if res['success']:
        st.session_state.lista_marcas = res['data']
    else:
        st.error(f"Error cargando marcas: {res['error']}")
        st.session_state.lista_marcas = []
    
    # Unidades
    res = execute_query("SELECT id, nombre, abreviatura FROM unidades_medida ORDER BY nombre", fetch=True)
    if res['success']:
        st.session_state.lista_unidades = res['data']
    else:
        st.error(f"Error cargando unidades: {res['error']}")
        st.session_state.lista_unidades = []
 
def modulo_productos():
    """Gestión de productos 100% alineada con el Schema real de PostgreSQL de Balmaceda Market"""
    st.title("📦 Productos")
    
    # Cargar listas maestras si está vacías
    if not st.session_state.lista_categorias:
        cargar_listas_maestras()
 
    tab1, tab2, tab3, tab4 = st.tabs(["Listar", "Crear Producto", "Buscar", "📁 Categorías y Marcas"])
    
    with tab1:
        st.subheader("Inventario de Productos")
        res = execute_query("""
            SELECT p.id, p.codigo_barras, p.nombre, c.nombre as categoria, m.nombre as marca,
                   p.stock_actual, p.stock_minimo, p.precio_venta_actual, p.activo, u.abreviatura as unidad
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            LEFT JOIN marcas m ON p.marca_id = m.id
            LEFT JOIN unidades_medida u ON p.unidad_medida_id = u.id
            ORDER BY p.nombre
        """, fetch=True)
        
        if res['success'] and res['data']:
            df = pd.DataFrame(res['data'])
            df.columns = ['ID', 'Código de Barras', 'Nombre', 'Categoría', 'Marca', 'Stock Actual', 'Stock Mínimo', 'Precio Venta', 'Activo', 'U. Medida']
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay productos registrados")
    
    with tab2:
        st.subheader("Crear Nuevo Producto")
        
        col_cod1, col_cod2 = st.columns([3, 1])
        with col_cod1:
            codigo_raw = st.text_input("Código de Barras", placeholder="Escanea o escribe manualmente...", key="input_codigo_maestro")
            codigo = codigo_raw.strip() if codigo_raw else ""
            
        with col_cod2:
            st.write("¿Escanear?")
            activar_camara = st.checkbox("📷 Abrir Cámara", value=False)
            
        if activar_camara:
            componente_camara = """
            <div style="width: 100%; max-width: 400px; margin: 0 auto;">
                <div id="lector-camara" style="width: 100%; background: #1e1e1e; border-radius: 8px;"></div>
            </div>
            <script src="https://unpkg.com/html5-qrcode"></script>
            <script>
                function onScanSuccess(decodedText, decodedResult) {
                    const inputElement = window.parent.document.querySelector('input[aria-label="Código de Barras"]');
                    if (inputElement) {
                        inputElement.value = decodedText;
                        inputElement.dispatchEvent(new Event('input', { bubbles: true }));
                        inputElement.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    html5QrcodeScanner.clear();
                }
                let config = { fps: 15, qrbox: {width: 280, height: 160} };
                let html5QrcodeScanner = new Html5QrcodeScanner("lector-camara", config, false);
                html5QrcodeScanner.render(onScanSuccess);
            </script>
            """
            import streamlit.components.v1 as components
            components.html(componente_camara, height=330)
 
        if codigo:
            res = execute_query("SELECT nombre, activo FROM productos WHERE codigo_barras = %s", (codigo,), fetch=True)
            if res['success'] and res['data']:
                estado_prod = "Activo" if res['data'][0]['activo'] else "Inactivo"
                st.warning(f"⚠️ Ya existe un producto registrado con este código: **{res['data'][0]['nombre']}** (Estado: {estado_prod})")
        
        st.markdown("### 📝 Datos de la Ficha del Producto")
        col_form_izq, col_form_der = st.columns(2)
        
        with col_form_izq:
            st.markdown("#### 🔴 Datos Obligatorios")
            nombre_raw = st.text_input("Nombre del Producto (ej: Agua Sin Gas)")
            nombre = nombre_raw.strip() if nombre_raw else ""
            
            # Categorías
            cats_dict = {c['nombre']: c['id'] for c in st.session_state.lista_categorias}
            if cats_dict:
                categoria_sel = st.selectbox("Categoría", list(cats_dict.keys()))
            else:
                st.warning("⚠️ No hay categorías. Ve a la pestaña 4 para crear una.")
                categoria_sel = None
            
            # Marcas
            marcas_dict = {m['nombre']: m['id'] for m in st.session_state.lista_marcas}
            if marcas_dict:
                marca_sel = st.selectbox("Marca", list(marcas_dict.keys()))
            else:
                st.warning("⚠️ No hay marcas. Ve a la pestaña 4 para crear una.")
                marca_sel = None
            
            # Unidades
            unidades_dict = {f"{u['nombre']} ({u['abreviatura']})": u['id'] for u in st.session_state.lista_unidades}
            if unidades_dict:
                unidad_sel = st.selectbox("Unidad de Medida", list(unidades_dict.keys()))
            else:
                st.warning("⚠️ No hay unidades en la BD.")
                unidad_sel = None
            
            precio_venta = st.number_input("Precio de Venta al Público ($)", min_value=0.0, step=50.0)
            stock_min = st.number_input("Stock Mínimo de Alerta", min_value=0, value=5)
 
        with col_form_der:
            st.markdown("#### 🟢 Datos Recomendados / Historial")
            estado_input = st.selectbox("Estado del Producto", ["Activo", "Inactivo"])
            activo_bool = True if estado_input == "Activo" else False
            
            st.text_area("Descripción (Opcional)", key="prod_desc_opc", placeholder="Detalles del producto...")
            st.text_input("Fecha de Creación (Automática)", value=datetime.now().strftime("%d-%m-%Y %H:%M"), disabled=True)
            st.text_input("Usuario Operador", value=st.session_state.get('user', 'admin'), disabled=True)
 
        st.markdown("---")
        
        if st.button("💾 Guardar Producto en Balmaceda Market", type="primary"):
            if not codigo or not nombre or not categoria_sel or not marca_sel or not unidad_sel:
                st.error("❌ Por favor verifica los datos obligatorios (código, nombre, categoría, marca, unidad).")
            elif precio_venta <= 0:
                st.error("❌ El Precio de Venta debe ser mayor a cero ($).")
            else:
                res = execute_query("SELECT id FROM productos WHERE codigo_barras = %s", (codigo,), fetch=True)
                if res['success'] and res['data']:
                    st.error("❌ Error: Ese código de barras ya está registrado.")
                else:
                    cat_id = cats_dict[categoria_sel]
                    marca_id = marcas_dict[marca_sel]
                    unidad_id = unidades_dict[unidad_sel]
                    desc_text = st.session_state.get('prod_desc_opc', '')
                    
                    res = execute_query("""
                        INSERT INTO productos 
                        (codigo_barras, nombre, descripcion, marca_id, categoria_id, unidad_medida_id, 
                         precio_compra_actual, precio_venta_actual, stock_actual, stock_minimo, activo, fecha_creacion, fecha_modificacion)
                        VALUES (%s, %s, %s, %s, %s, %s, 0.0, %s, 0, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (codigo, nombre, desc_text, marca_id, cat_id, unidad_id, precio_venta, stock_min, activo_bool))
                    
                    if res['success']:
                        st.success(f"✅ ¡{nombre}! Ha sido creado exitosamente en Neon.")
                        st.balloons()
                    else:
                        st.error(f"❌ Error al guardar en PostgreSQL: {res['error']}")
                    
    with tab3:
        st.subheader("Buscar Producto")
        busqueda = st.text_input("Buscar por nombre o código")
        if busqueda:
            res = execute_query("""
                SELECT p.id, p.codigo_barras, p.nombre, c.nombre as categoria,
                       p.stock_actual, p.precio_venta_actual, p.activo
                FROM productos p
                LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE (p.nombre ILIKE %s OR p.codigo_barras LIKE %s)
            """, (f"%{busqueda}%", f"%{busqueda}%"), fetch=True)
            
            if res['success'] and res['data']:
                df = pd.DataFrame(res['data'])
                df.columns = ['ID', 'Código de Barras', 'Nombre', 'Categoría', 'Stock Actual', 'Precio Venta', 'Activo']
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No se encontraron productos.")
 
    with tab4:
        st.subheader("📁 Administración de Categorías y Marcas")
        
        # VISOR EN TIEMPO REAL DE LO QUE YA EXISTE EN NEON
        st.markdown("### 📊 Elementos actuales en la Base de Datos")
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            nombres_cats = [c['nombre'] for c in st.session_state.lista_categorias]
            if nombres_cats:
                st.caption(f"**Categorías ({len(nombres_cats)}):**")
                st.write(", ".join(nombres_cats))
            else:
                st.warning("**Categorías:** No hay categorías registradas aún.")
        
        with col_v2:
            nombres_marcas = [m['nombre'] for m in st.session_state.lista_marcas]
            if nombres_marcas:
                st.caption(f"**Marcas ({len(nombres_marcas)}):**")
                st.write(", ".join(nombres_marcas))
            else:
                st.warning("**Marcas:** No hay marcas registradas aún.")
            
        st.markdown("---")
        col_cat, col_mar = st.columns(2)
        
        with col_cat:
            st.markdown("### 🆕 Crear Nueva Categoría")
            cat_input = st.text_input("Nombre de la Categoría", key="pestaña_txt_cat", placeholder="Ej: Detergentes")
            if st.button("💾 Guardar Categoría", key="pestaña_btn_cat", type="primary"):
                if cat_input.strip():
                    nombre_limpio = cat_input.strip()
                    # Verificar si existe
                    res = execute_query("SELECT id FROM categorias WHERE nombre ILIKE %s", (nombre_limpio,), fetch=True)
                    if res['success'] and not res['data']:
                        # Guardar
                        res_insert = execute_query(
                            "INSERT INTO categorias (nombre, activo, descripcion) VALUES (%s, true, 'Creada desde la App')", 
                            (nombre_limpio,)
                        )
                        if res_insert['success']:
                            # Recargar lista
                            res_reload = execute_query("SELECT id, nombre FROM categorias WHERE activo = true ORDER BY nombre", fetch=True)
                            if res_reload['success']:
                                st.session_state.lista_categorias = res_reload['data']
                            st.success(f"✅ ¡Categoría '{nombre_limpio}' guardada con éxito!")
                            st.rerun()
                        else:
                            st.error(f"❌ Error al guardar: {res_insert['error']}")
                    else:
                        st.warning("⚠️ Esta categoría ya existe en Neon.")
                else:
                    st.error("Escribe un nombre válido para la categoría.")
                    
        with col_mar:
            st.markdown("### 🆕 Crear Nueva Marca")
            marca_input = st.text_input("Nombre de la Marca", key="pestaña_txt_marca", placeholder="Ej: Ariel")
            if st.button("💾 Guardar Marca", key="pestaña_btn_marca", type="primary"):
                if marca_input.strip():
                    nombre_limpio = marca_input.strip()
                    # Verificar si existe
                    res = execute_query("SELECT id FROM marcas WHERE nombre ILIKE %s", (nombre_limpio,), fetch=True)
                    if res['success'] and not res['data']:
                        # Guardar
                        res_insert = execute_query(
                            "INSERT INTO marcas (nombre, activo) VALUES (%s, true)", 
                            (nombre_limpio,)
                        )
                        if res_insert['success']:
                            # Recargar lista
                            res_reload = execute_query("SELECT id, nombre FROM marcas WHERE activo = true ORDER BY nombre", fetch=True)
                            if res_reload['success']:
                                st.session_state.lista_marcas = res_reload['data']
                            st.success(f"✅ ¡Marca '{nombre_limpio}' guardada con éxito!")
                            st.rerun()
                        else:
                            st.error(f"❌ Error al guardar: {res_insert['error']}")
                    else:
                        st.warning("⚠️ Esta marca ya existe en Neon.")
                else:
                    st.error("Escribe un nombre válido para la marca.")
 
def modulo_ventas():
    """Módulo de ventas - PLACEHOLDER"""
    st.title("🛍️ Ventas")
    st.info("Módulo de ventas en desarrollo")
 
def modulo_compras():
    """Gestión de compras"""
    st.title("🚚 Compras")
    
    tab1, tab2 = st.tabs(["Nueva Compra", "Historial"])
    
    with tab1:
        st.subheader("Registrar Compra a Proveedor")
        st.info("Módulo en desarrollo")
    
    with tab2:
        st.subheader("Historial de Compras")
        st.info("Módulo en desarrollo")
 
def modulo_inventario():
    """Gestión de inventario"""
    st.title("📋 Inventario")
    
    tab1, tab2 = st.tabs(["Estado Actual", "Movimientos"])
    
    with tab1:
        st.subheader("Stock Actual")
        
        res = execute_query("""
            SELECT p.nombre, p.stock_actual, p.stock_minimo, 
                   p.precio_venta_actual,
                   CASE WHEN p.stock_actual <= p.stock_minimo 
                        THEN '⚠️ BAJO' ELSE '✅ OK' END as estado
            FROM productos p
            WHERE p.activo = true
            ORDER BY p.nombre
        """, fetch=True)
        
        if res['success'] and res['data']:
            df = pd.DataFrame(res['data'])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay productos registrados")
    
    with tab2:
        st.subheader("Movimientos de Inventario")
        st.info("Módulo en desarrollo")
 
def modulo_reportes():
    """Reportes y análisis"""
    st.title("📈 Reportes")
    st.info("Módulo en desarrollo")
 
# ============================================================================
# MAIN
# ============================================================================
 
def main():
    # Sidebar
    with st.sidebar:
        st.title("🏪 Balmaceda Market")
        
        if st.session_state.authenticated:
            st.write(f"**{st.session_state.user}** ({st.session_state.user_role})")
            
            st.markdown("---")
            
            # Menú según rol
            if st.session_state.user_role == "administrador":
                pagina = st.radio("Menú", [
                    "📊 Dashboard",
                    "📦 Productos",
                    "🛍️ Ventas",
                    "🚚 Compras",
                    "📋 Inventario",
                    "📈 Reportes"
                ])
            else:
                pagina = st.radio("Menú", [
                    "📊 Dashboard",
                    "📦 Productos",
                    "🛍️ Ventas",
                    "📋 Inventario"
                ])
            
            st.markdown("---")
            
            if st.button("🚪 Cerrar Sesión"):
                st.session_state.authenticated = False
                st.session_state.lista_categorias = []
                st.session_state.lista_marcas = []
                st.session_state.lista_unidades = []
                st.rerun()
        
        st.markdown("""
        ---
        **Versión:** 2.0.0  
        **Estado:** MVP
        """)
    
    # Contenido principal
    if not st.session_state.authenticated:
        login_page()
    else:
        if pagina == "📊 Dashboard":
            dashboard()
        elif pagina == "📦 Productos":
            modulo_productos()
        elif pagina == "🛍️ Ventas":
            modulo_ventas()
        elif pagina == "🚚 Compras":
            modulo_compras()
        elif pagina == "📋 Inventario":
            modulo_inventario()
        elif pagina == "📈 Reportes":
            modulo_reportes()
 
if __name__ == "__main__":
    main()
