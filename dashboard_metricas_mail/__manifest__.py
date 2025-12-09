{
    'name': 'Email Marketing Dashboard',
    'version': '1.0',
    'author': 'Pedro Pereira Vaz',
    'website': 'https://wavext.io',
    'category': 'Marketing/Email Marketing',
    'summary': 'Dashboard para metricas de Email Marketing',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mass_mailing',
        'web',
        'utm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/marketing_dashboard_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dashboard_metricas_mail/static/src/dashboard/**/*',
        ],
    },
    'description': """
Dashboard de Email Marketing
============================

Este módulo proporciona un tablero visual interactivo para monitorear el rendimiento de su Email Marketing en Odoo 18.

Características Principales:
----------------------------
*   **Vista Unificada de Métricas:** Consolida métricas críticas de correo en una sola pantalla.
*   **Entregabilidad y Calidad:** Rastrea estados de Enviado, Entregado, Rebotado y Excepciones con capacidad de desglose.
*   **Analíticas de Interacción:** Monitorea Tasas de Apertura, Clics (CTR), Click-To-Open (CTOR) y Respuestas.
*   **Conversión:** Visualiza Ingresos generados y Cotizaciones vinculadas a los envíos (requiere módulo de ventas).
*   **Salud de la Lista:** Visualiza Contactos Activos vs. Lista Negra y tendencia de nuevos suscriptores (últimos 30 días).
*   **Etapas de Campaña:** Visualiza la distribución de sus campañas a través de sus etapas (Nuevo, Enviando, Hecho).
*   **Filtrado Inteligente:**
    *   **Filtro de Campaña:** Seleccione una campaña para ver datos específicos.
    *   **Filtro de Envío Dependiente:** Al seleccionar una campaña, la lista de envíos se filtra automáticamente.
*   **Desglose Interactivo:** Al hacer clic en las tarjetas de métricas o listas de etapas, se abren vistas detalladas de Rastros, Contactos o Campañas.
    """,
    'images': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
