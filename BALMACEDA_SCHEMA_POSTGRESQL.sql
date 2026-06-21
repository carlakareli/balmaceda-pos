-- ============================================================================
-- BALMACEDA MARKET - SISTEMA POS
-- Schema PostgreSQL COMPLETO (100% GRATIS)
-- Ejecutar en: Neon, Railway, Vercel Postgres, o tu PostgreSQL online
-- ============================================================================

-- Tablas de referencia
-- ============================================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL,
    contraseña VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(150) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('administrador', 'vendedor')),
    activo BOOLEAN DEFAULT true,
    ultimo_acceso TIMESTAMP,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    descripcion TEXT,
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS unidades_medida (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    abreviatura VARCHAR(10) UNIQUE NOT NULL,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS marcas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS proveedores (
    id SERIAL PRIMARY KEY,
    nombre_proveedor VARCHAR(150) NOT NULL,
    rut VARCHAR(20) UNIQUE,
    telefono VARCHAR(20),
    correo VARCHAR(100),
    direccion TEXT,
    contacto_principal VARCHAR(100),
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gestión de Productos e Inventario
-- ============================================================================

CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    codigo_barras VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT,
    marca_id INTEGER REFERENCES marcas(id),
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    unidad_medida_id INTEGER NOT NULL REFERENCES unidades_medida(id),
    precio_compra_actual DECIMAL(10, 2) NOT NULL DEFAULT 0,
    precio_venta_actual DECIMAL(10, 2) NOT NULL DEFAULT 0,
    stock_actual INTEGER NOT NULL DEFAULT 0,
    stock_minimo INTEGER NOT NULL DEFAULT 5,
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT stock_no_negativo CHECK (stock_actual >= 0),
    CONSTRAINT precio_compra_positivo CHECK (precio_compra_actual >= 0),
    CONSTRAINT precio_venta_positivo CHECK (precio_venta_actual >= 0)
);

CREATE INDEX idx_productos_codigo_barras ON productos(codigo_barras);
CREATE INDEX idx_productos_nombre ON productos(nombre);
CREATE INDEX idx_productos_categoria ON productos(categoria_id);

-- Históricos de Precios
-- ============================================================================

CREATE TABLE IF NOT EXISTS historial_precios_compra (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
    precio_compra DECIMAL(10, 2) NOT NULL,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    observacion TEXT,
    CONSTRAINT precio_positivo CHECK (precio_compra >= 0)
);

CREATE INDEX idx_historial_precios_compra_producto ON historial_precios_compra(producto_id);
CREATE INDEX idx_historial_precios_compra_fecha ON historial_precios_compra(fecha);

CREATE TABLE IF NOT EXISTS historial_precios_venta (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    precio_venta DECIMAL(10, 2) NOT NULL,
    motivo_cambio VARCHAR(200),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    CONSTRAINT precio_positivo CHECK (precio_venta >= 0)
);

CREATE INDEX idx_historial_precios_venta_producto ON historial_precios_venta(producto_id);

-- Módulo de Compras
-- ============================================================================

CREATE TABLE IF NOT EXISTS compras (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
    numero_factura VARCHAR(50) UNIQUE NOT NULL,
    total_compra DECIMAL(12, 2) NOT NULL DEFAULT 0,
    observaciones TEXT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    estado VARCHAR(20) DEFAULT 'finalizada' CHECK (estado IN ('borrador', 'finalizada')),
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT total_positivo CHECK (total_compra >= 0)
);

CREATE INDEX idx_compras_proveedor ON compras(proveedor_id);
CREATE INDEX idx_compras_fecha ON compras(fecha);

CREATE TABLE IF NOT EXISTS detalle_compras (
    id SERIAL PRIMARY KEY,
    compra_id INTEGER NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad INTEGER NOT NULL,
    precio_compra_unitario DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL,
    CONSTRAINT cantidad_positiva CHECK (cantidad > 0),
    CONSTRAINT precio_positivo CHECK (precio_compra_unitario >= 0),
    CONSTRAINT subtotal_positivo CHECK (subtotal >= 0)
);

CREATE INDEX idx_detalle_compras_compra ON detalle_compras(compra_id);

-- Módulo de Ventas
-- ============================================================================

CREATE TABLE IF NOT EXISTS ventas (
    id SERIAL PRIMARY KEY,
    numero_venta VARCHAR(50) UNIQUE NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    total_venta DECIMAL(12, 2) NOT NULL DEFAULT 0,
    descuento_monto DECIMAL(10, 2) DEFAULT 0,
    descuento_porcentaje DECIMAL(5, 2) DEFAULT 0,
    total_final DECIMAL(12, 2) NOT NULL,
    metodo_pago VARCHAR(20) NOT NULL CHECK (metodo_pago IN ('efectivo', 'debito', 'credito', 'transferencia')),
    monto_recibido DECIMAL(12, 2) DEFAULT 0,
    vuelto DECIMAL(12, 2) DEFAULT 0,
    observaciones TEXT,
    CONSTRAINT total_positivo CHECK (total_venta >= 0),
    CONSTRAINT total_final_positivo CHECK (total_final >= 0)
);

CREATE INDEX idx_ventas_fecha ON ventas(fecha);
CREATE INDEX idx_ventas_numero_venta ON ventas(numero_venta);

CREATE TABLE IF NOT EXISTS detalle_ventas (
    id SERIAL PRIMARY KEY,
    venta_id INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad INTEGER NOT NULL,
    precio_venta_unitario DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL,
    CONSTRAINT cantidad_positiva CHECK (cantidad > 0),
    CONSTRAINT precio_positivo CHECK (precio_venta_unitario >= 0),
    CONSTRAINT subtotal_positivo CHECK (subtotal >= 0)
);

CREATE INDEX idx_detalle_ventas_venta ON detalle_ventas(venta_id);

-- Auditoría y Trazabilidad
-- ============================================================================

CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo_movimiento VARCHAR(20) NOT NULL CHECK (tipo_movimiento IN ('compra', 'venta', 'ajuste', 'merma', 'devoluccion', 'correccion')),
    cantidad INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    observacion TEXT,
    referencia_documento VARCHAR(50),
    referencia_id INTEGER
);

CREATE INDEX idx_movimientos_inventario_producto ON movimientos_inventario(producto_id);
CREATE INDEX idx_movimientos_inventario_fecha ON movimientos_inventario(fecha);

CREATE TABLE IF NOT EXISTS mermas (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    cantidad INTEGER NOT NULL,
    motivo VARCHAR(50) NOT NULL CHECK (motivo IN ('vencido', 'danado', 'roto', 'perdido')),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observacion TEXT,
    CONSTRAINT cantidad_positiva CHECK (cantidad > 0)
);

CREATE INDEX idx_mermas_producto ON mermas(producto_id);
CREATE INDEX idx_mermas_fecha ON mermas(fecha);

-- ============================================================================
-- DATOS INICIALES
-- ============================================================================

INSERT INTO unidades_medida (nombre, abreviatura, descripcion) VALUES
('Unidad', 'Und', 'Producto individual'),
('Kilogramo', 'kg', 'Peso en kilogramos'),
('Litro', 'L', 'Volumen en litros'),
('Gramo', 'g', 'Peso en gramos'),
('Mililitro', 'ml', 'Volumen en mililitros'),
('Caja', 'caja', 'Caja con múltiples unidades'),
('Paquete', 'paq', 'Paquete con múltiples unidades')
ON CONFLICT DO NOTHING;

INSERT INTO categorias (nombre, descripcion) VALUES
('Detergentes', 'Detergentes para lavado de ropa'),
('Suavizantes', 'Suavizantes y perfumadores'),
('Cloro y Desinfectantes', 'Productos de desinfección'),
('Limpiadores', 'Limpiadores multiusos'),
('Higiene Personal', 'Shampoo, jabón, desodorantes'),
('Pañales y Toallitas', 'Pañales y artículos de higiene infantil'),
('Pasta Dental', 'Cremas dentales y enjuagues'),
('Acondicionadores', 'Acondicionadores y tratamientos capilares'),
('Otros', 'Otros productos de consumo masivo')
ON CONFLICT DO NOTHING;

INSERT INTO marcas (nombre) VALUES
('Ace'),
('Ariel'),
('Persil'),
('OMO'),
('Comfort'),
('Downy'),
('Dettol'),
('Lisoform'),
('Clorox'),
('Mr. Limpio'),
('Ponds'),
('Dove'),
('Colgate'),
('Oral-B')
ON CONFLICT DO NOTHING;

INSERT INTO usuarios (username, correo, contraseña, nombre_completo, rol) VALUES
('admin', 'admin@balmaceda.local', '123456', 'Administrador', 'administrador'),
('vendedor', 'vendedor@balmaceda.local', '123456', 'Vendedor', 'vendedor')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- VISTAS ÚTILES PARA REPORTES
-- ============================================================================

CREATE VIEW IF NOT EXISTS v_productos_bajo_stock AS
SELECT 
    p.id,
    p.codigo_barras,
    p.nombre,
    c.nombre as categoria,
    p.stock_actual,
    p.stock_minimo,
    (p.stock_minimo - p.stock_actual) as falta_para_minimo
FROM productos p
JOIN categorias c ON p.categoria_id = c.id
WHERE p.stock_actual <= p.stock_minimo
AND p.activo = true
ORDER BY p.stock_actual ASC;

CREATE VIEW IF NOT EXISTS v_inventario_valorizado AS
SELECT 
    c.nombre as categoria,
    p.id,
    p.codigo_barras,
    p.nombre,
    p.stock_actual,
    p.precio_compra_actual,
    p.precio_venta_actual,
    (p.stock_actual * p.precio_compra_actual) as valor_costo,
    (p.stock_actual * p.precio_venta_actual) as valor_venta,
    ((p.stock_actual * p.precio_venta_actual) - (p.stock_actual * p.precio_compra_actual)) as utilidad_potencial
FROM productos p
JOIN categorias c ON p.categoria_id = c.id
WHERE p.activo = true
ORDER BY c.nombre, p.nombre;

CREATE VIEW IF NOT EXISTS v_ventas_resumen_diario AS
SELECT 
    DATE(v.fecha) as fecha,
    COUNT(v.id) as cantidad_transacciones,
    COUNT(DISTINCT v.usuario_id) as usuarios_activos,
    SUM(v.total_final) as total_ventas,
    AVG(v.total_final) as ticket_promedio,
    SUM(CASE WHEN v.metodo_pago = 'efectivo' THEN v.total_final ELSE 0 END) as ventas_efectivo,
    SUM(CASE WHEN v.metodo_pago = 'debito' THEN v.total_final ELSE 0 END) as ventas_debito,
    SUM(CASE WHEN v.metodo_pago = 'credito' THEN v.total_final ELSE 0 END) as ventas_credito
FROM ventas v
GROUP BY DATE(v.fecha)
ORDER BY fecha DESC;

-- ============================================================================
-- FIN DEL SCHEMA
-- ============================================================================

-- Para usar:
-- 1. Copiar todo el script
-- 2. Ir a tu PostgreSQL online (Neon, Railway, etc.)
-- 3. Ejecutar en el SQL Editor
-- 4. Listo! Base de datos lista para usar
