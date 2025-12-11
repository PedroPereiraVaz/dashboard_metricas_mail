# -*- coding: utf-8 -*-
{
    'name': 'Email Marketing Dashboard',
    'version': '1.0',
    'author': 'Pedro Pereira Vaz',
    'website': 'https://wavext.io',
    'category': 'Marketing/Email Marketing',
    'summary': 'Dashboard para metricas de Email Marketing',
    'description': '''
        Dashboard de Métricas de Email Marketing
        ========================================
        
        Este módulo profesional proporciona un tablero visual centralizado para
        monitorear y analizar el rendimiento de sus campañas de Email Marketing
        en Odoo 18.
        
        🎯 Valor que Aporta
        -------------------
        Consolide toda la información crítica (entregabilidad, interacción, conversión
        y salud de listas) en una única pantalla interactiva.
        
        ✨ Nuevas Características & Mejoras
        -----------------------------------
        • 📊 Conversión Avanzada: Desglose de "Ingresos Facturados" vs "Potenciales" y conteo de conversiones.
        • 🏆 Top Charts (Rankings):
            - Top 5 Campañas (por ingresos)
            - Top 5 Envíos (por ingresos)
            - Enlaces más clicados (con acceso directo a stats)
        • ℹ️ Ayudas Visuales: Tooltips explicativos (i) en cada métrica y efectos visuales Hover.
        • 🌍 Internacionalización: Traducción completa al Español (es_ES).
        
        🚀 Funcionalidades Clave
        ------------------------
        • Vista Unificada: Monitoreo en tiempo real de Enviados, Entregados, Rebotes y Respuestas.
        • Analíticas de Engagement: Tasa de Apertura, CTR y CTOR interactivos.
        • Salud de Listas: Análisis de contactos Activos vs. Lista Negra.
        • Etapas de Campaña: Visualización del ciclo de vida de sus campañas.
        • Filtros Inteligentes: Filtrado dependiente (Campaña -> Envíos) y PERSISTENTE.
        
        🔧 Detalles Técnicos
        --------------------
        • Framework Owl: Interfaz reactiva y moderna.
        • Arquitectura optimizada para grandes volúmenes de datos.
        • Compatible con Odoo 18 Community y Enterprise.
        
        🚀 Instalación y Uso
        --------------------
        1. Instale el módulo "Email Marketing Dashboard".
        2. Vaya a Email Marketing > Informes > Dashboard de Métricas.
        
        No requiere configuración adicional. Se integra automáticamente.
    ''',
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
    'images': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
