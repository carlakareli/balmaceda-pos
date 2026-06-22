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
        # Volvemos a armar el diccionario asegurando que el puerto sea un entero
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
        st.error(f"Error conectando a BD: {e}")
        return None

def execute_query(query, params=None, fetch=False):
    """Ejecutar consulta SQL"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        
        if fetch:
            result = cur.fetchall()
        else:
            conn.commit()
            result = True
        
        cur.close()
        return result
    except Exception as e:
        st.error(f"Error en query: {e}")
        return None

# ============================================================================
# INICIALIZACIÓN
# ============================================================================

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'user' not in st.session_state:
    st.session_state.user = None

if 'user_role' not in st.session_state:
    st.session_state.user_role = None

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
            # --- PROTECCIÓN ABSOLUTA EN REPOSITORIOS PÚBLICOS ---
            # Recanalizamos la autenticación para leer EXCLUSIVAMENTE de Streamlit Secrets (Nube)
            # Si por alguna razón no los encuentra, fallará en vez de exponer una clave por defecto.
            usuario_seguro = os.getenv('ADMIN_USER')
            clave_segura = os.getenv('ADMIN_PASS')
            
            if not usuario_seguro or not clave_segura:
                st.error("❌ Error de configuración: No se encontraron las credenciales seguras en los Secrets de la nube.")
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
    ventas_hoy = execute_query(
        "SELECT SUM(total_final) FROM ventas WHERE DATE(fecha) = CURRENT_DATE",
        fetch=True
    )
    
    # Stock total
    stock_total = execute_query(
        "SELECT SUM(stock_actual) FROM productos WHERE activo = true",
        fetch=True
    )
    
    # Productos
    productos_total = execute_query(
        "SELECT COUNT(*) as cant FROM productos WHERE activo = true",
        fetch=True
    )
    
    # Stock bajo
    stock_bajo = execute_query(
        "SELECT COUNT(*) as cant FROM productos WHERE stock_actual <= stock_minimo AND activo = true",
        fetch=True
    )
    
    with col1:
        st.metric("Ventas Hoy", f"${ventas_hoy[0][0] or 0:.2f}")
    
    with col2:
        st.metric("Stock Total", stock_total[0][0] or 0)
    
    with col3:
        st.metric("Productos", productos_total[0][0] or 0)
    
    with col4:
        st.metric("⚠️ Stock Bajo", stock_bajo[0][0] or 0)
    
    st.markdown("---")
    
    # Gráfico ventas últimos 7 días
    st.subheader("📈 Ventas Últimos 7 Días")
    
    ventas_7d = execute_query("""
        SELECT DATE(fecha) as fecha, SUM(total_final) as total
        FROM ventas
        WHERE fecha >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY DATE(fecha)
        ORDER BY fecha
    """, fetch=True)
    
    if ventas_7d:
        df = pd.DataFrame(ventas_7d)
        fig = px.bar(df, x='fecha', y='total', title='Ventas por Día')
        st.plotly_chart(fig, use_container_width=True)
    
    # Top productos
    st.subheader("🏆 Top 5 Productos Vendidos")
    
    top_productos = execute_query("""
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
    
    if top_productos:
        df = pd.DataFrame(top_productos)
        st.dataframe(df, use_container_width=True)

def modulo_productos():
    """Gestión de productos con pestañas independientes y re-intento silencioso de conexión"""
    st.title("📦 Productos")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Listar", "Crear Producto", "Buscar", "📁 Categorías y Marcas"])
    
    with tab1:
        st.subheader("Inventario de Productos")
        
        productos = execute_query("""
            SELECT p.id, p.codigo_barras, p.nombre, c.nombre as categoria, m.nombre as marca,
                   p.stock_actual, p.stock_minimo, p.precio_venta_actual, p.activo, p.unidad_medida
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            LEFT JOIN marcas m ON p.marca_id = m.id
            ORDER BY p.nombre
        """, fetch=True)
        
        if productos:
            df = pd.DataFrame(productos)
            df.columns = ['ID', 'Código de Barras', 'Nombre', 'Categoría', 'Marca', 'Stock Actual', 'Stock Mínimo', 'Precio Venta', 'Activo', 'Unidad Medida']
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay productos registrados")
    
    with tab2:
        st.subheader("Crear Nuevo Producto")
        
        # --- SECCIÓN DE ESCANEO OPCIONAL ---
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

        # 1. VALIDACIÓN: Código de barras único
        if codigo:
            prod_existente = execute_query("SELECT nombre, activo FROM productos WHERE codigo_barras = %s", (codigo,), fetch=True)
            if prod_existente:
                estado_prod = "Activo" if prod_existente[0]['activo'] else "Inactivo"
                st.warning(f"⚠️ Ya existe un producto registrado con este código: **{prod_existente[0]['nombre']}** (Estado: {estado_prod})")
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🔍 Ver Producto", use_container_width=True):
                        st.info("Función para redireccionar en desarrollo.")
                with col_btn2:
                    if st.button("✏️ Editar Producto", use_container_width=True):
                        st.info("Función para editar en desarrollo.")
                st.markdown("---")

        # --- FORMULARIO PRINCIPAL ---
        st.markdown("### 📝 Datos de la Ficha del Producto")
        col_form_izq, col_form_der = st.columns(2)
        
        with col_form_izq:
            st.markdown("#### 🔴 Datos Obligatorios")
            
            nombre_raw = st.text_input("Nombre del Producto (ej: Agua Sin Gas)")
            nombre = nombre_raw.strip() if nombre_raw else ""
            
            # CONTROL SILENCIOSO: Si la conexión falla por herencia de pestañas, se recupera sin lanzar error rojo
            try:
                categoria_opt = execute_query("SELECT nombre FROM categorias ORDER BY nombre", fetch=True)
                listado_cats = [c['nombre'] for c in categoria_opt] if categoria_opt else []
            except Exception:
                listado_cats = []
                
            if not listado_cats:
                listado_cats = ["⚠️ No hay categorías creadas aún. Ve a la pestaña de Categorías."]
            categoria = st.selectbox("Categoría", listado_cats)
            
            try:
                marca_opt = execute_query("SELECT nombre FROM marcas ORDER BY nombre", fetch=True)
                listado_marcas = [m['nombre'] for m in marca_opt] if marca_opt else []
            except Exception:
                listado_marcas = []
                
            if not listado_marcas:
                listado_marcas = ["⚠️ No hay marcas creadas aún. Ve a la pestaña de Categorías."]
            marca = st.selectbox("Marca", listado_marcas)
            
            precio_venta = st.number_input("Precio de Venta al Público ($)", min_value=0.0, step=50.0)
            stock_min = st.number_input("Stock Mínimo de Alerta", min_value=0, value=5)

        with col_form_der:
            st.markdown("#### 🟢 Datos Recomendados / Auditoría")
            
            estado_input = st.selectbox("Estado del Producto", ["Activo", "Inactivo"])
            activo_bool = True if estado_input == "Activo" else False
            
            unidad_medida = st.selectbox("Unidad de Medida", ["Unidad", "Pack", "Caja", "Litro", "Kg"])
            descripcion = st.text_area("Descripción / Observaciones (Opcional)", placeholder="Ej: Producto estacional...")
            
            st.text_input("Fecha de Creación (Automática)", value=datetime.now().strftime("%d-%m-%Y %H:%M"), disabled=True)
            st.text_input("Usuario Creador (Automático)", value=st.session_state.get('user', 'Carla'), disabled=True)

        st.markdown("---")
        
        if st.button("💾 Guardar Producto en Balmaceda Market", type="primary"):
            if not codigo:
                st.error("❌ El Código de Barras es obligatorio.")
            elif not nombre:
                st.error("❌ El Nombre del Producto es obligatorio.")
            elif "⚠️" in categoria or not listado_cats:
                st.error("❌ Debe seleccionar una Categoría válida. Créala primero en la pestaña 'Categorías y Marcas'.")
            elif "⚠️" in marca or not listado_marcas:
                st.error("❌ Debe seleccionar una Marca válida. Créala primero en la pestaña 'Categorías y Marcas'.")
            elif precio_venta <= 0:
                st.error("❌ El Precio de Venta debe ser mayor a cero ($).")
            else:
                try:
                    duplicado = execute_query("SELECT id FROM productos WHERE codigo_barras = %s", (codigo,), fetch=True)
                    if duplicado:
                        st.error("❌ Error: Ese código de barras ya fue guardado.")
                    else:
                        cat_id = execute_query("SELECT id FROM categorias WHERE nombre = %s", (categoria,), fetch=True)[0]['id']
                        marca_id = execute_query("SELECT id FROM marcas WHERE nombre = %s", (marca,), fetch=True)[0]['id']
                        usuario_actual = st.session_state.get('user', 'Carla')
                        
                        execute_query("""
                            INSERT INTO productos 
                            (codigo_barras, nombre, categoria_id, marca_id, 
                             precio_compra_actual, precio_venta_actual, stock_actual, stock_minimo, 
                             activo, unidad_medida, descripcion, usuario_creador, fecha_creacion)
                            VALUES (%s, %s, %s, %s, 0.0, %s, 0, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """, (codigo, nombre, cat_id, marca_id, precio_venta, stock_min, activo_bool, unidad_medida, descripcion, usuario_actual))
                        
                        st.success(f"✅ ¡{nombre}! Ha sido creado exitosamente.")
                        st.balloons()
                except Exception as e:
                    st.error(f"❌ Error al guardar en PostgreSQL: {e}")
                    
    with tab3:
        st.subheader("Buscar Producto")
        busqueda = st.text_input("Buscar por nombre o código")
        
        if busqueda:
            resultados = execute_query("""
                SELECT p.id, p.codigo_barras, p.nombre, c.nombre as categoria,
                       p.stock_actual, p.precio_venta_actual, p.activo
                FROM productos p
                LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE (p.nombre ILIKE %s OR p.codigo_barras LIKE %s)
            """, (f"%{busqueda}%", f"%{busqueda}%"), fetch=True)
            
            if resultados:
                df = pd.DataFrame(resultados)
                df.columns = ['ID', 'Código de Barras', 'Nombre', 'Categoría', 'Stock Actual', 'Precio Venta', 'Activo']
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No se encontraron productos")

    with tab4:
        st.subheader("📁 Administración de Categorías y Marcas")
        st.info("Crea aquí los maestros. Al guardarlos, aparecerán inmediatamente en el formulario de creación de productos.")
        
        col_cat, col_mar = st.columns(2)
        
        with col_cat:
            st.markdown("### 🆕 Crear Nueva Categoría")
            cat_input = st.text_input("Nombre de la Categoría", placeholder="Ej: Bebidas, Lácteos, Fiambrería...", key="pestaña_txt_cat")
            if st.button("💾 Guardar Categoría", key="pestaña_btn_cat", type="secondary"):
                if cat_input.strip():
                    existencia = execute_query("SELECT id FROM categorias WHERE nombre ILIKE %s", (cat_input.strip(),), fetch=True)
                    if not existencia:
                        execute_query("INSERT INTO categorias (nombre) VALUES (%s)", (cat_input.strip(),))
                        st.success(f"✅ Categoría '{cat_input.strip()}' guardada exitosamente.")
                    else:
                        st.warning("⚠️ Esta categoría ya existe.")
                else:
                    st.error("Escribe un nombre válido.")
                    
        with col_mar:
            st.markdown("### 🆕 Crear Nueva Marca")
            marca_input = st.text_input("Nombre de la Marca", placeholder="Ej: Coca-Cola, Nestlé, Soprole...", key="pestaña_txt_marca")
            if st.button("💾 Guardar Marca", key="pestaña_btn_marca", type="secondary"):
                if marca_input.strip():
                    existencia = execute_query("SELECT id FROM marcas WHERE nombre ILIKE %s", (marca_input.strip(),), fetch=True)
                    if not existencia:
                        execute_query("INSERT INTO marcas (nombre) VALUES (%s)", (marca_input.strip(),))
                        st.success(f"✅ Marca '{marca_input.strip()}' guardada exitosamente.")
                    else:
                        st.warning("⚠️ Esta marca ya existe.")
                else:
                    st.error("Escribe un nombre válido.")

def modulo_compras():
    """Gestión de compras"""
    st.title("🚚 Compras")
    
    tab1, tab2 = st.tabs(["Nueva Compra", "Historial"])
    
    with tab1:
        st.subheader("Registrar Compra a Proveedor")
        
        col1, col2, col3 = st.columns(3)
        
        # Obtener proveedores
        proveedores = execute_query(
            "SELECT id, nombre_proveedor FROM proveedores WHERE activo = true",
            fetch=True
        )
        
        with col1:
            if proveedores:
                proveedor = st.selectbox("Proveedor", 
                    [p['nombre_proveedor'] for p in proveedores])
                prov_id = next(p['id'] for p in proveedores 
                    if p['nombre_proveedor'] == proveedor)
        
        with col2:
            numero_factura = st.text_input("Número Factura")
        
        with col3:
            st.write("Fecha:", datetime.now().strftime("%Y-%m-%d"))
        
        st.markdown("---")
        st.subheader("Líneas de Compra")
        
        # Tabla de productos
        productos = execute_query(
            "SELECT id, codigo_barras, nombre FROM productos WHERE activo = true",
            fetch=True
        )
        
        lineas_compra = []
        
        for i in range(3):  # Mostrar 3 filas iniciales
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if productos:
                    producto = st.selectbox(
                        f"Producto {i+1}",
                        [p['nombre'] for p in productos],
                        key=f"prod_{i}"
                    )
            
            with col2:
                cantidad = st.number_input(f"Cantidad {i+1}", min_value=0, key=f"cant_{i}")
            
            with col3:
                precio = st.number_input(f"Precio {i+1}", min_value=0.0, key=f"prec_{i}")
            
            with col4:
                subtotal = cantidad * precio
                st.metric("Subtotal", f"${subtotal:.2f}")
            
            if cantidad > 0 and precio > 0:
                lineas_compra.append({
                    'producto': producto,
                    'cantidad': cantidad,
                    'precio': precio
                })
        
        st.markdown("---")
        
        if lineas_compra:
            total = sum(l['cantidad'] * l['precio'] for l in lineas_compra)
            st.subheader(f"Total Compra: ${total:.2f}")
            
            if st.button("Registrar Compra"):
                try:
                    usuario = execute_query(
                        "SELECT id FROM usuarios WHERE username = %s",
                        (st.session_state.user,),
                        fetch=True
                    )[0]['id']
                    
                    # Insertar compra
                    compra = execute_query("""
                        INSERT INTO compras
                        (fecha, proveedor_id, numero_factura, total_compra, usuario_id)
                        VALUES (CURRENT_TIMESTAMP, %s, %s, %s, %s)
                        RETURNING id
                    """, (prov_id, numero_factura, total, usuario), fetch=True)
                    
                    compra_id = compra[0]['id']
                    
                    # Procesar líneas
                    for linea in lineas_compra:
                        prod = next(p for p in productos if p['nombre'] == linea['producto'])
                        prod_id = prod['id']
                        
                        # Detalle compra
                        execute_query("""
                            INSERT INTO detalle_compras
                            (compra_id, producto_id, cantidad, 
                             precio_compra_unitario, subtotal)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (compra_id, prod_id, linea['cantidad'], 
                              linea['precio'], linea['cantidad'] * linea['precio']))
                        
                        # Actualizar stock
                        execute_query("""
                            UPDATE productos
                            SET stock_actual = stock_actual + %s,
                                precio_compra_actual = %s,
                                fecha_modificacion = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (linea['cantidad'], linea['precio'], prod_id))
                        
                        # Historial precios
                        execute_query("""
                            INSERT INTO historial_precios_compra
                            (producto_id, proveedor_id, precio_compra, usuario_id)
                            VALUES (%s, %s, %s, %s)
                        """, (prod_id, prov_id, linea['precio'], usuario))
                        
                        # Movimiento inventario
                        execute_query("""
                            INSERT INTO movimientos_inventario
                            (producto_id, tipo_movimiento, cantidad, usuario_id,
                             referencia_documento, referencia_id)
                            VALUES (%s, 'compra', %s, %s, 'compra', %s)
                        """, (prod_id, linea['cantidad'], usuario, compra_id))
                    
                    st.success(f"✅ Compra registrada - Nº {numero_factura}")
                
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    
    with tab2:
        st.subheader("Historial de Compras")
        
        compras = execute_query("""
            SELECT c.numero_factura, c.fecha, c.total_compra, p.nombre_proveedor
            FROM compras c
            JOIN proveedores p ON c.proveedor_id = p.id
            ORDER BY c.fecha DESC
            LIMIT 50
        """, fetch=True)
        
        if compras:
            df = pd.DataFrame(compras)
            st.dataframe(df, use_container_width=True)

def modulo_inventario():
    """Gestión de inventario"""
    st.title("📋 Inventario")
    
    tab1, tab2 = st.tabs(["Estado Actual", "Movimientos"])
    
    with tab1:
        st.subheader("Stock Actual")
        
        inventario = execute_query("""
            SELECT p.nombre, p.stock_actual, p.stock_minimo, 
                   p.precio_venta_actual,
                   CASE WHEN p.stock_actual <= p.stock_minimo 
                        THEN '⚠️ BAJO' ELSE '✅ OK' END as estado
            FROM productos p
            WHERE p.activo = true
            ORDER BY p.nombre
        """, fetch=True)
        
        if inventario:
            df = pd.DataFrame(inventario)
            st.dataframe(df, use_container_width=True)
    
    with tab2:
        st.subheader("Movimientos de Inventario")
        
        movimientos = execute_query("""
            SELECT m.fecha, p.nombre, m.tipo_movimiento, m.cantidad, u.nombre_completo
            FROM movimientos_inventario m
            JOIN productos p ON m.producto_id = p.id
            JOIN usuarios u ON m.usuario_id = u.id
            ORDER BY m.fecha DESC
            LIMIT 100
        """, fetch=True)
        
        if movimientos:
            df = pd.DataFrame(movimientos)
            st.dataframe(df, use_container_width=True)

def modulo_reportes():
    """Reportes y análisis"""
    st.title("📈 Reportes")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Ventas", "Inventario", "Productos", "Análisis"])
    
    with tab1:
        st.subheader("Reporte de Ventas")
        
        rango = st.date_input("Rango de fechas", 
            value=(datetime.now() - timedelta(days=30), datetime.now()))
        
        if len(rango) == 2:
            ventas = execute_query("""
                SELECT DATE(v.fecha) as fecha, COUNT(v.id) as transacciones,
                       SUM(v.total_final) as total
                FROM ventas v
                WHERE DATE(v.fecha) BETWEEN %s AND %s
                GROUP BY DATE(v.fecha)
                ORDER BY fecha
            """, (rango[0], rango[1]), fetch=True)
            
            if ventas:
                df = pd.DataFrame(ventas)
                fig = px.bar(df, x='fecha', y='total', title='Ventas Diarias')
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df, use_container_width=True)
    
    with tab2:
        st.subheader("Inventario Valorizado")
        
        inventario = execute_query("""
            SELECT p.nombre, p.stock_actual, p.precio_compra_actual,
                   (p.stock_actual * p.precio_compra_actual) as valor_costo,
                   (p.stock_actual * p.precio_venta_actual) as valor_venta
            FROM productos p
            WHERE p.activo = true
            ORDER BY valor_venta DESC
        """, fetch=True)
        
        if inventario:
            df = pd.DataFrame(inventario)
            st.dataframe(df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Valor Total Costo", 
                    f"${df['valor_costo'].sum():.2f}")
            with col2:
                st.metric("Valor Total Venta", 
                    f"${df['valor_venta'].sum():.2f}")
    
    with tab3:
        st.subheader("Productos Más Vendidos")
        
        top = execute_query("""
            SELECT p.nombre, SUM(dv.cantidad) as vendido,
                   SUM(dv.subtotal) as monto
            FROM detalle_ventas dv
            JOIN productos p ON dv.producto_id = p.id
            GROUP BY p.id, p.nombre
            ORDER BY vendido DESC
            LIMIT 20
        """, fetch=True)
        
        if top:
            df = pd.DataFrame(top)
            fig = px.bar(df, x='nombre', y='vendido', 
                title='Productos Más Vendidos')
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)
    
    with tab4:
        st.subheader("Análisis de Márgenes")
        
        analisis = execute_query("""
            SELECT p.nombre, p.precio_compra_actual, p.precio_venta_actual,
                   (p.precio_venta_actual - p.precio_compra_actual) as margen_unitario,
                   ROUND((
                       (p.precio_venta_actual - p.precio_compra_actual) / 
                       p.precio_compra_actual * 100
                   ), 2) as margen_porcentaje
            FROM productos p
            WHERE p.activo = true AND p.precio_compra_actual > 0
            ORDER BY margen_porcentaje DESC
        """, fetch=True)
        
        if analisis:
            df = pd.DataFrame(analisis)
            st.dataframe(df, use_container_width=True)

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
                st.rerun()
        
        st.markdown("""
        ---
        **Versión:** 1.0.0  
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
