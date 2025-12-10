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
        }

    @api.model
    def get_filter_options(self, campaign_id=None):
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

        mailings = self.env['mailing.mailing'].sudo().search_read(mailing_domain, ['id', 'subject', 'sent_date'], order='sent_date desc', limit=50)
        
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
        # Requires mass_mailing_sale or similar for revenue
        
        # Ensure we are finding mailings first
        mailings = self.env['mailing.mailing'].search(domain)
        
        if not mailings:
             return {
                'revenue': 0,
                'revenue_per_email': 0,
                'conversions': 0,
                'conversion_rate': 0,
            }

        revenue = 0
        conversions = 0
        
        if 'sale_invoiced_amount' in self.env['mailing.mailing']._fields:
            for mailing in mailings:
                revenue += mailing.sale_invoiced_amount
                conversions += mailing.sale_quotation_count
        
        total_sent = sum(mailings.mapped('sent'))
        
        return {
            'revenue': revenue,
            'revenue_per_email': (revenue / total_sent) if total_sent else 0,
            'conversions': conversions,
            'conversion_rate': (conversions / total_sent * 100) if total_sent else 0,
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
