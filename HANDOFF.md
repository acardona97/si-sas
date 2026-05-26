# Sí S.A.S. — Handoff

**Proyecto:** Generador de documentos de constitución S.A.S. para Quarta Acompañamiento Legal S.A.S.  
**Repositorio:** https://github.com/acardona97/si-sas  
**Despliegue:** Railway (rama `main` → autodeploy)  
**Última actualización:** 2026-05-26

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Flask (Python 3.11) |
| PDF AcroForm | pypdf |
| DOCX | python-docx |
| IA | Anthropic SDK — modelo `claude-haiku-4-5-20251001` |
| Auth | Flask session + SQLite + werkzeug |
| Frontend | HTML/CSS/JS vanilla (sin framework) |
| Despliegue | Railway (`Procfile`, `runtime.txt`) |

---

## Qué se ha construido (estado actual)

### Funcionalidades completas

- **Formulario 7 pasos** guiado para constituir S.A.S.:
  - Nombre y domicilio, accionistas, representantes legales, objeto social, capital y régimen, condiciones especiales, resumen
- **Generación de paquete ZIP** con todos los documentos:
  - Estatutos (DOCX), Acta de constitución (DOCX), Pre-RUT (PDF AcroForm), RUES (PDF AcroForm), Otras Entidades (PDF AcroForm), Situación de control, Ley 1780, Responsabilidades DIAN, Grupo étnico
- **Objeto social IA**: Claude siempre reescribe el texto del usuario en formato jurídico profesional (se eliminó el shortcut de 200 chars)
- **OCR por IA**: Extracción de datos desde cédula/pasaporte y Certificado de Existencia (Claude Vision)
  - Funciona para accionistas, representante legal, y apoderado
- **Chat asistente legal** integrado (Claude Haiku)
- **Capital pagado**: lógica de dos modos — individual por accionista o global; acepta valor 0 correctamente
- **Gramática "DE PESOS"**: solo se usa después de millón/millones
- **Landing page** pública con planes y hero estilo Quarta
- **Sistema de autenticación**: login, register, logout con Flask sessions + SQLite
- **Panel de administración** `/admin`: ver usuarios, cambiar plan, activar/desactivar
- **Protección de rutas**: `/app` y todas las `/api/*` requieren sesión activa

### Diseño

- Paleta: navy `#0C1E35`, gold `#B8920A`, fondo cálido `#F7F5F2`
- Tipografía: Playfair Display (display) + Inter (body)
- Inspirado en quarta.co

---

## Variables de entorno requeridas (Railway)

| Variable | Descripción |
|---|---|
| `ANTHROPIC_API_KEY` | Clave de la API de Claude (ya configurada) |
| `ADMIN_EMAIL` | Correo del administrador (se crea/actualiza al arrancar) |
| `ADMIN_PASSWORD` | Contraseña del admin (mín. 12 chars) |
| `SECRET_KEY` | Clave secreta para Flask sessions (cadena aleatoria larga) |

---

## Problemas resueltos en este ciclo de desarrollo

| Problema | Causa | Fix aplicado |
|---|---|---|
| Modelo Claude 404 | Cuenta solo tiene modelos Claude 4.x | Se agregó `/api/debug/models` temporal; se cambió a `claude-haiku-4-5-20251001` |
| Capital pagado artículo 6 = suscrito cuando es 0 | Backend tenía fallback `if pagado <= 0: pagado = suscrito` | Se eliminó fallback; se acepta 0 explícito |
| Auto-relleno capital_pagado asumía 1M | `syncPorcentaje` leía `capital_suscrito` antes de que el usuario lo llenara | Se eliminó auto-relleno; usuario llena capital_pagado manualmente |
| "SEISCIENTOS MIL DE PESOS" (gramática) | `_monto_letras_cifras()` siempre ponía "DE PESOS" | Conector "DE PESOS" solo cuando termina en millón/millones |
| Fuente rara en PDF Otras Entidades | Regex `(/F\w+)` no capturaba `/Helv` ni otros nombres estándar | Cambiado a `(/[\w+]+)\s+[\d.]+\s+Tf` |

---

## Arquitectura de archivos clave

```
si_sas_proyecto/
├── src/
│   ├── app.py              # Flask app, rutas, auth middleware
│   ├── auth.py             # SQLite user management
│   ├── processors/
│   │   ├── estatutos.py    # Genera DOCX de estatutos
│   │   ├── objeto_social.py # IA para objeto social
│   │   └── pdf_filler.py   # Llena AcroForms PDF
│   ├── static/
│   │   ├── css/style.css   # Design system completo (v=20260525a)
│   │   └── js/app.js       # Lógica frontend
│   └── templates/
│       ├── index.html      # Formulario principal (/app)
│       ├── landing.html    # Página de inicio (/)
│       ├── auth.html       # Login + Register
│       └── admin.html      # Panel administrador (/admin)
├── plantillas/             # PDFs AcroForm de plantilla
├── data/
│   ├── listado_ciiu.json
│   └── users.db            # SQLite (se crea automáticamente)
├── Procfile                # web: python src/app.py
└── runtime.txt             # python-3.11.9
```

---

## Flujo de autenticación

```
/ (landing)
  ↓ no sesión
/login o /register
  ↓ sesión válida
/app  (formulario completo)
  ↓ plan == 'admin'
/admin (gestión de usuarios)
```

Planes disponibles: `basic` (350k), `standard` (750k), `premium` (1.6M), `admin`.  
Por ahora todos los planes tienen acceso igual al formulario. La restricción por plan se implementa en fase de pagos.

---

## Pendiente / Próximos pasos

### Alta prioridad

- [ ] **Persistencia Railway**: agregar Volume montado en `/app/data` para que `users.db` sobreviva redeploys. Sin esto, los usuarios se pierden en cada deploy (el admin se recrea desde env vars, pero no los demás).
- [ ] **Ruta `/admin/add-user`**: crear usuarios directamente desde el panel sin que tengan que registrarse (útil para onboarding manual de clientes).
- [ ] **Verificar Otras Entidades PDF**: confirmar visualmente que el fix del font regex resuelve la fuente rara. Si sigue mal, puede ser el template mismo (ver `plantillas/otras_entidades.pdf`).

### Media prioridad

- [ ] **Integración de pagos**: Wompi o Bold para Colombia. Después del pago → asignar plan automáticamente al usuario.
- [ ] **Email de confirmación**: enviar ZIP por correo al generar documentos (SendGrid o similar).
- [ ] **Dashboard de usuario**: página `/dashboard` donde el usuario ve sus generaciones anteriores y su plan.
- [ ] **Límites por plan**: actualmente todos los planes tienen acceso igual. Implementar restricciones reales (ej: Basic = 1 generación, Standard = ilimitado).

### Baja prioridad

- [ ] **Migrar de SQLite a PostgreSQL**: Railway provee Postgres gratis. Elimina el problema de persistencia de Volume.
- [ ] **Logs de uso**: registrar qué usuario generó qué documentos y cuándo.
- [ ] **Pruebas automatizadas**: ninguna cobertura de tests actualmente.

---

## Notas de desarrollo importantes

1. **Modelo de IA**: Solo usar `claude-haiku-4-5-20251001`. La cuenta solo tiene modelos Claude 4.x. No usar nombres de modelos Claude 3.x.
2. **API key**: NUNCA pegar en chat. Solo en Railway → Variables.
3. **Cache-buster**: Al modificar CSS → incrementar `?v=` en `<link>` de todos los templates. Al modificar JS → incrementar `?v=` en `<script>` de `index.html`.
4. **AcroForm PDFs**: Los templates están en `plantillas/`. No modificar — son los formularios oficiales de Cámara de Comercio y DIAN.
5. **Tildes en PDFs**: `_strip_tildes()` en `pdf_filler.py` elimina tildes de todo texto antes de llenar AcroForms (evita problemas de encoding en PDFs).
6. **Capital pagado**: lógica de dos modos en `app.py` línea ~250. Modo A: sum de individuales si alguno tiene valor. Modo B: valor global distribuido proporcionalmente.

---

## Comandos útiles

```bash
# Correr localmente
cd si_sas_proyecto
python src/app.py

# Ver logs Railway
railway logs --tail

# Push y redeploy
git add src/ && git commit -m "mensaje" && git push origin main
```
