# 📘 Generador de Dossiers Legislativos

Herramienta de escritorio desarrollada en **Python + Tkinter** para la **consulta, revisión, selección y generación automatizada de dossiers legislativos** en formato **Word**, a partir de información estructurada (JSON / API).

Diseñada para consultoría legislativa, análisis político y seguimiento parlamentario.

---

## 🎯 Objetivo del sistema

Permitir a un usuario:

1. Autenticarse en la plataforma
2. Seleccionar un **rango de fechas**
3. Consultar información legislativa por **Cámara**
4. Revisar los **apartados legislativos**
5. **Seleccionar individualmente** los elementos relevantes
6. Generar un **Dossier Legislativo en Word**, usando una **plantilla corporativa**

---

## 🧩 Funcionalidades principales

### 🔐 Autenticación
- Pantalla inicial de **login**
- Autenticación local (mock) mediante archivo `users.json`
- Contraseñas hasheadas (SHA-256 + salt)
- Arquitectura lista para migrar a **API / SSO**

---

### 📅 Consulta por rango de fechas
- Selección de fecha **Desde / Hasta**
- Validación de rango
- Preparado para consumir:
  - Mock local (JSON)
  - API REST (futuro)

---

### 🏛️ Organización legislativa
Los resultados se agrupan automáticamente por:

- **Cámara**
  - Senado
  - Diputados
- **Apartado legislativo**
  - Comunicaciones
  - Dictámenes
  - Iniciativas
  - Proposiciones
  - Acuerdos Parlamentarios
  - Minutas

Cada apartado puede contener múltiples elementos.

---

### ☑️ Selección granular de contenidos
- Cada **item individual** puede marcarse o desmarcarse
- El checkbox **no es por apartado**, sino por elemento
- Solo los elementos seleccionados se exportan al Word

---

### 📄 Generación de Dossier en Word
- Exportación a **.docx**
- Uso de **plantilla corporativa**
- Inserción automática de:
  - Rango de fechas
  - Contenidos seleccionados
  - Separación por Cámara y Apartado
- Soporte para:
  - Tokens dentro de encabezados
  - Tokens dentro de tablas
  - Tokens dentro de **TextBox del header** (vía reemplazo XML)

---

### 🖼️ Branding corporativo
- Banner institucional en la pantalla de login
- Plantilla Word con imagen corporativa y encabezados fijos
- Fácil personalización por cliente

---

## 🗂️ Estructura del proyecto

```text
Generador_de_Dossiers_App/
│
├── src/
│   ├── app.py                     # Orquestador principal + login + navegación
│   ├── main.py                    # Entry point
│   │
│   ├── config/
│   │   └── settings.py            # Configuración general
│   │
│   ├── domain/
│   │   └── models.py              # Modelos de dominio y ViewModel
│   │
│   ├── services/
│   │   ├── auth_service.py        # Autenticación (file / api)
│   │   ├── dossier_repository.py  # Fuente de datos (file / api)
│   │   ├── dossier_mapper.py      # Normalización JSON → UI
│   │   └── dossier_exporter_word_template.py
│   │                                # Exportación Word con plantilla
│   │
│   └── ui/
│       ├── styles.py              # Estilos Tkinter
│       └── views/
│           ├── login_view.py
│           ├── parametros_view.py
│           └── resultados_view.py
│
├── data/
│   ├── mock/
│   │   ├── JSON_EJEMPLO_Dossier.json
│   │   └── users.json
│   │
│   └── assets/
│       └── images/
│           └── safie_banner.jpg
│
├── templates/
│   └── Plantilla_Dossier_Legislativo.docx
│
└── README.md
