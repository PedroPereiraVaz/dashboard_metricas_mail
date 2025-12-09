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
    'description': '''
        Dashboard de Métricas de Email Marketing
        ========================================
        
        Este módulo profesional proporciona un tablero visual centralizado para
        monitorear y analizar el rendimiento de sus campañas de Email Marketing
        en Odoo 18.
        
        🎯 Valor que Aporta
        -------------------
        Odoo nativo dispersa las métricas de email marketing en múltiples vistas
        y reportes. Este módulo consolida toda la información crítica (entregabilidad,
        interacción, conversión y salud de listas) en una única pantalla interactiva,
        permitiendo decisiones rápidas basadas en datos reales.
        
        ✨ Características Principales
        ------------------------------
        • Vista Unificada: Monitoreo en tiempo real de Enviados, Entregados, Rebotes y Respuestas
        • Analíticas de Engagement: Cálculo preciso de Tasa de Apertura, CTR y CTOR
        • Tracking de Conversión: Visualización de Ingresos y Cotizaciones generadas
        • Salud de Listas: Análisis de contactos Activos vs. Lista Negra y crecimiento reciente
        • Etapas de Campaña: Visualización del ciclo de vida de sus campañas
        • Filtros Inteligentes: Filtrado dependiente (Campaña -> Envíos) para aislar datos
        
        🔧 Detalles Técnicos
        --------------------
        El módulo utiliza tecnologías estándar de Odoo 18:
        
        • Framework Owl: Interfaz reactiva y moderna
        • Arquitectura: Cliente-Servidor optimizado para métricas
        • Compatibilidad: Funciona en Community y Enterprise sin dependencias extra
        
        📊 Casos de Uso
        ---------------
        Ideal para equipos de marketing que:
        - Necesitan reportes rápidos de rendimiento de campañas
        - Quieren entender por qué rebotan sus correos (Drill-down)
        - Buscan correlacionar envíos con ventas reales
        - Gestionan múltiples campañas y necesitan filtrar ágilmente
        
        🚀 Instalación y Uso
        --------------------
        1. Instale el módulo "Email Marketing Dashboard"
        2. Vaya a Email Marketing > Informes > Dashboard de Métricas
        3. Use los filtros superiores para explorar sus datos
        
        No requiere configuración adicional. Se integra automáticamente con
        los datos de Mass Mailing existentes.
        
        📝 Notas Técnicas
        -----------------
        Compatible con Odoo 18 Community y Enterprise.
        
    ''',
    'images': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
