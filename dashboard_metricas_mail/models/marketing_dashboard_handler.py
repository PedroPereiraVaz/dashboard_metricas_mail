from odoo import models, fields, api
from datetime import timedelta

class MarketingDashboardHandler(models.TransientModel):
    _name = 'marketing.dashboard.handler'
    _description = 'Marketing Dashboard Handler'

    @api.model
    def get_dashboard_data(self, campaign_id=None, mailing_id=None):
        """
        Main method to fetch all dashboard data.
        """
        domain = []
        
        # Filter by Campaign
        if campaign_id:
            # mass_mailing.mailing has 'campaign_id' field if mass_mailing is installed
            # Check if field exists to avoid errors
            if 'campaign_id' in self.env['mailing.mailing']._fields:
                domain.append(('campaign_id', '=', int(campaign_id)))
        
        # Filter by Mailing
        if mailing_id:
            domain.append(('id', '=', int(mailing_id)))

        return {
            'deliverability': self.get_deliverability_metrics(domain),
            'engagement': self.get_engagement_metrics(domain),
            'conversion': self.get_conversion_metrics(domain),
            'list_health': self.get_list_health_metrics(), # List health is global
            'campaign_stages': self.get_campaign_stages(campaign_id),
            'top_links': self.get_top_links(domain),
            'ab_testing': self.get_ab_testing_metrics(domain),
        }

    # ... existing methods ...

    @api.model
    def get_campaign_stages(self, campaign_id=None):
        """
        Get campaign counts per stage (if utm.stage exists).
        Replaces automation metrics.
        """
        if 'utm.stage' not in self.env or 'stage_id' not in self.env['utm.campaign']._fields:
            return {
                'stages': [],
                'has_stages': False,
            }
        
        # Build domain for campaigns
        campaign_domain = []
        if campaign_id:
            campaign_domain.append(('id', '=', int(campaign_id)))
            
        # Get stages
        stages = self.env['utm.stage'].search_read([], ['id', 'name'], order='sequence')
        
        stage_data = []
        for stage in stages:
            # Count campaigns in this stage
            # We filter by stage AND specific campaign (if selected)
            count = self.env['utm.campaign'].search_count(campaign_domain + [('stage_id', '=', stage['id'])])
            stage_data.append({
                'id': stage['id'],
                'name': stage['name'],
                'count': count
            })
            
        return {
            'stages': stage_data,
            'has_stages': True,
            'has_stages': True,
        }

    @api.model
    def get_top_links(self, domain):
        """
        Get top 5 clicked links.
        """
        # Ensure we have mailings context
        mailings = self.env['mailing.mailing'].search(domain)
        if not mailings:
             return []

        # Filter clicks by these mailings
        # 'link.tracker.click' has 'mass_mailing_id'
        click_domain = [('mass_mailing_id', 'in', mailings.ids)]
        
        # Read Group to count clicks per link
        # 'link_id' is the Many2one to link.tracker
        groups = self.env['link.tracker.click'].read_group(
            click_domain,
            ['link_id'],
            ['link_id'],
            orderby='link_id_count desc',
            limit=5
        )
        
        links_data = []
        for g in groups:
            if not g['link_id']:
                continue
                
            # g['link_id'] is usually (id, name) tuple in read_group for m2o
            link_id = g['link_id'][0]
            link_name = g['link_id'][1] or "Unknown Link"
            count = g['link_id_count']
            
            # Fetch full link object to get title and label
            link = self.env['link.tracker'].browse(link_id)
            # Display both Title and Label if available
            parts = []
            if link.title:
                parts.append(link.title)
            if link.label:
                parts.append(link.label)
            
            display_name = " - ".join(parts) if parts else link_name
            
            # Use the Global click count from the link object to match user expectation ("various")
            # The 'count' from read_group is filtered by mailing, which might be why they see 1.
            # Showing global popularity is often more useful for "Top Links".
            total_clicks = link.count 
            
            links_data.append({
                'id': link_id,
                'name': display_name,
                'url': link.url, # storing URL separately for the href
                'short_url': link.short_url, # For the + stats redirection
                'count': total_clicks
            })
            
        return links_data

    @api.model
    def get_filter_options(self, campaign_id=None, mailing_id=None):
        """
        Returns available campaigns and mailings for filters.
        """
        # Usage of sudo() to ensure users can see the options even if they have restrictive rules
        # (Dashboard usually implies read access to high level metrics)
        
        campaigns = []
        # Prioritize utm.campaign as it's used by mass_mailing
        if 'utm.campaign' in self.env:
             campaigns = self.env['utm.campaign'].sudo().search_read([], ['id', 'name'])
        elif 'marketing.campaign' in self.env:
             campaigns = self.env['marketing.campaign'].sudo().search_read([], ['id', 'name'])

        mailing_domain = [('state', 'in', ['done', 'sending'])]
        
        if campaign_id:
            # Verify field exists before filtering
            if 'campaign_id' in self.env['mailing.mailing']._fields:
                try:
                    mailing_domain.append(('campaign_id', '=', int(campaign_id)))
                except (ValueError, TypeError):
                    pass # Ignore invalid campaign_id
        
        # Fetch default recent mailings
        mailings = self.env['mailing.mailing'].sudo().search_read(mailing_domain, ['id', 'subject', 'sent_date'], order='sent_date desc', limit=50)
        
        # Ensure the selected mailing_id is in the list (if it exists)
        if mailing_id:
            try:
                m_id = int(mailing_id)
                # Check if the selected mailing is already in the list
                found = False
                for m in mailings:
                    if m['id'] == m_id:
                        found = True
                        break
                
                if not found:
                     # Fetch specifically this one
                     specific_mailing = self.env['mailing.mailing'].sudo().search_read([('id', '=', m_id)], ['id', 'subject', 'sent_date'], limit=1)
                     if specific_mailing:
                         mailings.extend(specific_mailing)
            except (ValueError, TypeError):
                pass

        return {
            'campaigns': campaigns,
            'mailings': [{'id': m['id'], 'name': f"{m['subject']} ({m['sent_date'] or 'No Date'})"} for m in mailings],
        }

    @api.model
    def get_deliverability_metrics(self, mailing_domain):
        """
        Calculate deliverability metrics directly from mailing.trace.
        Uses the same approach as the JavaScript frontend for consistency.
        """
        Trace = self.env['mailing.trace']
        
        # Build trace domain based on mailing filters
        trace_domain = []
        
        # If we have mailing filters, first get the mailing IDs
        if mailing_domain:
            mailings = self.env['mailing.mailing'].search(mailing_domain)
            if mailings:
                trace_domain.append(('mass_mailing_id', 'in', mailings.ids))
            else:
                # No mailings match the filter, return 0s
                return {
                    'sent': 0, 'delivered': 0, 'bounced': 0, 'exception': 0,
                    'delivery_rate': 0, 'bounce_rate': 0, 'exception_rate': 0, 'sent_rate': 0
                }
        
        # Determine the status field (version dependent)
        status_field = 'trace_status' if 'trace_status' in Trace._fields else 'state'
        
        # SENT: Traces that were successfully sent (not error/cancel/failure)
        # Success statuses: sent, open, reply, click, bounce, delivered
        sent_statuses = ['sent', 'open', 'reply', 'click', 'bounce', 'delivered']
        sent = Trace.search_count(trace_domain + [(status_field, 'in', sent_statuses)]) if trace_domain else Trace.search_count([(status_field, 'in', sent_statuses)])
        
        # DELIVERED: Traces that reached recipient (excludes bounce)
        delivered_statuses = ['sent', 'open', 'reply', 'click', 'delivered']
        delivered = Trace.search_count(trace_domain + [(status_field, 'in', delivered_statuses)]) if trace_domain else Trace.search_count([(status_field, 'in', delivered_statuses)])
        
        # BOUNCED: Traces that bounced
        bounced = Trace.search_count(trace_domain + [(status_field, '=', 'bounce')]) if trace_domain else Trace.search_count([(status_field, '=', 'bounce')])
        
        # EXCEPTION: All traces that are NOT in sent statuses
        # This catches any error status regardless of name (error, exception, failure, cancel, etc.)
        exception = Trace.search_count(trace_domain + [(status_field, 'not in', sent_statuses)]) if trace_domain else Trace.search_count([(status_field, 'not in', sent_statuses)])
        
        # Calculate rates based on total traces (sent + exception = total attempts)
        total_attempts = sent + exception
        
        return {
            'sent': sent,
            'delivered': delivered,
            'bounced': bounced,
            'exception': exception,
            'total': Trace.search_count(trace_domain) if trace_domain else Trace.search_count([]),
            'delivery_rate': (delivered / total_attempts * 100) if total_attempts else 0,
            'bounce_rate': (bounced / total_attempts * 100) if total_attempts else 0,
            'exception_rate': (exception / total_attempts * 100) if total_attempts else 0,
            'sent_rate': (sent / total_attempts * 100) if total_attempts else 0,
        }

    @api.model
    def get_engagement_metrics(self, mailing_domain):
        """
        Calculate engagement metrics from mailing.trace using datetime fields.
        """
        Trace = self.env['mailing.trace']
        
        # Build trace domain based on mailing filters
        trace_domain = []
        if mailing_domain:
            mailings = self.env['mailing.mailing'].search(mailing_domain)
            if mailings:
                trace_domain = [('mass_mailing_id', 'in', mailings.ids)]
            else:
                 return {
                    'open_rate': 0, 'click_rate': 0, 'reply_rate': 0, 'ctor': 0,
                    'total_opens': 0, 'total_clicks': 0, 'total_replies': 0,
                }
        
        # Determine the status field for delivered count
        status_field = 'trace_status' if 'trace_status' in Trace._fields else 'state'
        
        # Total delivered (base for rates) - all successful traces
        delivered_statuses = ['sent', 'open', 'reply', 'click', 'delivered']
        if trace_domain:
            delivered = Trace.search_count(trace_domain + [(status_field, 'in', delivered_statuses)])
        else:
            delivered = Trace.search_count([(status_field, 'in', delivered_statuses)])
        
        # OPENED: Count traces where open_datetime IS NOT NULL
        if trace_domain:
            opened = Trace.search_count(trace_domain + [('open_datetime', '!=', False)])
        else:
            opened = Trace.search_count([('open_datetime', '!=', False)])
        
        # CLICKED: Count traces where links_click_datetime IS NOT NULL
        if trace_domain:
            clicked = Trace.search_count(trace_domain + [('links_click_datetime', '!=', False)])
        else:
            clicked = Trace.search_count([('links_click_datetime', '!=', False)])
        
        # REPLIED: Count traces where reply_datetime IS NOT NULL
        if trace_domain:
            replied = Trace.search_count(trace_domain + [('reply_datetime', '!=', False)])
        else:
            replied = Trace.search_count([('reply_datetime', '!=', False)])
        
        # Calculate rates
        open_rate = (opened / delivered * 100) if delivered else 0
        click_rate = (clicked / delivered * 100) if delivered else 0
        reply_rate = (replied / delivered * 100) if delivered else 0
        ctor = (clicked / opened * 100) if opened else 0
        
        return {
            'open_rate': open_rate,
            'click_rate': click_rate,
            'reply_rate': reply_rate,
            'ctor': ctor,
            'total_opens': opened,
            'total_clicks': clicked,
            'total_replies': replied,
        }

    @api.model
    def get_conversion_metrics(self, domain):
        """
        Calculate detailed conversion metrics from linked sale.order records.
        """
        # Ensure we are finding mailings first to establish context
        mailings = self.env['mailing.mailing'].search(domain)
        
        if not mailings:
             return {
                'potential_revenue': 0,
                'potential_conversions': 0,
                'total_revenue': 0,
                'total_conversions': 0,
                'conversion_rate': 0,
                'revenue_per_email': 0,
            }

        # Build domain for sale.order
        # We need to find orders linked to these mailings
        # Since 'mass_mailing_id' is not available on sale.order, we use the UTM Source.
        # Each mailing has a defined source_id that is passed to the order via tracking.
        
        sources = mailings.mapped('source_id')
        sale_domain = [('source_id', 'in', sources.ids)] if sources else [('id', '=', 0)] # Fallback if no sources
        
        Orders = self.env['sale.order']
        
        # POTENTIAL: 
        # 1. Draft/Sent Quotations (Presupuestos)
        # 2. Confirmed Orders NOT fully invoiced (state='sale' AND invoice_status != 'invoiced')
        # This captures all pipeline revenue: Quotes, "To Invoice", "Upselling", "Nothing to Invoice" (e.g. waiting for delivery)
        potential_domain = sale_domain + ['|', '|', ('state', '=', 'draft'), ('state', '=', 'sent'), '&', ('state', '=', 'sale'), ('invoice_status', '!=', 'invoiced')]
        potential_orders = Orders.search(potential_domain)
        potential_revenue = sum(potential_orders.mapped('amount_total'))
        potential_conversions = len(potential_orders)
        
        # CONSOLIDATED (Total): State in 'sale', 'done' AND invoice_status = 'invoiced'
        # This ensures we only show fully invoiced revenue as requested
        total_domain = sale_domain + [('state', 'in', ['sale', 'done']), ('invoice_status', '=', 'invoiced')]
        total_orders = Orders.search(total_domain)
        total_revenue = sum(total_orders.mapped('amount_total'))
        total_conversions = len(total_orders)
        
        total_sent = sum(mailings.mapped('sent'))
        
        return {
            'potential_revenue': potential_revenue,
            'potential_conversions': potential_conversions,
            'total_revenue': total_revenue, # Now using amount_total (with tax)
            'total_conversions': total_conversions,
            'conversion_rate': (total_conversions / total_sent * 100) if total_sent else 0,
            'revenue_per_email': (total_revenue / total_sent) if total_sent else 0,
        }

    @api.model
    def get_list_health_metrics(self):
        # List health is usually global
        contacts = self.env['mailing.contact']
        total_contacts = contacts.search_count([])
        blacklisted = contacts.search_count([('is_blacklisted', '=', True)])
        
        active = total_contacts - blacklisted
        
        last_30_days = fields.Datetime.now() - timedelta(days=30)
        new_contacts = contacts.search_count([('create_date', '>=', last_30_days)])
        
        return {
            'total_contacts': total_contacts,
            'active_contacts': active,
            'blacklisted': blacklisted,
            'new_contacts_30d': new_contacts,
            'inactive_ratio': (blacklisted / total_contacts * 100) if total_contacts else 0,
        }



    @api.model
    def get_ab_testing_metrics(self, domain):
        # Filter for mailings that are part of AB test
        if 'ab_testing_enabled' not in self.env['mailing.mailing']._fields:
             return {'ab_test_count': 0}

        ab_mailings = self.env['mailing.mailing'].search(domain + [('ab_testing_enabled', '=', True)])
        
        return {
            'ab_test_count': len(ab_mailings),
        }
