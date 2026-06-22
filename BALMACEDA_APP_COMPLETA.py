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
    """Obtener conexión a PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
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
    """Pantalla de login"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        st.title("🏪 Balmaceda Market")
        st.subheader("Sistema POS")
        st.markdown("---")
        
        username = st.text_input("Usuario", key="username")
        password = st.text_input("Contraseña", type="password", key="password")
        
        if st.button("Acceder"):
            # Validar en BD
            result = execute_query(
                "SELECT id, username, nombre_completo, rol FROM usuarios WHERE username = %s AND contraseña = %s AND activo = true",
                (username, password),
                fetch=True
            )
            
            if result:
                st.session_state.authenticated = True
                st.session_state.user = result[0]['username']
                st.session_state.user_role = result[0]['rol']
                st.success("✅ Bienvenido!")
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
    """Gestión de productos"""
    st.title("📦 Productos")
    
    tab1, tab2, tab3 = st.tabs(["Listar", "Crear", "Buscar"])
    
    with tab1:
        st.subheader("Inventario de Productos")
        
        productos = execute_query("""
            SELECT p.id, p.codigo_barras, p.nombre, c.nombre as categoria,
                   p.stock_actual, p.stock_minimo, p.precio_venta_actual, p.activo
            FROM productos p
            JOIN categorias c ON p.categoria_id = c.id
            WHERE p.activo = true
            ORDER BY p.nombre
        """, fetch=True)
        
        if productos:
            df = pd.DataFrame(productos)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay productos registrados")
    
    with tab2:
        st.subheader("Crear Nuevo Producto")
        
        # Inicializar una variable limpia en la memoria de la sesión para el código
        if "codigo_escaneado_camara" not in st.session_state:
            st.session_state["codigo_escaneado_camara"] = ""

        st.markdown("### 📷 Escanear Código con la Cámara")
        
        # HTML/JavaScript corregido para usar la API de mensajes de Streamlit correctamente
        componente_camara = """
        <div style="width: 100%; max-width: 400px; margin: 0 auto;">
            <div id="lector-camara" style="width: 100%; background: #1e1e1e; border-radius: 8px;"></div>
        </div>
        <script src="https://unpkg.com/html5-qrcode"></script>
        <script>
            function onScanSuccess(decodedText, decodedResult) {
                // Truco técnico: Enviar el código simulando un evento que Streamlit sí entiende en el árbol de HTML
                const inputElement = window.parent.document.querySelector('input[aria-label="Código de Barras"]');
                if (inputElement) {
                    inputElement.value = decodedText;
                    inputElement.dispatchEvent(new Event('input', { bubbles: true }));
                    inputElement.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    // Alternativa si no encuentra el foco directo
                    window.parent.postMessage({type: 'streamlit:setComponentValue', value: decodedText}, '*');
                }
                html5QrcodeScanner.clear();
            }
            
            let config = { fps: 15, qrbox: {width: 280, height: 160} };
            let html5QrcodeScanner = new Html5QrcodeScanner("lector-camara", config, false);
            html5QrcodeScanner.render(onScanSuccess);
        </script>
        """
        
        import streamlit.components.v1 as components
        # Renderizamos la cámara fijando el valor capturado de forma independiente
        components.html(componente_camara, height=330)
        
        st.markdown("---")
        st.markdown("### 📝 Datos de la Ficha del Producto")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Ahora el campo está limpio. Si la cámara escribe, aparecerá aquí; si no, digitas tú sin DeltaGenerators.
            codigo = st.text_input("Código de Barras", placeholder="Escanea o escribe manualmente...")
            nombre = st.text_input("Nombre del Producto (ej: Detergente Líquido 3L)")
            
        with col2:
            categoria_opt = execute_query("SELECT id, nombre FROM categorias", fetch=True)
            categoria = st.selectbox("Categoría", [c['nombre'] for c in categoria_opt] if categoria_opt else [])
            
            marca_opt = execute_query("SELECT id, nombre FROM marcas", fetch=True)
            marca = st.selectbox("Marca", [m['nombre'] for m in marca_opt] if marca_opt else [])
        
        col3, col4 = st.columns(2)
        with col3:
            precio_venta = st.number_input("Precio de Venta al Público ($)", min_value=0.0, step=50.0)
        with col4:
            stock_min = st.number_input("Stock Mínimo de Alerta", min_value=0, value=5)
        
        if st.button("💾 Guardar Producto en Balmaceda Market", type="primary"):
            if not codigo or not nombre:
                st.error("❌ El Código de Barras y el Nombre del Producto son campos obligatorios.")
            else:
                try:
                    cat_id = execute_query("SELECT id FROM categorias WHERE nombre = %s", (categoria,), fetch=True)[0]['id']
                    marca_id = execute_query("SELECT id FROM marcas WHERE nombre = %s", (marca,), fetch=True)[0]['id']
                    
                    execute_query("""
                        INSERT INTO productos 
                        (codigo_barras, nombre, categoria_id, marca_id, 
                         precio_compra_actual, precio_venta_actual, stock_actual, stock_minimo, activo)
                        VALUES (%s, %s, %s, %s, 0.0, %s, 0, %s, true)
                    """, (codigo, nombre, cat_id, marca_id, precio_venta, stock_min))
                    
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
                       p.stock_actual, p.precio_venta_actual
                FROM productos p
                JOIN categorias c ON p.categoria_id = c.id
                WHERE (p.nombre ILIKE %s OR p.codigo_barras LIKE %s) AND p.activo = true
            """, (f"%{busqueda}%", f"%{busqueda}%"), fetch=True)
            
            if resultados:
                df = pd.DataFrame(resultados)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No se encontraron productos")
def modulo_ventas():
    """Módulo de ventas con carga de Excel"""
    st.title("🛍️ Ventas")
    
    tab1, tab2 = st.tabs(["Cargar Ventas (Excel)", "Historial"])
    
    with tab1:
        st.subheader("Cargar Ventas del Día")
        st.info("""
        📝 Instrucciones:
        1. Escanea productos durante el día en Excel
        2. Columnas: Código | Nombre | Cantidad | Precio Unitario | Subtotal
        3. Sube el archivo aquí
        4. El sistema actualiza stock automáticamente
        """)
        
        archivo = st.file_uploader("Selecciona Excel de ventas", type=['xlsx', 'xls', 'csv'])
        
        if archivo:
            # Leer Excel
            if archivo.name.endswith('.csv'):
                df_ventas = pd.read_csv(archivo)
            else:
                df_ventas = pd.read_excel(archivo)
            
            st.dataframe(df_ventas)
            
            if st.button("Procesar Ventas"):
                try:
                    # Obtener ID de usuario
                    usuario = execute_query(
                        "SELECT id FROM usuarios WHERE username = %s",
                        (st.session_state.user,),
                        fetch=True
                    )[0]['id']
                    
                    # Crear venta principal
                    total_venta = df_ventas['Subtotal'].sum()
                    numero_venta = f"V-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    venta_result = execute_query("""
                        INSERT INTO ventas 
                        (numero_venta, usuario_id, total_venta, total_final, 
                         metodo_pago, monto_recibido, vuelto)
                        VALUES (%s, %s, %s, %s, 'efectivo', %s, %s)
                        RETURNING id
                    """, (numero_venta, usuario, total_venta, total_venta, 
                          total_venta, 0), fetch=True)
                    
                    venta_id = venta_result[0]['id']
                    
                    # Procesar cada línea
                    for _, row in df_ventas.iterrows():
                        # Obtener producto
                        producto = execute_query(
                            "SELECT id, stock_actual FROM productos WHERE codigo_barras = %s",
                            (row['Código'],),
                            fetch=True
                        )
                        
                        if producto:
                            prod_id = producto[0]['id']
                            cantidad = int(row['Cantidad'])
                            precio = float(row['Precio Unitario'])
                            
                            # Insertar detalle venta
                            execute_query("""
                                INSERT INTO detalle_ventas 
                                (venta_id, producto_id, cantidad, 
                                 precio_venta_unitario, subtotal)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (venta_id, prod_id, cantidad, precio, 
                                  cantidad * precio))
                            
                            # Actualizar stock
                            execute_query("""
                                UPDATE productos
                                SET stock_actual = stock_actual - %s,
                                    fecha_modificacion = CURRENT_TIMESTAMP
                                WHERE id = %s
                            """, (cantidad, prod_id))
                            
                            # Registrar movimiento
                            execute_query("""
                                INSERT INTO movimientos_inventario
                                (producto_id, tipo_movimiento, cantidad, usuario_id,
                                 referencia_documento, referencia_id)
                                VALUES (%s, 'venta', %s, %s, 'venta', %s)
                            """, (prod_id, cantidad, usuario, venta_id))
                    
                    st.success(f"✅ Ventas cargadas - Nº {numero_venta}")
                    st.balloons()
                
                except Exception as e:
                    st.error(f"❌ Error procesando ventas: {e}")
    
    with tab2:
        st.subheader("Historial de Ventas")
        
        ventas = execute_query("""
            SELECT v.numero_venta, v.fecha, v.total_final, u.nombre_completo
            FROM ventas v
            JOIN usuarios u ON v.usuario_id = u.id
            ORDER BY v.fecha DESC
            LIMIT 100
        """, fetch=True)
        
        if ventas:
            df = pd.DataFrame(ventas)
            st.dataframe(df, use_container_width=True)

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
