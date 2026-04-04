"""
main.py
-------
API REST principal de OCA - Software & Servicios Digitales
Framework: FastAPI | Base de datos: Supabase (PostgreSQL)
Versión: 2.0

════════════════════════════════════════════════════════════════════════
ESTRUCTURA DE MÓDULOS (para futura modularización):
════════════════════════════════════════════════════════════════════════

Si en el futuro divides este archivo en carpetas, la estructura sería:

📁 app/
├── main.py                        ← Solo el app = FastAPI() y los include_router
├── core/
│   ├── database.py                ← Conexión Supabase (ya separado)
│   └── security.py                ← Funciones de autenticación JWT
├── routers/
│   ├── dashboard/                 ← 📊 Todo el panel admin
│   │   ├── usuarios.py
│   │   ├── categorias.py
│   │   ├── software.py
│   │   ├── planes.py
│   │   ├── pagos.py
│   │   ├── licencias.py
│   │   ├── tickets.py
│   │   ├── cupones.py
│   │   ├── leads.py
│   │   ├── resenas.py
│   │   └── analytics.py
│   ├── web/                       ← 🌐 Todo lo de la página pública
│   │   ├── productos.py
│   │   ├── planes.py
│   │   ├── auth.py
│   │   ├── carrito.py
│   │   ├── pagos.py
│   │   ├── resenas.py
│   │   ├── tickets.py
│   │   └── contacto.py
│   └── usuario/                   ← 👤 Panel del usuario logueado
│       ├── perfil.py
│       ├── licencias.py
│       ├── historial.py
│       ├── favoritos.py
│       └── notificaciones.py
└── models/                        ← Pydantic schemas (request/response)
    ├── usuarios.py
    ├── productos.py
    ├── pagos.py
    └── ...

════════════════════════════════════════════════════════════════════════
SEPARACIÓN DE SECCIONES EN ESTE ARCHIVO:
════════════════════════════════════════════════════════════════════════
  [COMPARTIDO]   → Usado tanto por dashboard como por página web
  [DASHBOARD]    → Solo panel administrativo (/admin/...)
  [WEB]          → Solo página pública del cliente (/...)
  [USUARIO]      → Panel del usuario logueado (/mis-... y /usuario/...)
════════════════════════════════════════════════════════════════════════
"""

from fastapi import FastAPI, Depends, HTTPException, Query, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import date
import uuid

from database import get_supabase, supabase as db
from supabase import Client

# ══════════════════════════════════════════════
# INICIALIZACIÓN DE LA APP
# ══════════════════════════════════════════════

app = FastAPI(
    title="OCA - Software & Servicios Digitales",
    description="""
## API REST completa para OCA

### Secciones:
- 📊 **Dashboard Admin** (`/admin/...`) — Panel de gestión interna
- 🌐 **Página Web Pública** (`/productos`, `/planes`, `/auth/...`) — Portal del cliente
- 👤 **Panel de Usuario** (`/mis-...`, `/usuario/...`) — Área personal del cliente logueado

### Métodos de pago soportados:
Yape · Plin · Transferencia Bancaria · Tarjeta · Efectivo
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware CORS — ajusta los orígenes según tu dominio en producción
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 🔧 Cambiar a tu dominio en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────────
#  MODELOS PYDANTIC (Schemas de Request/Response)
# ─────────────────────────────────────────────────────────────────────
# Si modularizas → mover cada grupo a 📁 app/models/<nombre>.py
# ══════════════════════════════════════════════════════════════════════

# ── [COMPARTIDO] Usuarios ─────────────────────────────────────────────
class UsuarioCreate(BaseModel):
    nombre_completo: str
    email: EmailStr
    password: str
    rol: str = "cliente"  # admin | cliente | soporte

class UsuarioEstado(BaseModel):
    estado: str  # activo | suspendido | bloqueado

class UsuarioRol(BaseModel):
    rol: str  # admin | cliente | soporte

# ── [COMPARTIDO] Categorías ───────────────────────────────────────────
class CategoriaCreate(BaseModel):
    nombre: str
    slug: str
    icono: Optional[str] = None
    orden: int = 0
    visible: bool = True

class CategoriaEstado(BaseModel):
    visible: bool

# ── [COMPARTIDO] Software ─────────────────────────────────────────────
class SoftwareCreate(BaseModel):
    categoria_id: Optional[int] = None
    nombre_sistema: str
    descripcion_corta: Optional[str] = None
    descripcion: Optional[str] = None
    precio_regular: float
    precio_oferta: Optional[float] = None
    tecnologias_usadas: Optional[str] = None
    url_imagen: Optional[str] = None
    url_demo: Optional[str] = None
    url_video: Optional[str] = None

class SoftwareEstado(BaseModel):
    estado: str  # Activo | Inactivo | Eliminado

class SoftwareOferta(BaseModel):
    precio_oferta: float
    es_oferta: bool = True

# ── [COMPARTIDO] Planes Web ───────────────────────────────────────────
class PlanCreate(BaseModel):
    nombre_plan: str
    subtitulo: Optional[str] = None
    precio: float
    precio_tachado: Optional[float] = None
    etiqueta_especial: Optional[str] = None
    tipo_pago: str = "Pago_Unico"
    color_tema: Optional[str] = None
    orden: int = 0

class PlanEstado(BaseModel):
    estado: str  # Activo | Inactivo

# ── [COMPARTIDO] Detalles de Items ────────────────────────────────────
class DetalleCreate(BaseModel):
    item_id: int
    tipo_item: str  # plan | software | servicio
    caracteristica: str
    incluido: bool = True
    orden: int = 0

class DetalleEstado(BaseModel):
    incluido: bool

# ── [DASHBOARD] Pagos ────────────────────────────────────────────────
class PagoRechazo(BaseModel):
    motivo: str

class PagoReembolso(BaseModel):
    motivo: Optional[str] = None

# ── [DASHBOARD] Licencias ────────────────────────────────────────────
class LicenciaRenovar(BaseModel):
    nueva_fecha_expiracion: date

# ── [DASHBOARD] Tickets ───────────────────────────────────────────────
class TicketAsignar(BaseModel):
    asignado_a: str  # UUID del agente de soporte

class TicketEstado(BaseModel):
    estado: str  # En_Progreso | Resuelto | Cerrado

class TicketMensaje(BaseModel):
    contenido: str
    es_interno: bool = False  # True = nota interna, no visible al cliente

# ── [COMPARTIDO] Cupones ──────────────────────────────────────────────
class CuponCreate(BaseModel):
    codigo: str
    descuento_porcentaje: Optional[float] = None
    descuento_monto: Optional[float] = None
    fecha_expiracion: Optional[date] = None
    usos_maximos: Optional[int] = None

class CuponEstado(BaseModel):
    activo: bool

# ── [DASHBOARD] Leads ─────────────────────────────────────────────────
class LeadEstado(BaseModel):
    estado: str  # Nuevo | Contactado | Calificado | Convertido | Descartado
    atendido_por: Optional[str] = None  # UUID del vendedor

# ── [WEB] Auth ────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    nombre_completo: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PerfilUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    telefono: Optional[str] = None
    empresa: Optional[str] = None
    ciudad: Optional[str] = None
    direccion: Optional[str] = None
    ruc: Optional[str] = None
    avatar_url: Optional[str] = None

# ── [WEB] Carrito / Checkout ──────────────────────────────────────────
class CarritoAgregar(BaseModel):
    producto_id: int
    tipo: str  # software | plan

class CarritoEliminar(BaseModel):
    producto_id: int
    tipo: str

class CheckoutRequest(BaseModel):
    producto_id: int
    tipo: str  # software | plan
    cupon_codigo: Optional[str] = None

# ── [WEB] Pagos del cliente ───────────────────────────────────────────
class SubirComprobante(BaseModel):
    numero_operacion: str
    comprobante_url: str        # URL ya subida a Supabase Storage
    metodo_pago: str            # Yape | Plin | Transferencia_Bancaria
    numero_telefono_pagador: Optional[str] = None
    nombre_titular_cuenta: Optional[str] = None
    servicio_id: int

# ── [WEB] Reseñas ─────────────────────────────────────────────────────
class ResenaCreate(BaseModel):
    software_id: Optional[int] = None
    plan_id: Optional[int] = None
    nombre_autor: str
    calificacion: int           # 1 a 5
    comentario: str

# ── [WEB] Tickets del cliente ─────────────────────────────────────────
class TicketCreate(BaseModel):
    asunto: str
    descripcion: str
    prioridad: str = "Media"    # Baja | Media | Alta | Critica

class MensajeCreate(BaseModel):
    contenido: str

# ── [WEB] Contacto / Lead ────────────────────────────────────────────
class ContactoCreate(BaseModel):
    nombre: str
    email: EmailStr
    telefono: Optional[str] = None
    empresa: Optional[str] = None
    servicio_interes: Optional[str] = None
    mensaje: Optional[str] = None

# ── [WEB] Extras ─────────────────────────────────────────────────────
class ValidarCupon(BaseModel):
    codigo: str
    monto_original: float

class FavoritoToggle(BaseModel):
    producto_id: int
    tipo: str  # software | plan


# ══════════════════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────────
#                        HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────
# Si modularizas → mover a 📁 app/core/helpers.py
# ══════════════════════════════════════════════════════════════════════

def handle_db_error(response, detail: str = "Error en base de datos"):
    """Lanza HTTPException si Supabase retorna error."""
    if hasattr(response, "error") and response.error:
        raise HTTPException(status_code=400, detail=str(response.error))
    return response

def not_found(data, msg: str = "Recurso no encontrado"):
    """Lanza 404 si el resultado está vacío."""
    if not data:
        raise HTTPException(status_code=404, detail=msg)
    return data

def log_actividad(usuario_id: Optional[str], accion: str, tabla: str, registro_id: str, metadata: dict = {}):
    """
    Registra una acción en historial_actividad.
    Llamar después de cualquier operación crítica (pagos, licencias, etc.)
    """
    try:
        db.table("historial_actividad").insert({
            "usuario_id": usuario_id,
            "accion": accion,
            "tabla_afectada": tabla,
            "registro_id": str(registro_id),
            "metadata": metadata
        }).execute()
    except Exception:
        pass  # El log nunca debe interrumpir el flujo principal


# ══════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════
#
#   ██████╗  █████╗ ███████╗██╗  ██╗██████╗  ██████╗  █████╗ ██████╗
#   ██╔══██╗██╔══██╗██╔════╝██║  ██║██╔══██╗██╔═══██╗██╔══██╗██╔══██╗
#   ██║  ██║███████║███████╗███████║██████╔╝██║   ██║███████║██║  ██║
#   ██║  ██║██╔══██║╚════██║██╔══██║██╔══██╗██║   ██║██╔══██║██║  ██║
#   ██████╔╝██║  ██║███████║██║  ██║██████╔╝╚██████╔╝██║  ██║██████╔╝
#   ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═════╝
#
#   PANEL ADMINISTRATIVO — /admin/...
#   Si modularizas → 📁 app/routers/dashboard/
#
# ══════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: USUARIOS
# Si modularizas → 📁 app/routers/dashboard/usuarios.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/usuarios", tags=["📊 Dashboard — Usuarios"])
def admin_listar_usuarios(
    rol: Optional[str] = None,
    activo: Optional[bool] = None,
    email: Optional[str] = None,
    fecha_registro: Optional[date] = None,
    db: Client = Depends(get_supabase)
):
    """
    Lista todos los usuarios con su perfil de cliente asociado.
    Permite filtrar por rol, estado, email o fecha de registro.
    Incluye: datos personales, rol, estado, último acceso, perfil cliente.
    """
    query = db.table("usuarios").select("*, clientes(*)")

    if rol:
        query = query.eq("rol", rol)
    if activo is not None:
        query = query.eq("activo", activo)
    if email:
        query = query.ilike("email", f"%{email}%")
    if fecha_registro:
        query = query.gte("fecha_registro", str(fecha_registro))

    res = query.execute()
    return res.data


@app.get("/admin/usuarios/{id}", tags=["📊 Dashboard — Usuarios"])
def admin_detalle_usuario(id: str, db: Client = Depends(get_supabase)):
    """
    Detalle completo de un usuario: datos, cliente, compras, tickets, pagos.
    """
    usuario = db.table("usuarios").select("*, clientes(*)").eq("id", id).single().execute()
    not_found(usuario.data, "Usuario no encontrado")

    compras = db.table("servicios_adquiridos").select("*, software_venta(*), planes_web(*)").eq("usuario_id", id).execute()
    tickets = db.table("tickets_soporte").select("*").eq("usuario_id", id).execute()
    pagos   = db.table("pagos").select("*").eq("usuario_id", id).execute()

    return {
        "usuario": usuario.data,
        "compras": compras.data,
        "tickets": tickets.data,
        "pagos": pagos.data,
    }


@app.post("/admin/usuarios", tags=["📊 Dashboard — Usuarios"], status_code=201)
def admin_crear_usuario(body: UsuarioCreate, db: Client = Depends(get_supabase)):
    """
    Crea un usuario manualmente desde el dashboard.
    Permite crear admin, soporte o cliente interno.
    Usa Supabase Auth y luego sincroniza con la tabla usuarios.
    """
    # Crear en Supabase Auth
    auth_res = db.auth.admin.create_user({
        "email": body.email,
        "password": body.password,
        "email_confirm": True,
    })
    if not auth_res.user:
        raise HTTPException(status_code=400, detail="No se pudo crear el usuario en Auth")

    uid = auth_res.user.id

    # Insertar en tabla usuarios (el trigger debería hacerlo, pero lo forzamos)
    res = db.table("usuarios").upsert({
        "id": uid,
        "nombre_completo": body.nombre_completo,
        "email": body.email,
        "rol": body.rol,
    }).execute()

    log_actividad(uid, f"Usuario creado con rol {body.rol}", "usuarios", uid)
    return {"mensaje": "Usuario creado exitosamente", "id": uid}


@app.post("/admin/usuarios/{id}/estado", tags=["📊 Dashboard — Usuarios"])
def admin_cambiar_estado_usuario(id: str, body: UsuarioEstado, db: Client = Depends(get_supabase)):
    """
    Actualiza el estado del usuario: activo | suspendido | bloqueado.
    Evita el DELETE físico. También actualiza estado_cliente en tabla clientes.
    """
    db.table("usuarios").update({"activo": body.estado == "activo"}).eq("id", id).execute()
    db.table("clientes").update({"estado_cliente": body.estado.capitalize()}).eq("usuario_id", id).execute()
    log_actividad(None, f"Estado de usuario cambiado a {body.estado}", "usuarios", id)
    return {"mensaje": f"Estado actualizado a {body.estado}"}


@app.post("/admin/usuarios/{id}/rol", tags=["📊 Dashboard — Usuarios"])
def admin_cambiar_rol_usuario(id: str, body: UsuarioRol, db: Client = Depends(get_supabase)):
    """
    Cambia el rol del usuario: admin | cliente | soporte.
    Crítico para permisos y RLS.
    """
    db.table("usuarios").update({"rol": body.rol}).eq("id", id).execute()
    log_actividad(None, f"Rol de usuario cambiado a {body.rol}", "usuarios", id)
    return {"mensaje": f"Rol actualizado a {body.rol}"}


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: CATEGORÍAS
# Si modularizas → 📁 app/routers/dashboard/categorias.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/categorias", tags=["📊 Dashboard — Categorías"])
def admin_listar_categorias(db: Client = Depends(get_supabase)):
    """Lista todas las categorías, incluyendo las ocultas."""
    res = db.table("categorias").select("*").order("orden").execute()
    return res.data


@app.post("/admin/categorias", tags=["📊 Dashboard — Categorías"], status_code=201)
def admin_crear_categoria(body: CategoriaCreate, db: Client = Depends(get_supabase)):
    """Crea una nueva categoría para el catálogo."""
    res = db.table("categorias").insert(body.dict()).execute()
    handle_db_error(res)
    return res.data[0]


@app.post("/admin/categorias/{id}", tags=["📊 Dashboard — Categorías"])
def admin_editar_categoria(id: int, body: CategoriaCreate, db: Client = Depends(get_supabase)):
    """Edita una categoría existente."""
    res = db.table("categorias").update(body.dict(exclude_none=True)).eq("id", id).execute()
    handle_db_error(res)
    return res.data[0] if res.data else {"mensaje": "Actualizado"}


@app.post("/admin/categorias/{id}/estado", tags=["📊 Dashboard — Categorías"])
def admin_estado_categoria(id: int, body: CategoriaEstado, db: Client = Depends(get_supabase)):
    """Activa u oculta una categoría del menú principal."""
    db.table("categorias").update({"visible": body.visible}).eq("id", id).execute()
    return {"mensaje": "Visibilidad actualizada"}


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: SOFTWARE
# Si modularizas → 📁 app/routers/dashboard/software.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/software", tags=["📊 Dashboard — Software"])
def admin_listar_software(
    categoria: Optional[int] = None,
    estado: Optional[str] = None,
    oferta: Optional[bool] = None,
    db: Client = Depends(get_supabase)
):
    """Lista todo el software con filtros de categoría, estado y oferta."""
    query = db.table("software_venta").select("*, categorias(nombre)")
    if categoria:
        query = query.eq("categoria_id", categoria)
    if estado:
        query = query.eq("estado", estado)
    if oferta is not None:
        query = query.eq("es_oferta", oferta)
    return query.execute().data


@app.get("/admin/software/{id}", tags=["📊 Dashboard — Software"])
def admin_detalle_software(id: int, db: Client = Depends(get_supabase)):
    """
    Detalle completo del software incluyendo:
    características, reseñas, descargas, licencias asociadas.
    """
    sw = db.table("software_venta").select("*, categorias(*)").eq("id", id).single().execute()
    not_found(sw.data)
    detalles   = db.table("detalles_items").select("*").eq("item_id", id).eq("tipo_item", "software").execute()
    resenas    = db.table("opiniones_resenas").select("*").eq("software_id", id).eq("estado_moderacion", "Aprobado").execute()
    licencias  = db.table("licencias").select("*").eq("software_id", id).execute()
    return {
        "software": sw.data,
        "detalles": detalles.data,
        "resenas": resenas.data,
        "licencias": licencias.data,
    }


@app.post("/admin/software", tags=["📊 Dashboard — Software"], status_code=201)
def admin_crear_software(body: SoftwareCreate, db: Client = Depends(get_supabase)):
    """Crea un nuevo software en el catálogo."""
    res = db.table("software_venta").insert(body.dict(exclude_none=True)).execute()
    handle_db_error(res)
    return res.data[0]


@app.post("/admin/software/{id}", tags=["📊 Dashboard — Software"])
def admin_editar_software(id: int, body: SoftwareCreate, db: Client = Depends(get_supabase)):
    """Edita los datos de un software existente."""
    res = db.table("software_venta").update(body.dict(exclude_none=True)).eq("id", id).execute()
    handle_db_error(res)
    return res.data[0] if res.data else {"mensaje": "Actualizado"}


@app.post("/admin/software/{id}/estado", tags=["📊 Dashboard — Software"])
def admin_estado_software(id: int, body: SoftwareEstado, db: Client = Depends(get_supabase)):
    """Cambia el estado: Activo | Inactivo | Eliminado (lógico, no físico)."""
    db.table("software_venta").update({"estado": body.estado}).eq("id", id).execute()
    log_actividad(None, f"Estado de software cambiado a {body.estado}", "software_venta", str(id))
    return {"mensaje": f"Estado actualizado a {body.estado}"}


@app.post("/admin/software/{id}/oferta", tags=["📊 Dashboard — Software"])
def admin_activar_oferta_software(id: int, body: SoftwareOferta, db: Client = Depends(get_supabase)):
    """Activa o desactiva la oferta del software con precio especial."""
    db.table("software_venta").update({
        "precio_oferta": body.precio_oferta,
        "es_oferta": body.es_oferta
    }).eq("id", id).execute()
    return {"mensaje": "Oferta actualizada"}


@app.post("/admin/software/{id}/incrementar-descarga", tags=["📊 Dashboard — Software"])
def admin_incrementar_descarga(id: int, db: Client = Depends(get_supabase)):
    """
    Incrementa el contador de descargas del software.
    Puede conectarse con el trigger fn_incrementar_descarga de la BD.
    """
    sw = db.table("software_venta").select("contador_descargas").eq("id", id).single().execute()
    not_found(sw.data)
    nuevo_contador = (sw.data.get("contador_descargas") or 0) + 1
    db.table("software_venta").update({"contador_descargas": nuevo_contador}).eq("id", id).execute()
    return {"contador_descargas": nuevo_contador}


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: PLANES WEB
# Si modularizas → 📁 app/routers/dashboard/planes.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/planes", tags=["📊 Dashboard — Planes Web"])
def admin_listar_planes(db: Client = Depends(get_supabase)):
    """Lista todos los planes web (incluyendo inactivos)."""
    return db.table("planes_web").select("*").order("orden").execute().data


@app.post("/admin/planes", tags=["📊 Dashboard — Planes Web"], status_code=201)
def admin_crear_plan(body: PlanCreate, db: Client = Depends(get_supabase)):
    """Crea un nuevo plan web."""
    res = db.table("planes_web").insert(body.dict(exclude_none=True)).execute()
    handle_db_error(res)
    return res.data[0]


@app.post("/admin/planes/{id}", tags=["📊 Dashboard — Planes Web"])
def admin_editar_plan(id: int, body: PlanCreate, db: Client = Depends(get_supabase)):
    """Edita un plan web existente."""
    res = db.table("planes_web").update(body.dict(exclude_none=True)).eq("id", id).execute()
    handle_db_error(res)
    return res.data[0] if res.data else {"mensaje": "Actualizado"}


@app.post("/admin/planes/{id}/estado", tags=["📊 Dashboard — Planes Web"])
def admin_estado_plan(id: int, body: PlanEstado, db: Client = Depends(get_supabase)):
    """Activa o desactiva un plan web."""
    db.table("planes_web").update({"estado": body.estado}).eq("id", id).execute()
    return {"mensaje": f"Plan actualizado a {body.estado}"}


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: DETALLES DE ITEMS (Características)
# Si modularizas → 📁 app/routers/dashboard/detalles.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/items/{tipo}/{id}/detalles", tags=["📊 Dashboard — Detalles Items"])
def admin_obtener_detalles(tipo: str, id: int, db: Client = Depends(get_supabase)):
    """
    Obtiene las características de un software o plan.
    tipo: software | plan | servicio
    """
    res = db.table("detalles_items").select("*").eq("item_id", id).eq("tipo_item", tipo).order("orden").execute()
    return res.data


@app.post("/admin/items/detalle", tags=["📊 Dashboard — Detalles Items"], status_code=201)
def admin_agregar_detalle(body: DetalleCreate, db: Client = Depends(get_supabase)):
    """Agrega una nueva característica a un software, plan o servicio."""
    res = db.table("detalles_items").insert(body.dict()).execute()
    handle_db_error(res)
    return res.data[0]


@app.post("/admin/items/detalle/{id}", tags=["📊 Dashboard — Detalles Items"])
def admin_editar_detalle(id: int, body: DetalleCreate, db: Client = Depends(get_supabase)):
    """Edita una característica existente."""
    res = db.table("detalles_items").update(body.dict(exclude_none=True)).eq("id", id).execute()
    handle_db_error(res)
    return res.data[0] if res.data else {"mensaje": "Actualizado"}


@app.post("/admin/items/detalle/{id}/estado", tags=["📊 Dashboard — Detalles Items"])
def admin_estado_detalle(id: int, body: DetalleEstado, db: Client = Depends(get_supabase)):
    """Activa o desactiva visualmente una característica (campo 'incluido')."""
    db.table("detalles_items").update({"incluido": body.incluido}).eq("id", id).execute()
    return {"mensaje": "Visibilidad del detalle actualizada"}


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: PAGOS ⚠️ CRÍTICO
# Si modularizas → 📁 app/routers/dashboard/pagos.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/pagos", tags=["📊 Dashboard — Pagos ⚠️"])
def admin_listar_pagos(
    estado_pago: Optional[str] = None,
    metodo_pago: Optional[str] = None,
    fecha: Optional[date] = None,
    db: Client = Depends(get_supabase)
):
    """
    Lista todos los pagos. Filtros: estado, método de pago, fecha.
    Los pagos son sensibles → sin DELETE normal.
    """
    query = db.table("pagos").select("*, usuarios(nombre_completo, email)").order("id", desc=True)
    if estado_pago:
        query = query.eq("estado_pago", estado_pago)
    if metodo_pago:
        query = query.eq("metodo_pago", metodo_pago)
    if fecha:
        query = query.gte("comprobante_subido_en", str(fecha))
    return query.execute().data


@app.get("/admin/pagos/{id}", tags=["📊 Dashboard — Pagos ⚠️"])
def admin_detalle_pago(id: int, db: Client = Depends(get_supabase)):
    """
    Detalle completo del pago: comprobante, cliente, producto comprado.
    """
    pago = db.table("pagos").select(
        "*, usuarios(nombre_completo, email), servicios_adquiridos(*, software_venta(*), planes_web(*))"
    ).eq("id", id).single().execute()
    not_found(pago.data, "Pago no encontrado")
    return pago.data


@app.post("/admin/pagos/{id}/revisar", tags=["📊 Dashboard — Pagos ⚠️"])
def admin_pago_revisar(id: int, db: Client = Depends(get_supabase)):
    """Marca el pago como En_Revision. Admin está revisando el comprobante."""
    db.table("pagos").update({"estado_pago": "En_Revision"}).eq("id", id).execute()
    log_actividad(None, "Pago puesto En_Revision", "pagos", str(id))
    return {"mensaje": "Pago marcado como En Revisión"}


@app.post("/admin/pagos/{id}/aprobar", tags=["📊 Dashboard — Pagos ⚠️"])
def admin_pago_aprobar(id: int, revisado_por: str, db: Client = Depends(get_supabase)):
    """
    ⚠️ ACCIÓN CRÍTICA — Aprueba el pago y ejecuta todo el flujo:
    1. Aprueba el pago
    2. Genera la licencia de software
    3. Activa el servicio adquirido
    4. Notifica al usuario
    5. Registra en historial_actividad
    """
    # 1. Obtener el pago y el servicio
    pago = db.table("pagos").select(
        "*, servicios_adquiridos(*, software_id, plan_id, usuario_id)"
    ).eq("id", id).single().execute()
    not_found(pago.data, "Pago no encontrado")

    # Validar que tenga comprobante si es Yape/Plin
    if pago.data.get("metodo_pago") in ["Yape", "Plin"] and not pago.data.get("comprobante_url"):
        raise HTTPException(status_code=400, detail="No se puede aprobar sin comprobante de pago")

    usuario_id = pago.data["usuario_id"]
    servicio   = pago.data.get("servicios_adquiridos", {})
    software_id = servicio.get("software_id") if servicio else None

    # 2. Aprobar pago
    from datetime import datetime
    db.table("pagos").update({
        "estado_pago": "Aprobado",
        "revisado_por": revisado_por,
        "fecha_revision": datetime.utcnow().isoformat()
    }).eq("id", id).execute()

    # 3. Activar servicio adquirido
    if pago.data.get("servicio_id"):
        db.table("servicios_adquiridos").update({"estado": "Activo"}).eq("id", pago.data["servicio_id"]).execute()

    # 4. Generar licencia si el pago es de software
    if software_id:
        clave = str(uuid.uuid4()).replace("-", "").upper()[:20]
        db.table("licencias").insert({
            "software_id": software_id,
            "usuario_id": usuario_id,
            "servicio_id": pago.data.get("servicio_id"),
            "clave_licencia": clave,
            "estado": "Activa"
        }).execute()

    # 5. Notificar al usuario
    db.table("notificaciones").insert({
        "usuario_id": usuario_id,
        "titulo": "✅ Pago aprobado",
        "mensaje": "Tu pago ha sido verificado y aprobado. Ya puedes acceder a tu producto.",
        "tipo": "pago",
        "enlace_url": "/mis-licencias"
    }).execute()

    # 6. Registrar en historial
    log_actividad(revisado_por, "Pago aprobado y licencia generada", "pagos", str(id), {
        "software_id": software_id,
        "usuario_id": usuario_id
    })

    return {"mensaje": "Pago aprobado, licencia generada y usuario notificado"}


@app.post("/admin/pagos/{id}/rechazar", tags=["📊 Dashboard — Pagos ⚠️"])
def admin_pago_rechazar(id: int, body: PagoRechazo, revisado_por: str, db: Client = Depends(get_supabase)):
    """Rechaza un pago con motivo. Notifica al usuario."""
    from datetime import datetime
    pago = db.table("pagos").select("usuario_id").eq("id", id).single().execute()
    not_found(pago.data)

    db.table("pagos").update({
        "estado_pago": "Rechazado",
        "notas_revision": body.motivo,
        "revisado_por": revisado_por,
        "fecha_revision": datetime.utcnow().isoformat()
    }).eq("id", id).execute()

    # Notificar al usuario
    db.table("notificaciones").insert({
        "usuario_id": pago.data["usuario_id"],
        "titulo": "❌ Pago rechazado",
        "mensaje": f"Tu pago fue rechazado. Motivo: {body.motivo}",
        "tipo": "pago",
        "enlace_url": "/mis-pagos"
    }).execute()

    log_actividad(revisado_por, f"Pago rechazado. Motivo: {body.motivo}", "pagos", str(id))
    return {"mensaje": "Pago rechazado y usuario notificado"}


@app.post("/admin/pagos/{id}/reembolso", tags=["📊 Dashboard — Pagos ⚠️"])
def admin_pago_reembolso(id: int, body: PagoReembolso, revisado_por: str, db: Client = Depends(get_supabase)):
    """Marca el pago como Reembolsado y notifica al cliente."""
    pago = db.table("pagos").select("usuario_id, servicio_id").eq("id", id).single().execute()
    not_found(pago.data)

    db.table("pagos").update({"estado_pago": "Reembolsado", "notas_revision": body.motivo}).eq("id", id).execute()

    # Desactivar el servicio asociado
    if pago.data.get("servicio_id"):
        db.table("servicios_adquiridos").update({"estado": "Inactivo"}).eq("id", pago.data["servicio_id"]).execute()

    db.table("notificaciones").insert({
        "usuario_id": pago.data["usuario_id"],
        "titulo": "💰 Reembolso procesado",
        "mensaje": "Tu reembolso ha sido procesado. Contáctanos si tienes dudas.",
        "tipo": "pago"
    }).execute()

    log_actividad(revisado_por, "Pago reembolsado", "pagos", str(id))
    return {"mensaje": "Reembolso registrado y usuario notificado"}


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: LICENCIAS
# Si modularizas → 📁 app/routers/dashboard/licencias.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/licencias", tags=["📊 Dashboard — Licencias"])
def admin_listar_licencias(
    estado: Optional[str] = None,
    db: Client = Depends(get_supabase)
):
    """Lista todas las licencias con filtro de estado opcional."""
    query = db.table("licencias").select("*, usuarios(nombre_completo, email), software_venta(nombre_sistema)")
    if estado:
        query = query.eq("estado", estado)
    return query.execute().data


@app.get("/admin/licencias/{id}", tags=["📊 Dashboard — Licencias"])
def admin_detalle_licencia(id: int, db: Client = Depends(get_supabase)):
    """Detalle completo de una licencia."""
    res = db.table("licencias").select(
        "*, usuarios(nombre_completo, email), software_venta(*), servicios_adquiridos(*)"
    ).eq("id", id).single().execute()
    not_found(res.data)
    return res.data


@app.post("/admin/licencias/{id}/revocar", tags=["📊 Dashboard — Licencias"])
def admin_revocar_licencia(id: int, db: Client = Depends(get_supabase)):
    """Revoca una licencia activa permanentemente."""
    db.table("licencias").update({"estado": "Revocada"}).eq("id", id).execute()
    log_actividad(None, "Licencia revocada", "licencias", str(id))
    return {"mensaje": "Licencia revocada"}


@app.post("/admin/licencias/{id}/suspender", tags=["📊 Dashboard — Licencias"])
def admin_suspender_licencia(id: int, db: Client = Depends(get_supabase)):
    """Suspende una licencia temporalmente."""
    db.table("licencias").update({"estado": "Suspendida"}).eq("id", id).execute()
    log_actividad(None, "Licencia suspendida", "licencias", str(id))
    return {"mensaje": "Licencia suspendida"}


@app.post("/admin/licencias/{id}/renovar", tags=["📊 Dashboard — Licencias"])
def admin_renovar_licencia(id: int, body: LicenciaRenovar, db: Client = Depends(get_supabase)):
    """Renueva o extiende la fecha de expiración de una licencia."""
    db.table("licencias").update({
        "estado": "Activa",
        "fecha_expiracion": str(body.nueva_fecha_expiracion)
    }).eq("id", id).execute()
    log_actividad(None, "Licencia renovada", "licencias", str(id))
    return {"mensaje": "Licencia renovada hasta " + str(body.nueva_fecha_expiracion)}


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: TICKETS DE SOPORTE
# Si modularizas → 📁 app/routers/dashboard/tickets.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/tickets", tags=["📊 Dashboard — Tickets"])
def admin_listar_tickets(
    estado: Optional[str] = None,
    prioridad: Optional[str] = None,
    db: Client = Depends(get_supabase)
):
    """Lista todos los tickets de soporte con filtros."""
    query = db.table("tickets_soporte").select("*, usuarios(nombre_completo, email)").order("id", desc=True)
    if estado:
        query = query.eq("estado", estado)
    if prioridad:
        query = query.eq("prioridad", prioridad)
    return query.execute().data


@app.get("/admin/tickets/{id}", tags=["📊 Dashboard — Tickets"])
def admin_detalle_ticket(id: int, db: Client = Depends(get_supabase)):
    """Detalle del ticket con todos sus mensajes (incluye notas internas)."""
    ticket   = db.table("tickets_soporte").select("*, usuarios(*)").eq("id", id).single().execute()
    mensajes = db.table("mensajes_ticket").select("*, usuarios(nombre_completo, rol)").eq("ticket_id", id).order("id").execute()
    not_found(ticket.data)
    return {"ticket": ticket.data, "mensajes": mensajes.data}


@app.post("/admin/tickets/{id}/asignar", tags=["📊 Dashboard — Tickets"])
def admin_asignar_ticket(id: int, body: TicketAsignar, db: Client = Depends(get_supabase)):
    """Asigna el ticket a un agente de soporte."""
    db.table("tickets_soporte").update({
        "asignado_a": body.asignado_a,
        "estado": "En_Progreso"
    }).eq("id", id).execute()
    return {"mensaje": "Ticket asignado"}


@app.post("/admin/tickets/{id}/estado", tags=["📊 Dashboard — Tickets"])
def admin_estado_ticket(id: int, body: TicketEstado, db: Client = Depends(get_supabase)):
    """Cambia el estado del ticket: En_Progreso | Resuelto | Cerrado."""
    update_data: dict = {"estado": body.estado}
    if body.estado in ["Resuelto", "Cerrado"]:
        from datetime import datetime
        update_data["fecha_cierre"] = datetime.utcnow().isoformat()
    db.table("tickets_soporte").update(update_data).eq("id", id).execute()
    return {"mensaje": f"Estado actualizado a {body.estado}"}


@app.post("/admin/tickets/{id}/mensaje", tags=["📊 Dashboard — Tickets"])
def admin_responder_ticket(id: int, body: TicketMensaje, autor_id: str, db: Client = Depends(get_supabase)):
    """
    Agrega un mensaje al ticket.
    Si es_interno=True → solo visible para el equipo de soporte.
    """
    res = db.table("mensajes_ticket").insert({
        "ticket_id": id,
        "usuario_id": autor_id,
        "contenido": body.contenido,
        "es_interno": body.es_interno
    }).execute()

    # Si no es interno, notificar al cliente
    if not body.es_interno:
        ticket = db.table("tickets_soporte").select("usuario_id").eq("id", id).single().execute()
        if ticket.data:
            db.table("notificaciones").insert({
                "usuario_id": ticket.data["usuario_id"],
                "titulo": "💬 Respuesta en tu ticket",
                "mensaje": "El equipo de soporte ha respondido tu ticket.",
                "tipo": "ticket",
                "enlace_url": f"/mis-tickets/{id}"
            }).execute()

    return res.data[0]


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: CUPONES
# Si modularizas → 📁 app/routers/dashboard/cupones.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/cupones", tags=["📊 Dashboard — Cupones"])
def admin_listar_cupones(db: Client = Depends(get_supabase)):
    """Lista todos los cupones de descuento."""
    return db.table("cupones").select("*").order("id", desc=True).execute().data


@app.post("/admin/cupones", tags=["📊 Dashboard — Cupones"], status_code=201)
def admin_crear_cupon(body: CuponCreate, db: Client = Depends(get_supabase)):
    """Crea un nuevo cupón de descuento."""
    res = db.table("cupones").insert(body.dict(exclude_none=True)).execute()
    handle_db_error(res)
    return res.data[0]


@app.post("/admin/cupones/{id}", tags=["📊 Dashboard — Cupones"])
def admin_editar_cupon(id: int, body: CuponCreate, db: Client = Depends(get_supabase)):
    """Edita un cupón existente."""
    res = db.table("cupones").update(body.dict(exclude_none=True)).eq("id", id).execute()
    handle_db_error(res)
    return res.data[0] if res.data else {"mensaje": "Actualizado"}


@app.post("/admin/cupones/{id}/estado", tags=["📊 Dashboard — Cupones"])
def admin_estado_cupon(id: int, body: CuponEstado, db: Client = Depends(get_supabase)):
    """Activa o desactiva un cupón."""
    db.table("cupones").update({"activo": body.activo}).eq("id", id).execute()
    return {"mensaje": "Estado del cupón actualizado"}


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: LEADS
# Si modularizas → 📁 app/routers/dashboard/leads.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/leads", tags=["📊 Dashboard — Leads"])
def admin_listar_leads(
    estado: Optional[str] = None,
    db: Client = Depends(get_supabase)
):
    """Lista todos los leads capturados desde el formulario de contacto."""
    query = db.table("leads").select("*").order("id", desc=True)
    if estado:
        query = query.eq("estado", estado)
    return query.execute().data


@app.get("/admin/leads/{id}", tags=["📊 Dashboard — Leads"])
def admin_detalle_lead(id: int, db: Client = Depends(get_supabase)):
    """Detalle completo de un lead."""
    res = db.table("leads").select("*, usuarios(nombre_completo)").eq("id", id).single().execute()
    not_found(res.data)
    return res.data


@app.post("/admin/leads/{id}/estado", tags=["📊 Dashboard — Leads"])
def admin_estado_lead(id: int, body: LeadEstado, db: Client = Depends(get_supabase)):
    """
    Actualiza el estado del lead:
    Nuevo | Contactado | Calificado | Convertido | Descartado
    """
    from datetime import datetime
    update_data: dict = {"estado": body.estado}
    if body.atendido_por:
        update_data["atendido_por"] = body.atendido_por
    if body.estado == "Contactado":
        update_data["fecha_contacto"] = datetime.utcnow().isoformat()
    db.table("leads").update(update_data).eq("id", id).execute()
    return {"mensaje": f"Lead actualizado a {body.estado}"}


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: RESEÑAS (Moderación)
# Si modularizas → 📁 app/routers/dashboard/resenas.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/resenas", tags=["📊 Dashboard — Reseñas"])
def admin_listar_resenas(
    estado: Optional[str] = None,
    db: Client = Depends(get_supabase)
):
    """Lista todas las reseñas pendientes de moderación o ya procesadas."""
    query = db.table("opiniones_resenas").select("*, usuarios(nombre_completo), software_venta(nombre_sistema), planes_web(nombre_plan)")
    if estado:
        query = query.eq("estado_moderacion", estado)
    return query.execute().data


@app.post("/admin/resenas/{id}/aprobar", tags=["📊 Dashboard — Reseñas"])
def admin_aprobar_resena(id: int, moderador_id: str, db: Client = Depends(get_supabase)):
    """Aprueba una reseña para que sea visible públicamente."""
    db.table("opiniones_resenas").update({
        "estado_moderacion": "Aprobado",
        "moderado_por": moderador_id
    }).eq("id", id).execute()
    return {"mensaje": "Reseña aprobada"}


@app.post("/admin/resenas/{id}/rechazar", tags=["📊 Dashboard — Reseñas"])
def admin_rechazar_resena(id: int, moderador_id: str, db: Client = Depends(get_supabase)):
    """Rechaza una reseña (no se mostrará públicamente)."""
    db.table("opiniones_resenas").update({
        "estado_moderacion": "Rechazado",
        "moderado_por": moderador_id
    }).eq("id", id).execute()
    return {"mensaje": "Reseña rechazada"}


# ──────────────────────────────────────────────────────────────────────
# [DASHBOARD] MÓDULO: ANALYTICS / DASHBOARD ANALÍTICO
# Si modularizas → 📁 app/routers/dashboard/analytics.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/admin/dashboard/resumen", tags=["📊 Dashboard — Analytics"])
def admin_dashboard_resumen(db: Client = Depends(get_supabase)):
    """
    Resumen ejecutivo del dashboard:
    - Ventas totales
    - Pagos pendientes
    - Usuarios registrados
    - Tickets abiertos
    - Productos más vendidos
    """
    pagos_aprobados = db.table("pagos").select("monto_final").eq("estado_pago", "Aprobado").execute()
    ventas_totales  = sum(p.get("monto_final", 0) for p in (pagos_aprobados.data or []))

    pagos_pendientes  = db.table("pagos").select("id", count="exact").eq("estado_pago", "Pendiente").execute()
    total_usuarios    = db.table("usuarios").select("id", count="exact").execute()
    tickets_abiertos  = db.table("tickets_soporte").select("id", count="exact").eq("estado", "Abierto").execute()

    return {
        "ventas_totales_soles": ventas_totales,
        "pagos_pendientes": pagos_pendientes.count,
        "usuarios_registrados": total_usuarios.count,
        "tickets_abiertos": tickets_abiertos.count,
    }


@app.get("/admin/dashboard/ventas-mensuales", tags=["📊 Dashboard — Analytics"])
def admin_ventas_mensuales(db: Client = Depends(get_supabase)):
    """Pagos aprobados agrupados por mes para gráficas de tendencia."""
    res = db.table("pagos").select("monto_final, comprobante_subido_en").eq("estado_pago", "Aprobado").execute()

    from collections import defaultdict
    mensuales: dict = defaultdict(float)
    for pago in (res.data or []):
        fecha = pago.get("comprobante_subido_en", "")
        if fecha:
            mes = fecha[:7]  # YYYY-MM
            mensuales[mes] += pago.get("monto_final", 0)

    return [{"mes": k, "total": v} for k, v in sorted(mensuales.items())]


@app.get("/admin/dashboard/productos-top", tags=["📊 Dashboard — Analytics"])
def admin_productos_top(db: Client = Depends(get_supabase)):
    """Los productos más comprados (software + planes)."""
    sw  = db.table("servicios_adquiridos").select("software_id, software_venta(nombre_sistema)").not_.is_("software_id", None).execute()
    pl  = db.table("servicios_adquiridos").select("plan_id, planes_web(nombre_plan)").not_.is_("plan_id", None).execute()

    from collections import Counter
    sw_counter = Counter(s["software_venta"]["nombre_sistema"] for s in (sw.data or []) if s.get("software_venta"))
    pl_counter = Counter(p["planes_web"]["nombre_plan"] for p in (pl.data or []) if p.get("planes_web"))

    return {
        "software_top": [{"nombre": k, "ventas": v} for k, v in sw_counter.most_common(5)],
        "planes_top":   [{"nombre": k, "ventas": v} for k, v in pl_counter.most_common(5)],
    }


@app.get("/admin/dashboard/ingresos-metodo-pago", tags=["📊 Dashboard — Analytics"])
def admin_ingresos_por_metodo(db: Client = Depends(get_supabase)):
    """
    Ingresos agrupados por método de pago.
    Muy útil para ver el peso de Yape / Plin vs otros métodos.
    """
    res = db.table("pagos").select("metodo_pago, monto_final").eq("estado_pago", "Aprobado").execute()

    from collections import defaultdict
    por_metodo: dict = defaultdict(float)
    for p in (res.data or []):
        por_metodo[p["metodo_pago"]] += p.get("monto_final", 0)

    return [{"metodo": k, "total": v} for k, v in sorted(por_metodo.items(), key=lambda x: -x[1])]


# ══════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════
#
#   ██╗    ██╗███████╗██████╗      ██████╗ ██╗     ██╗███████╗███╗   ██╗████████╗███████╗
#   ██║    ██║██╔════╝██╔══██╗    ██╔════╝ ██║     ██║██╔════╝████╗  ██║╚══██╔══╝██╔════╝
#   ██║ █╗ ██║█████╗  ██████╔╝    ██║      ██║     ██║█████╗  ██╔██╗ ██║   ██║   █████╗
#   ██║███╗██║██╔══╝  ██╔══██╗    ██║      ██║     ██║██╔══╝  ██║╚██╗██║   ██║   ██╔══╝
#   ╚███╔███╔╝███████╗██████╔╝    ╚██████╗ ███████╗██║███████╗██║ ╚████║   ██║   ███████╗
#    ╚══╝╚══╝ ╚══════╝╚═════╝      ╚═════╝ ╚══════╝╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝
#
#   PÁGINA WEB PÚBLICA + ÁREA DE CLIENTE — /productos, /auth, /mis-...
#   Si modularizas → 📁 app/routers/web/ y 📁 app/routers/usuario/
#
# ══════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════


# ──────────────────────────────────────────────────────────────────────
# [WEB] MÓDULO: PRODUCTOS (Catálogo público)
# Si modularizas → 📁 app/routers/web/productos.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/productos", tags=["🌐 Web — Productos"])
def web_listar_productos(
    categoria: Optional[int] = None,
    precio_min: Optional[float] = None,
    precio_max: Optional[float] = None,
    oferta: Optional[bool] = None,
    orden: Optional[str] = "nombre_sistema",
    calificacion: Optional[int] = None,
    db: Client = Depends(get_supabase)
):
    """
    Listado público de software.
    Filtros: categoría, rango de precio, oferta, orden, calificación mínima.
    Solo muestra software con estado 'Activo'.
    """
    query = db.table("software_venta").select(
        "*, categorias(nombre, slug)"
    ).eq("estado", "Activo")

    if categoria:
        query = query.eq("categoria_id", categoria)
    if precio_min is not None:
        query = query.gte("precio_regular", precio_min)
    if precio_max is not None:
        query = query.lte("precio_regular", precio_max)
    if oferta is not None:
        query = query.eq("es_oferta", oferta)

    data = query.execute().data or []

    # Filtro por calificación promedio (post-query)
    if calificacion:
        resenas_res = db.table("opiniones_resenas").select("software_id, calificacion").eq("estado_moderacion", "Aprobado").execute()
        from collections import defaultdict
        promedios: dict = defaultdict(list)
        for r in (resenas_res.data or []):
            promedios[r["software_id"]].append(r["calificacion"])
        data = [
            p for p in data
            if promedios.get(p["id"]) and
            (sum(promedios[p["id"]]) / len(promedios[p["id"]])) >= calificacion
        ]

    return data


@app.get("/productos/ofertas", tags=["🌐 Web — Productos"])
def web_productos_ofertas(db: Client = Depends(get_supabase)):
    """Lista de software en oferta activa."""
    return db.table("software_venta").select("*").eq("estado", "Activo").eq("es_oferta", True).execute().data


@app.get("/productos/recomendados", tags=["🌐 Web — Productos"])
def web_productos_recomendados(db: Client = Depends(get_supabase)):
    """Software recomendado: los 6 más descargados y activos."""
    return db.table("software_venta").select("*").eq("estado", "Activo").order("contador_descargas", desc=True).limit(6).execute().data


@app.get("/productos/populares", tags=["🌐 Web — Productos"])
def web_productos_populares(db: Client = Depends(get_supabase)):
    """Software más popular por número de ventas."""
    return db.table("software_venta").select("*").eq("estado", "Activo").order("contador_descargas", desc=True).limit(10).execute().data


@app.get("/productos/buscar", tags=["🌐 Web — Productos"])
def web_buscar_productos(nombre: str = Query(..., min_length=2), db: Client = Depends(get_supabase)):
    """Búsqueda de software por nombre (búsqueda parcial)."""
    return db.table("software_venta").select("*, categorias(nombre)").eq("estado", "Activo").ilike("nombre_sistema", f"%{nombre}%").execute().data


@app.get("/productos/categoria/{slug}", tags=["🌐 Web — Productos"])
def web_productos_por_categoria(slug: str, db: Client = Depends(get_supabase)):
    """Lista de software filtrado por slug de categoría."""
    cat = db.table("categorias").select("id").eq("slug", slug).single().execute()
    not_found(cat.data, f"Categoría '{slug}' no encontrada")
    return db.table("software_venta").select("*, categorias(nombre, slug)").eq("estado", "Activo").eq("categoria_id", cat.data["id"]).execute().data


@app.get("/productos/{id}", tags=["🌐 Web — Productos"])
def web_detalle_producto(id: int, db: Client = Depends(get_supabase)):
    """
    Detalle público de un software.
    Incluye: descripción completa, características, reseñas aprobadas, demo, video.
    """
    sw = db.table("software_venta").select("*, categorias(*)").eq("id", id).eq("estado", "Activo").single().execute()
    not_found(sw.data, "Producto no encontrado")
    detalles = db.table("detalles_items").select("*").eq("item_id", id).eq("tipo_item", "software").order("orden").execute()
    resenas  = db.table("opiniones_resenas").select("nombre_autor, calificacion, comentario").eq("software_id", id).eq("estado_moderacion", "Aprobado").execute()
    return {"software": sw.data, "detalles": detalles.data, "resenas": resenas.data}


@app.get("/productos/relacionados/{id}", tags=["🌐 Web — Productos"])
def web_productos_relacionados(id: int, db: Client = Depends(get_supabase)):
    """Productos relacionados (misma categoría, excluyendo el actual)."""
    sw = db.table("software_venta").select("categoria_id").eq("id", id).single().execute()
    if not sw.data:
        return []
    return db.table("software_venta").select("id, nombre_sistema, precio_regular, url_imagen").eq("estado", "Activo").eq("categoria_id", sw.data["categoria_id"]).neq("id", id).limit(4).execute().data


# ──────────────────────────────────────────────────────────────────────
# [WEB] MÓDULO: PLANES (Vista pública)
# Si modularizas → 📁 app/routers/web/planes.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/planes", tags=["🌐 Web — Planes"])
def web_listar_planes(db: Client = Depends(get_supabase)):
    """Lista todos los planes web activos con sus características."""
    planes = db.table("planes_web").select("*").eq("estado", "Activo").order("orden").execute().data or []
    for plan in planes:
        plan["detalles"] = db.table("detalles_items").select("*").eq("item_id", plan["id"]).eq("tipo_item", "plan").order("orden").execute().data
    return planes


@app.get("/planes/{id}", tags=["🌐 Web — Planes"])
def web_detalle_plan(id: int, db: Client = Depends(get_supabase)):
    """Detalle de un plan web con sus características."""
    plan = db.table("planes_web").select("*").eq("id", id).eq("estado", "Activo").single().execute()
    not_found(plan.data, "Plan no encontrado")
    detalles = db.table("detalles_items").select("*").eq("item_id", id).eq("tipo_item", "plan").order("orden").execute()
    return {"plan": plan.data, "detalles": detalles.data}


# ──────────────────────────────────────────────────────────────────────
# [WEB + USUARIO] MÓDULO: AUTENTICACIÓN
# Si modularizas → 📁 app/routers/web/auth.py
# ──────────────────────────────────────────────────────────────────────

@app.post("/auth/register", tags=["🔐 Auth"])
def auth_register(body: RegisterRequest, db: Client = Depends(get_supabase)):
    """
    Registro de nuevo usuario cliente.
    Crea: auth.users → usuarios → clientes (automático por trigger en BD).
    """
    try:
        res = db.auth.sign_up({"email": body.email, "password": body.password})
        if not res.user:
            raise HTTPException(status_code=400, detail="No se pudo crear la cuenta")

        uid = res.user.id
        # Upsert en caso de que el trigger no haya creado el registro aún
        db.table("usuarios").upsert({
            "id": uid,
            "nombre_completo": body.nombre_completo,
            "email": body.email,
            "rol": "cliente"
        }).execute()

        # Crear perfil de cliente
        db.table("clientes").upsert({"usuario_id": uid}).execute()

        return {"mensaje": "Cuenta creada. Verifica tu correo.", "id": uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login", tags=["🔐 Auth"])
def auth_login(body: LoginRequest, db: Client = Depends(get_supabase)):
    """Login con email y contraseña. Retorna tokens de sesión."""
    try:
        res = db.auth.sign_in_with_password({"email": body.email, "password": body.password})
        if not res.user:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")

        # Actualizar último acceso
        from datetime import datetime
        db.table("usuarios").update({"ultimo_acceso": datetime.utcnow().isoformat()}).eq("id", res.user.id).execute()

        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "usuario": {"id": res.user.id, "email": res.user.email}
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")


@app.post("/auth/logout", tags=["🔐 Auth"])
def auth_logout(db: Client = Depends(get_supabase)):
    """Cierra la sesión del usuario actual."""
    db.auth.sign_out()
    return {"mensaje": "Sesión cerrada"}


@app.get("/auth/perfil", tags=["🔐 Auth"])
def auth_get_perfil(usuario_id: str, db: Client = Depends(get_supabase)):
    """
    [WEB + USUARIO] Obtiene el perfil completo del usuario logueado.
    Incluye datos de usuario + perfil de cliente.
    Úsalo tanto en el navbar como en el panel de usuario.
    """
    res = db.table("usuarios").select("*, clientes(*)").eq("id", usuario_id).single().execute()
    not_found(res.data, "Usuario no encontrado")
    return res.data


@app.post("/auth/perfil", tags=["🔐 Auth"])
def auth_update_perfil(usuario_id: str, body: PerfilUpdate, db: Client = Depends(get_supabase)):
    """
    [WEB + USUARIO] Actualiza el perfil del usuario logueado.
    Actualiza nombre en 'usuarios' y datos extendidos en 'clientes'.
    """
    if body.nombre_completo:
        db.table("usuarios").update({"nombre_completo": body.nombre_completo}).eq("id", usuario_id).execute()
    if body.avatar_url:
        db.table("usuarios").update({"avatar_url": body.avatar_url}).eq("id", usuario_id).execute()

    cliente_data = body.dict(exclude_none=True, exclude={"nombre_completo", "avatar_url"})
    if cliente_data:
        db.table("clientes").update(cliente_data).eq("usuario_id", usuario_id).execute()

    return {"mensaje": "Perfil actualizado"}


# ──────────────────────────────────────────────────────────────────────
# [WEB] MÓDULO: CARRITO Y CHECKOUT
# Si modularizas → 📁 app/routers/web/carrito.py
# ──────────────────────────────────────────────────────────────────────

# Carrito en memoria por sesión (en producción usar Redis o tabla en BD)
_carritos: dict = {}

@app.get("/carrito", tags=["🛒 Web — Carrito"])
def web_ver_carrito(session_id: str):
    """
    Retorna el carrito actual del usuario.
    En producción conectar con una tabla 'carrito' en Supabase.
    """
    return {"items": _carritos.get(session_id, [])}


@app.post("/carrito/agregar", tags=["🛒 Web — Carrito"])
def web_agregar_carrito(session_id: str, body: CarritoAgregar, db: Client = Depends(get_supabase)):
    """Agrega un producto (software o plan) al carrito."""
    if session_id not in _carritos:
        _carritos[session_id] = []

    # Verificar que el producto existe
    if body.tipo == "software":
        producto = db.table("software_venta").select("id, nombre_sistema, precio_regular, precio_oferta, es_oferta").eq("id", body.producto_id).eq("estado", "Activo").single().execute()
    else:
        producto = db.table("planes_web").select("id, nombre_plan, precio").eq("id", body.producto_id).eq("estado", "Activo").single().execute()

    not_found(producto.data, "Producto no encontrado")
    _carritos[session_id].append({"tipo": body.tipo, **producto.data})
    return {"mensaje": "Producto agregado", "carrito": _carritos[session_id]}


@app.post("/carrito/eliminar", tags=["🛒 Web — Carrito"])
def web_eliminar_carrito(session_id: str, body: CarritoEliminar):
    """Elimina un producto del carrito."""
    if session_id in _carritos:
        _carritos[session_id] = [
            i for i in _carritos[session_id]
            if not (i["id"] == body.producto_id and i["tipo"] == body.tipo)
        ]
    return {"mensaje": "Producto eliminado", "carrito": _carritos.get(session_id, [])}


@app.post("/checkout", tags=["🛒 Web — Carrito"])
def web_checkout(usuario_id: str, body: CheckoutRequest, db: Client = Depends(get_supabase)):
    """
    Genera el servicio adquirido y el pago pendiente.
    Crea: servicios_adquiridos + pagos (en estado Pendiente).
    El usuario luego sube el comprobante para completar el pago.
    """
    # Obtener precio del producto
    cupon_id = None
    descuento = 0.0

    if body.tipo == "software":
        prod = db.table("software_venta").select("precio_regular, precio_oferta, es_oferta").eq("id", body.producto_id).single().execute()
        not_found(prod.data)
        precio = prod.data["precio_oferta"] if prod.data["es_oferta"] and prod.data.get("precio_oferta") else prod.data["precio_regular"]
        sw_id, pl_id = body.producto_id, None
    else:
        prod = db.table("planes_web").select("precio").eq("id", body.producto_id).single().execute()
        not_found(prod.data)
        precio = prod.data["precio"]
        sw_id, pl_id = None, body.producto_id

    # Aplicar cupón si existe
    if body.cupon_codigo:
        cupon = db.table("cupones").select("*").eq("codigo", body.cupon_codigo).eq("activo", True).single().execute()
        if cupon.data:
            cupon_id = cupon.data["id"]
            if cupon.data.get("descuento_porcentaje"):
                descuento = precio * (cupon.data["descuento_porcentaje"] / 100)
            elif cupon.data.get("descuento_monto"):
                descuento = cupon.data["descuento_monto"]

    monto_final = round(precio - descuento, 2)

    # Crear servicio adquirido
    servicio = db.table("servicios_adquiridos").insert({
        "usuario_id": usuario_id,
        "software_id": sw_id,
        "plan_id": pl_id,
        "cupon_id": cupon_id,
        "modalidad": "Compra",
        "estado": "Inactivo"  # Se activa al aprobar el pago
    }).execute()

    servicio_id = servicio.data[0]["id"]

    # Crear pago pendiente
    pago = db.table("pagos").insert({
        "usuario_id": usuario_id,
        "servicio_id": servicio_id,
        "cupon_id": cupon_id,
        "monto_original": precio,
        "descuento_aplicado": descuento,
        "monto_final": monto_final,
        "metodo_pago": "Yape",     # El usuario elige el método al subir el comprobante
        "estado_pago": "Pendiente"
    }).execute()

    return {
        "mensaje": "Orden creada. Sube tu comprobante de pago para confirmar.",
        "servicio_id": servicio_id,
        "pago_id": pago.data[0]["id"],
        "monto_final": monto_final
    }


# ──────────────────────────────────────────────────────────────────────
# [WEB] MÓDULO: PAGOS DEL CLIENTE (Yape / Plin)
# Si modularizas → 📁 app/routers/web/pagos.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/pagos/metodos", tags=["💳 Web — Pagos"])
def web_metodos_pago():
    """
    Devuelve los métodos de pago disponibles con QR, números e instrucciones.
    Actualiza estos datos según la info real de OCA.
    """
    return {
        "metodos": [
            {
                "nombre": "Yape",
                "numero": "999-999-999",          # 🔧 Actualizar con número real de OCA
                "qr_url": "https://ohfwdxggjhomkthbqacu.supabase.co/storage/v1/object/public/qr/yape.png",
                "instrucciones": "Abre Yape, escanea el QR o ingresa el número, realiza el pago y sube la captura."
            },
            {
                "nombre": "Plin",
                "numero": "999-999-999",          # 🔧 Actualizar con número real de OCA
                "qr_url": "https://ohfwdxggjhomkthbqacu.supabase.co/storage/v1/object/public/qr/plin.png",
                "instrucciones": "Abre Plin, escanea el QR o ingresa el número, realiza el pago y sube la captura."
            },
            {
                "nombre": "Transferencia_Bancaria",
                "banco": "BCP",
                "cuenta": "000-00000000-0-00",    # 🔧 Actualizar con cuenta real de OCA
                "cci": "00200000000000000000",
                "instrucciones": "Realiza la transferencia y envía el comprobante."
            }
        ]
    }


@app.post("/pagos/subir-comprobante", tags=["💳 Web — Pagos"])
def web_subir_comprobante(body: SubirComprobante, db: Client = Depends(get_supabase)):
    """
    El cliente sube el comprobante de pago (Yape/Plin).
    Actualiza el registro de pago con los datos del comprobante.
    La URL del comprobante debe estar ya subida a Supabase Storage.
    """
    from datetime import datetime
    db.table("pagos").update({
        "numero_operacion": body.numero_operacion,
        "comprobante_url": body.comprobante_url,
        "metodo_pago": body.metodo_pago,
        "numero_telefono_pagador": body.numero_telefono_pagador,
        "nombre_titular_cuenta": body.nombre_titular_cuenta,
        "comprobante_subido_en": datetime.utcnow().isoformat(),
        "estado_pago": "Pendiente"
    }).eq("id", body.servicio_id).execute()

    # Notificar al admin (aquí podrías enviar email o webhook)
    return {"mensaje": "Comprobante subido exitosamente. Estamos verificando tu pago."}


# ──────────────────────────────────────────────────────────────────────
# [WEB] MÓDULO: VALIDAR CUPÓN
# [COMPARTIDO] Usado tanto en checkout web como potencialmente en dashboard
# Si modularizas → 📁 app/routers/web/cupones.py
# ──────────────────────────────────────────────────────────────────────

@app.post("/cupon/validar", tags=["🎟️ Web — Cupones"])
def web_validar_cupon(body: ValidarCupon, db: Client = Depends(get_supabase)):
    """
    Valida un cupón antes de pagar.
    Retorna el descuento aplicado y el monto final.
    """
    from datetime import date as date_type
    cupon = db.table("cupones").select("*").eq("codigo", body.cupon_codigo).eq("activo", True).single().execute()

    if not cupon.data:
        raise HTTPException(status_code=404, detail="Cupón inválido o inactivo")

    c = cupon.data

    # Verificar expiración
    if c.get("fecha_expiracion") and date_type.fromisoformat(c["fecha_expiracion"]) < date_type.today():
        raise HTTPException(status_code=400, detail="El cupón ha expirado")

    # Verificar usos máximos
    if c.get("usos_maximos") and c.get("usos_actuales", 0) >= c["usos_maximos"]:
        raise HTTPException(status_code=400, detail="El cupón ha alcanzado el límite de usos")

    descuento = 0.0
    if c.get("descuento_porcentaje"):
        descuento = body.monto_original * (c["descuento_porcentaje"] / 100)
    elif c.get("descuento_monto"):
        descuento = c["descuento_monto"]

    return {
        "valido": True,
        "codigo": body.cupon_codigo,
        "descuento": round(descuento, 2),
        "monto_original": body.monto_original,
        "monto_final": round(body.monto_original - descuento, 2)
    }


# ──────────────────────────────────────────────────────────────────────
# [WEB] MÓDULO: RESEÑAS (Vista pública + Crear)
# Si modularizas → 📁 app/routers/web/resenas.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/resenas/producto/{id}", tags=["⭐ Web — Reseñas"])
def web_resenas_producto(id: int, db: Client = Depends(get_supabase)):
    """Obtiene solo las reseñas aprobadas de un software."""
    return db.table("opiniones_resenas").select("nombre_autor, calificacion, comentario").eq("software_id", id).eq("estado_moderacion", "Aprobado").execute().data


@app.post("/resenas", tags=["⭐ Web — Reseñas"], status_code=201)
def web_crear_resena(usuario_id: str, body: ResenaCreate, db: Client = Depends(get_supabase)):
    """
    Crear reseña. Solo permitido a usuarios con compra validada.
    Valida que el usuario haya comprado el producto antes de reseñar.
    Las reseñas pasan por moderación antes de publicarse.
    """
    # Verificar que el usuario tiene una compra aprobada del producto
    filtro = {"usuario_id": usuario_id, "estado": "Activo"}
    if body.software_id:
        filtro["software_id"] = body.software_id
    elif body.plan_id:
        filtro["plan_id"] = body.plan_id
    else:
        raise HTTPException(status_code=400, detail="Debes especificar software_id o plan_id")

    compra = db.table("servicios_adquiridos").select("id").match(filtro).limit(1).execute()
    if not compra.data:
        raise HTTPException(status_code=403, detail="Solo puedes reseñar productos que hayas comprado")

    if not (1 <= body.calificacion <= 5):
        raise HTTPException(status_code=400, detail="La calificación debe ser entre 1 y 5")

    res = db.table("opiniones_resenas").insert({
        "usuario_id": usuario_id,
        **body.dict(exclude_none=True),
        "estado_moderacion": "Pendiente"
    }).execute()
    return {"mensaje": "Reseña enviada. Será publicada tras moderación.", "id": res.data[0]["id"]}


# ──────────────────────────────────────────────────────────────────────
# [WEB] MÓDULO: TICKETS DE SOPORTE (Vista cliente)
# Si modularizas → 📁 app/routers/web/tickets.py
# ──────────────────────────────────────────────────────────────────────

@app.post("/tickets", tags=["🎫 Web — Soporte"], status_code=201)
def web_crear_ticket(usuario_id: str, body: TicketCreate, db: Client = Depends(get_supabase)):
    """Crea un nuevo ticket de soporte desde el portal del cliente."""
    res = db.table("tickets_soporte").insert({
        "usuario_id": usuario_id,
        "asunto": body.asunto,
        "descripcion": body.descripcion,
        "prioridad": body.prioridad,
        "estado": "Abierto"
    }).execute()
    return {"mensaje": "Ticket creado exitosamente", "id": res.data[0]["id"]}


# ──────────────────────────────────────────────────────────────────────
# [WEB] MÓDULO: CONTACTO / LEADS (Formulario público)
# Si modularizas → 📁 app/routers/web/contacto.py
# ──────────────────────────────────────────────────────────────────────

@app.post("/contacto", tags=["📬 Web — Contacto"])
def web_formulario_contacto(body: ContactoCreate, request: Request, db: Client = Depends(get_supabase)):
    """
    Formulario de contacto público. Crea un lead en el sistema.
    Disponible para visitantes sin cuenta.
    """
    ip_origen = request.client.host if request.client else None
    res = db.table("leads").insert({
        "nombre": body.nombre,
        "email": body.email,
        "telefono": body.telefono,
        "empresa": body.empresa,
        "servicio_interes": body.servicio_interes,
        "mensaje": body.mensaje,
        "estado": "Nuevo",
        "ip_origen": ip_origen
    }).execute()
    return {"mensaje": "Gracias por contactarnos. Te responderemos pronto."}


# ══════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════
#
#   ██╗   ██╗███████╗██╗   ██╗ █████╗ ██████╗ ██╗ ██████╗
#   ██║   ██║██╔════╝██║   ██║██╔══██╗██╔══██╗██║██╔═══██╗
#   ██║   ██║███████╗██║   ██║███████║██████╔╝██║██║   ██║
#   ██║   ██║╚════██║██║   ██║██╔══██║██╔══██╗██║██║   ██║
#   ╚██████╔╝███████║╚██████╔╝██║  ██║██║  ██║██║╚██████╔╝
#    ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝
#
#   PANEL DEL USUARIO LOGUEADO — /mis-... y /usuario/...
#   Si modularizas → 📁 app/routers/usuario/
#
# ══════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════


# ──────────────────────────────────────────────────────────────────────
# [USUARIO] MÓDULO: MIS PAGOS
# Si modularizas → 📁 app/routers/usuario/pagos.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/mis-pagos", tags=["👤 Usuario — Panel"])
def usuario_mis_pagos(usuario_id: str, db: Client = Depends(get_supabase)):
    """
    Historial de pagos del usuario logueado.
    Incluye estado, monto, método de pago y fecha.
    """
    return db.table("pagos").select(
        "id, monto_final, metodo_pago, estado_pago, comprobante_subido_en, notas_revision"
    ).eq("usuario_id", usuario_id).order("id", desc=True).execute().data


# ──────────────────────────────────────────────────────────────────────
# [USUARIO] MÓDULO: MIS LICENCIAS
# Si modularizas → 📁 app/routers/usuario/licencias.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/mis-licencias", tags=["👤 Usuario — Panel"])
def usuario_mis_licencias(usuario_id: str, db: Client = Depends(get_supabase)):
    """
    Licencias activas del usuario logueado.
    Incluye clave de licencia, software, estado y fecha de expiración.
    """
    return db.table("licencias").select(
        "clave_licencia, estado, fecha_activacion, fecha_expiracion, software_venta(nombre_sistema, url_descarga)"
    ).eq("usuario_id", usuario_id).execute().data


# ──────────────────────────────────────────────────────────────────────
# [USUARIO] MÓDULO: MIS TICKETS
# Si modularizas → 📁 app/routers/usuario/tickets.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/mis-tickets", tags=["👤 Usuario — Panel"])
def usuario_mis_tickets(usuario_id: str, db: Client = Depends(get_supabase)):
    """Lista de tickets de soporte del usuario logueado."""
    return db.table("tickets_soporte").select("id, asunto, estado, prioridad, fecha_apertura").eq("usuario_id", usuario_id).order("id", desc=True).execute().data


@app.get("/mis-tickets/{id}", tags=["👤 Usuario — Panel"])
def usuario_detalle_ticket(id: int, usuario_id: str, db: Client = Depends(get_supabase)):
    """Detalle de un ticket con sus mensajes (excluye notas internas del equipo)."""
    ticket = db.table("tickets_soporte").select("*").eq("id", id).eq("usuario_id", usuario_id).single().execute()
    not_found(ticket.data, "Ticket no encontrado")

    # El cliente NO ve mensajes internos
    mensajes = db.table("mensajes_ticket").select(
        "contenido, usuarios(nombre_completo, rol), id"
    ).eq("ticket_id", id).eq("es_interno", False).order("id").execute()

    return {"ticket": ticket.data, "mensajes": mensajes.data}


@app.post("/mis-tickets/{id}/mensaje", tags=["👤 Usuario — Panel"])
def usuario_responder_ticket(id: int, usuario_id: str, body: MensajeCreate, db: Client = Depends(get_supabase)):
    """El cliente agrega un mensaje a su ticket."""
    # Verificar que el ticket pertenece al usuario
    ticket = db.table("tickets_soporte").select("id").eq("id", id).eq("usuario_id", usuario_id).single().execute()
    not_found(ticket.data, "Ticket no encontrado")

    res = db.table("mensajes_ticket").insert({
        "ticket_id": id,
        "usuario_id": usuario_id,
        "contenido": body.contenido,
        "es_interno": False
    }).execute()
    return res.data[0]


# ──────────────────────────────────────────────────────────────────────
# [USUARIO] MÓDULO: NOTIFICACIONES
# Si modularizas → 📁 app/routers/usuario/notificaciones.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/mis-notificaciones", tags=["👤 Usuario — Panel"])
def usuario_mis_notificaciones(usuario_id: str, db: Client = Depends(get_supabase)):
    """Lista de notificaciones del usuario. Muestra primero las no leídas."""
    return db.table("notificaciones").select("*").eq("usuario_id", usuario_id).order("id", desc=True).execute().data


@app.post("/mis-notificaciones/{id}/leer", tags=["👤 Usuario — Panel"])
def usuario_marcar_notificacion_leida(id: int, usuario_id: str, db: Client = Depends(get_supabase)):
    """Marca una notificación como leída."""
    db.table("notificaciones").update({"leido": True}).eq("id", id).eq("usuario_id", usuario_id).execute()
    return {"mensaje": "Notificación marcada como leída"}


@app.post("/mis-notificaciones/leer-todas", tags=["👤 Usuario — Panel"])
def usuario_marcar_todas_leidas(usuario_id: str, db: Client = Depends(get_supabase)):
    """Marca todas las notificaciones del usuario como leídas."""
    db.table("notificaciones").update({"leido": True}).eq("usuario_id", usuario_id).eq("leido", False).execute()
    return {"mensaje": "Todas las notificaciones marcadas como leídas"}


# ──────────────────────────────────────────────────────────────────────
# [USUARIO] MÓDULO: HISTORIAL DE COMPRAS
# Si modularizas → 📁 app/routers/usuario/historial.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/historial-compras", tags=["👤 Usuario — Panel"])
def usuario_historial_compras(usuario_id: str, db: Client = Depends(get_supabase)):
    """
    Historial completo de servicios adquiridos por el usuario.
    Útil para el panel 'Mis Compras' del cliente.
    """
    return db.table("servicios_adquiridos").select(
        "id, modalidad, fecha_compra, proximo_vencimiento, estado, "
        "software_venta(nombre_sistema, url_imagen), "
        "planes_web(nombre_plan)"
    ).eq("usuario_id", usuario_id).order("fecha_compra", desc=True).execute().data


# ──────────────────────────────────────────────────────────────────────
# [USUARIO] MÓDULO: FAVORITOS
# Si modularizas → 📁 app/routers/usuario/favoritos.py
# ──────────────────────────────────────────────────────────────────────

# Favoritos en memoria (en producción: crear tabla 'favoritos' en Supabase)
_favoritos: dict = {}

@app.get("/favoritos", tags=["👤 Usuario — Panel"])
def usuario_ver_favoritos(usuario_id: str, db: Client = Depends(get_supabase)):
    """
    Lista de productos favoritos del usuario.
    Para persistencia real, crea una tabla 'favoritos' en Supabase
    con campos: usuario_id, producto_id, tipo (software|plan).
    """
    ids = _favoritos.get(usuario_id, [])
    resultados = []
    for item in ids:
        if item["tipo"] == "software":
            r = db.table("software_venta").select("id, nombre_sistema, precio_regular, url_imagen").eq("id", item["id"]).single().execute()
        else:
            r = db.table("planes_web").select("id, nombre_plan, precio").eq("id", item["id"]).single().execute()
        if r.data:
            resultados.append({"tipo": item["tipo"], **r.data})
    return resultados


@app.post("/favoritos", tags=["👤 Usuario — Panel"])
def usuario_toggle_favorito(usuario_id: str, body: FavoritoToggle):
    """
    Agrega o quita un producto de favoritos.
    Si ya está en favoritos → lo quita. Si no está → lo agrega.
    """
    if usuario_id not in _favoritos:
        _favoritos[usuario_id] = []

    existe = next((i for i in _favoritos[usuario_id] if i["id"] == body.producto_id and i["tipo"] == body.tipo), None)
    if existe:
        _favoritos[usuario_id].remove(existe)
        return {"mensaje": "Eliminado de favoritos", "accion": "eliminado"}
    else:
        _favoritos[usuario_id].append({"id": body.producto_id, "tipo": body.tipo})
        return {"mensaje": "Agregado a favoritos", "accion": "agregado"}


# ──────────────────────────────────────────────────────────────────────
# [USUARIO] MÓDULO: RESUMEN DEL PANEL DE USUARIO
# Si modularizas → 📁 app/routers/usuario/panel.py
# ──────────────────────────────────────────────────────────────────────

@app.get("/usuario/panel", tags=["👤 Usuario — Panel"])
def usuario_resumen_panel(usuario_id: str, db: Client = Depends(get_supabase)):
    """
    Resumen del panel del usuario logueado.
    Muestra: compras activas, licencias, tickets abiertos, notificaciones no leídas.
    Ideal para la pantalla principal del área de cliente.
    """
    compras_activas  = db.table("servicios_adquiridos").select("id", count="exact").eq("usuario_id", usuario_id).eq("estado", "Activo").execute()
    licencias_activas = db.table("licencias").select("id", count="exact").eq("usuario_id", usuario_id).eq("estado", "Activa").execute()
    tickets_abiertos  = db.table("tickets_soporte").select("id", count="exact").eq("usuario_id", usuario_id).eq("estado", "Abierto").execute()
    notif_no_leidas   = db.table("notificaciones").select("id", count="exact").eq("usuario_id", usuario_id).eq("leido", False).execute()
    pagos_pendientes  = db.table("pagos").select("id", count="exact").eq("usuario_id", usuario_id).eq("estado_pago", "Pendiente").execute()

    return {
        "compras_activas": compras_activas.count or 0,
        "licencias_activas": licencias_activas.count or 0,
        "tickets_abiertos": tickets_abiertos.count or 0,
        "notificaciones_no_leidas": notif_no_leidas.count or 0,
        "pagos_pendientes": pagos_pendientes.count or 0,
    }


@app.get("/usuario/servicios-activos", tags=["👤 Usuario — Panel"])
def usuario_servicios_activos(usuario_id: str, db: Client = Depends(get_supabase)):
    """
    Lista los servicios activos del usuario con información de vencimiento.
    Útil para mostrar alertas de renovación en el panel.
    """
    return db.table("servicios_adquiridos").select(
        "id, modalidad, proximo_vencimiento, estado, "
        "software_venta(nombre_sistema), planes_web(nombre_plan)"
    ).eq("usuario_id", usuario_id).eq("estado", "Activo").execute().data


# ══════════════════════════════════════════════════════════════════════
# ROOT — Health check
# ══════════════════════════════════════════════════════════════════════

@app.get("/", tags=["🏠 Sistema"])
def root():
    """Health check. Verifica que la API está activa."""
    return {
        "sistema": "OCA - Software & Servicios Digitales",
        "version": "2.0.0",
        "estado": "✅ Operativo",
        "docs": "/docs",
    }


# ══════════════════════════════════════════════════════════════════════
# Ejecutar con: uvicorn main:app --reload
# ══════════════════════════════════════════════════════════════════════