/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

export class MarketingDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        // Initialize state with stored filters if available
        const storedFilters = JSON.parse(localStorage.getItem('marketing_dashboard_filters')) || {};

        this.state = useState({
            metrics: {
                deliverability: {},
                engagement: {},
                conversion: {
                    potential_revenue: 0,
                    potential_conversions: 0,
                    total_revenue: 0,
                    total_conversions: 0,
                    conversion_rate: 0,
                    revenue_per_email: 0,
                },
                list_health: {},
                campaign_stages: { stages: [], has_stages: false },
                ab_testing: {},
            },
            filters: {
                campaign_id: parseInt(storedFilters.campaign_id) || "",
                mailing_id: parseInt(storedFilters.mailing_id) || "",
            },
            options: {
                campaigns: [],
                mailings: [],
            },
            loading: true,
        });

        onWillStart(async () => {
            await Promise.all([
                this.loadFilters(),
                this.fetchData(),
            ]);
        });
    }

    async loadFilters() {
        try {
            // Pass the current campaign_id to filter mailings
            const args = [
                this.state.filters.campaign_id || null,
                this.state.filters.mailing_id || null
            ];
            const result = await this.orm.call("marketing.dashboard.handler", "get_filter_options", args);
            this.state.options = result;
        } catch (error) {
            console.error("Error loading filters:", error);
        }
    }

    async fetchData() {
        this.state.loading = true;
        try {
            const args = [
                this.state.filters.campaign_id || null,
                this.state.filters.mailing_id || null,
            ];
            const result = await this.orm.call("marketing.dashboard.handler", "get_dashboard_data", args);
            this.state.metrics = result;
        } catch (error) {
            console.error("Error fetching dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async onFilterChange(ev) {
        const { name, value } = ev.target;
        this.state.filters[name] = value;

        if (name === 'campaign_id') {
            // When campaign changes, we must reload the mailing options
            // and reset the mailing selection as it might not belong to the new campaign
            this.state.filters.mailing_id = "";
            await this.loadFilters();
        }

        // Save filters to localStorage
        localStorage.setItem('marketing_dashboard_filters', JSON.stringify({
            campaign_id: this.state.filters.campaign_id,
            mailing_id: this.state.filters.mailing_id
        }));

        await this.fetchData();
    }

    openView(res_model, domain, context = {}) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Details",
            res_model: res_model,
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            context: context,
            target: "current",
        });
    }

    openDeliverability(type) {
        const domain = [];

        // Campaign and Mailing filters
        if (this.state.filters.campaign_id) {
            domain.push(['campaign_id', '=', parseInt(this.state.filters.campaign_id)]);
        }
        if (this.state.filters.mailing_id) {
            domain.push(['mass_mailing_id', '=', parseInt(this.state.filters.mailing_id)]);
        }

        // Status filter - must match backend logic exactly
        // Success statuses: sent, open, reply, click, bounce, delivered
        const sentStatuses = ['sent', 'open', 'reply', 'click', 'bounce', 'delivered'];

        if (type === 'sent') {
            // SENT: Show traces that were successfully sent
            domain.push(['trace_status', 'in', sentStatuses]);
        } else if (type === 'delivered') {
            // DELIVERED: Show traces that reached the recipient (excludes bounce)
            domain.push(['trace_status', 'in', ['sent', 'open', 'reply', 'click', 'delivered']]);
        } else if (type === 'bounced') {
            domain.push(['trace_status', '=', 'bounce']);
        } else if (type === 'exception') {
            // EXCEPTION: Show all traces NOT in success statuses
            // This catches any error status regardless of name
            domain.push(['trace_status', 'not in', sentStatuses]);
        } else if (type === 'total') {
            // TOTAL: Show all traces properly associated with the campaign/mailing filters
            // We don't need to push any specific status domain here as we want ALL traces
        }

        this.openView("mailing.trace", domain);
    }

    openContacts(type) {
        let domain = [];
        if (type === 'blacklisted') {
            domain.push(['is_blacklisted', '=', true]);
        } else if (type === 'new') {
            const date = new Date();
            date.setDate(date.getDate() - 30);
            domain.push(['create_date', '>=', date.toISOString().split('T')[0]]);
        } else if (type === 'active') {
            domain.push(['is_blacklisted', '=', false]);
        }
        this.openView("mailing.contact", domain);
    }

    openStage(stageId) {
        // Open campaigns in this stage
        const domain = [['stage_id', '=', stageId]];
        if (this.state.filters.campaign_id) {
            domain.push(['id', '=', parseInt(this.state.filters.campaign_id)]);
        }
        this.openView("utm.campaign", domain);
    }

    async openConversion(type) {
        const domain = [];

        // Apply filters (prioritizing mailing_id as per requirements)
        if (this.state.filters.mailing_id) {
            // We need to find the source_id of this mailing to filter orders
            const mailings = await this.orm.read("mailing.mailing", [parseInt(this.state.filters.mailing_id)], ["source_id"]);
            if (mailings && mailings.length > 0 && mailings[0].source_id) {
                domain.push(['source_id', '=', mailings[0].source_id[0]]);
            } else {
                // If the mailing has no source_id, it cannot have generated orders via standard tracking
                // Force an empty result to match backend logic
                domain.push(['id', '=', -1]);
            }
        } else if (this.state.filters.campaign_id) {
            domain.push(['campaign_id', '=', parseInt(this.state.filters.campaign_id)]);
        }

        if (type === 'potential') {
            // New Logic: 
            // 1. Draft/Sent Quotes
            // 2. Confirmed Orders NOT fully invoiced
            domain.push('|');
            domain.push('|');
            domain.push(['state', '=', 'draft']);
            domain.push(['state', '=', 'sent']);
            domain.push('&');
            domain.push(['state', '=', 'sale']);
            domain.push(['invoice_status', '!=', 'invoiced']);
        } else if (type === 'total') {
            domain.push(['state', 'in', ['sale', 'done']]);
            domain.push(['invoice_status', '=', 'invoiced']);
        }
        // 'all' or others could just not filter state

        this.openView("sale.order", domain);
    }

    openAutomation(type) {
        if (!this.state.metrics.automation.installed) {
            this.env.services.notification.add("Marketing Automation module is not installed.", {
                type: "warning",
            });
            return;
        }
        if (type === 'campaigns') {
            this.openView("marketing.campaign", [['state', '=', 'running']]);
        }
        // Participants are harder to link directly without specific context, 
        // usually linked to traces/activities.
    }

    formatNumber(value) {
        if (value === undefined || value === null) return "0";
        return value.toLocaleString();
    }

    formatCurrency(value) {
        if (value === undefined || value === null) return "$0.00";
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
    }

    formatPercentage(value) {
        if (value === undefined || value === null) return "0%";
        return parseFloat(value).toFixed(1) + "%";
    }
    getStageColor(stageName) {
        if (!stageName) return 'bg-dark-gray';
        const name = stageName.toLowerCase();
        if (name.includes('new') || name.includes('nuevo')) return 'bg-gradient-warning';
        if (name.includes('design') || name.includes('diseño')) return 'bg-gradient-primary';
        if (name.includes('schedule') || name.includes('programar') || name.includes('cola')) return 'bg-gradient-info';
        if (name.includes('sent') || name.includes('enviado')) return 'bg-gradient-success';
        if (name.includes('cancel') || name.includes('stopped')) return 'bg-gradient-danger';
        return 'bg-dark-gray';
    }

    getStageBadgeColor(stageName) {
        if (!stageName) return 'text-dark';
        const name = stageName.toLowerCase();
        if (name.includes('new') || name.includes('nuevo')) return 'text-warning';
        if (name.includes('design') || name.includes('diseño')) return 'text-blue';
        if (name.includes('schedule') || name.includes('programar') || name.includes('cola')) return 'text-info';
        if (name.includes('sent') || name.includes('enviado')) return 'text-success';
        if (name.includes('cancel') || name.includes('stopped')) return 'text-danger';
        return 'text-dark';
    }
}

MarketingDashboard.template = "dashboard_metricas_mail.MarketingDashboard";

registry.category("actions").add("dashboard_metricas_mail.dashboard", MarketingDashboard);
