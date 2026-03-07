"""Demo data seeder — populates the database with realistic sample data."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from herald.database import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _hours_ago(hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def is_seeded() -> bool:
    """Check if the database already has seed data."""
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM customers").fetchone()
    return row["cnt"] > 0


def seed_all() -> None:
    """Seed the database with demo data. Only runs if database is empty."""
    if is_seeded():
        return

    conn = get_connection()

    # ==================== KNOWLEDGE BASE ====================
    knowledge_items = [
        # Product
        ("Getting Started with Herald", "Herald is a customer operations platform that unifies chatbots, support tools, and analytics. To get started, create your account, configure your team, and connect your communication channels. The dashboard gives you a real-time overview of all customer interactions.", "product"),
        ("Team Management", "Manage your support team from the Settings page. You can invite team members, assign roles (Admin, Agent, Viewer), set up round-robin ticket assignment, and configure business hours for each team member.", "product"),
        ("Automation Rules", "Herald supports automation rules that trigger on specific events. You can auto-assign tickets based on category, send follow-up emails after resolution, escalate tickets that have been open for more than 24 hours, and route conversations to specialized agents based on topic.", "product"),
        # Billing
        ("Pricing Plans", "Herald offers four plans: Free (up to 100 conversations/month, 1 agent), Starter ($29/mo, 1000 conversations, 3 agents), Pro ($99/mo, unlimited conversations, 10 agents, analytics), Enterprise (custom pricing, unlimited everything, dedicated support, SLA guarantees).", "billing"),
        ("Billing and Invoices", "Invoices are generated on the 1st of each month. You can view and download invoices from Settings > Billing. We accept all major credit cards and offer annual billing with a 20% discount. For Enterprise plans, we also support wire transfer and purchase orders.", "billing"),
        ("Refund Policy", "We offer a 30-day money-back guarantee on all paid plans. If you're not satisfied, contact support for a full refund. Partial month refunds are calculated pro-rata. Refunds are processed within 5-7 business days.", "billing"),
        # Technical
        ("API Documentation", "The Herald API uses REST with JSON. Authenticate using Bearer tokens from Settings > API Keys. Rate limits: Free (100 req/hr), Starter (1000 req/hr), Pro (5000 req/hr), Enterprise (unlimited). All endpoints return standard HTTP status codes.", "technical"),
        ("Webhook Integration", "Configure webhooks from Settings > Integrations. Supported events: conversation.created, conversation.resolved, ticket.created, ticket.updated, customer.churn_risk_changed. Webhooks include HMAC signatures for verification.", "technical"),
        ("SDK Installation", "Install the Herald SDK: npm install @herald/sdk (JavaScript), pip install herald-sdk (Python), or include our CDN script tag. The SDK handles authentication, real-time messaging, and event tracking automatically.", "technical"),
        # Onboarding
        ("Quick Start Guide", "Step 1: Create your Herald account. Step 2: Add your first team member. Step 3: Configure your chatbot greeting message. Step 4: Install the Herald widget on your website. Step 5: Send a test message to verify everything works.", "onboarding"),
        ("Widget Customization", "Customize the Herald chat widget to match your brand. You can change colors, position (bottom-left, bottom-right), greeting message, offline message, and avatar. Access customization from Settings > Widget. Changes deploy instantly.", "onboarding"),
        ("Importing Customer Data", "Import existing customer data via CSV upload or API. Supported fields: name, email, company, plan, signup_date. Duplicates are detected by email address. You can map custom fields during import.", "onboarding"),
        # FAQ
        ("How do I reset my password?", "Click 'Forgot Password' on the login page, enter your email, and follow the link in the reset email. The link expires after 24 hours. If you don't receive the email, check your spam folder or contact support.", "faq"),
        ("Can I export my data?", "Yes! Go to Settings > Data Export. You can export conversations, customer data, tickets, and analytics reports in CSV or JSON format. Enterprise plans also support automated scheduled exports via API.", "faq"),
        ("What browsers are supported?", "Herald supports Chrome 90+, Firefox 88+, Safari 14+, and Edge 90+. The mobile experience is fully responsive. We also offer native iOS and Android SDKs for building mobile support experiences.", "faq"),
    ]

    for title, content, category in knowledge_items:
        item_id = uuid4().hex
        now = _now()
        conn.execute(
            "INSERT INTO knowledge_items (id, title, content, category, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, title, content, category, now, now),
        )

    # ==================== CUSTOMERS ====================
    customers = [
        ("cust_01", "Sarah Chen", "sarah.chen@acmecorp.com", "Acme Corp", "enterprise", 92.0, _days_ago(180), _hours_ago(2), "low"),
        ("cust_02", "Marcus Williams", "marcus@startuplab.io", "StartupLab", "pro", 78.0, _days_ago(90), _hours_ago(12), "low"),
        ("cust_03", "Elena Rodriguez", "elena.r@designhub.co", "DesignHub", "starter", 45.0, _days_ago(60), _days_ago(15), "medium"),
        ("cust_04", "James O'Brien", "james@techforge.dev", "TechForge", "pro", 31.0, _days_ago(120), _days_ago(25), "high"),
        ("cust_05", "Priya Patel", "priya@cloudnine.ai", "CloudNine AI", "enterprise", 88.0, _days_ago(200), _hours_ago(5), "low"),
        ("cust_06", "Tom Nakamura", "tom.n@freelance.me", None, "free", 55.0, _days_ago(30), _days_ago(8), "medium"),
        ("cust_07", "Lisa Andersson", "lisa@nordictech.se", "NordicTech", "starter", 25.0, _days_ago(45), _days_ago(32), "high"),
        ("cust_08", "David Kim", "david.kim@megasoft.com", "MegaSoft", "enterprise", 95.0, _days_ago(365), _hours_ago(1), "low"),
    ]

    for cid, name, email, company, plan, health, signup, last_active, risk in customers:
        conn.execute(
            """INSERT INTO customers (id, name, email, company, plan, health_score, signup_date, last_active, churn_risk, total_conversations, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (cid, name, email, company, plan, health, signup, last_active, risk, _now()),
        )

    # ==================== CONVERSATIONS + MESSAGES ====================
    conversations_data = [
        # Active conversations
        {
            "id": "conv_01", "customer_id": "cust_01", "channel": "chat", "status": "active",
            "sentiment_score": 0.6, "subject": "API rate limiting question",
            "assigned_to": "Agent Smith", "created_at": _hours_ago(3),
            "messages": [
                ("customer", "Hi, I'm trying to understand the rate limits for our Enterprise plan. We're planning to scale up our API usage significantly.", _hours_ago(3)),
                ("bot", "Great question! On the Enterprise plan, you have unlimited API requests. There are no rate limits for Enterprise customers, so you can scale freely.", _hours_ago(3)),
                ("customer", "That's perfect, thank you! One more thing — do you support batch API calls?", _hours_ago(2)),
                ("bot", "Yes, we support batch API calls! You can send up to 100 operations in a single batch request. Check our API docs at /docs/api/batch for the full specification.", _hours_ago(2)),
            ],
        },
        {
            "id": "conv_02", "customer_id": "cust_03", "channel": "chat", "status": "active",
            "sentiment_score": -0.4, "subject": "Widget not loading",
            "assigned_to": "Agent Jones", "created_at": _hours_ago(6),
            "messages": [
                ("customer", "The chat widget on our website stopped loading after our last deployment. This is frustrating because customers can't reach us.", _hours_ago(6)),
                ("agent", "I'm sorry to hear that, Elena. Can you share your website URL and the Herald widget code you're using? I'll help debug this.", _hours_ago(5)),
                ("customer", "Sure, it's designhub.co. We're using the standard script tag from the dashboard.", _hours_ago(5)),
                ("agent", "I found the issue — your Content Security Policy is blocking our CDN. You need to add 'cdn.herald.io' to your script-src directive.", _hours_ago(4)),
                ("customer", "Let me try that. I'll get back to you.", _hours_ago(4)),
            ],
        },
        {
            "id": "conv_03", "customer_id": "cust_04", "channel": "email", "status": "escalated",
            "sentiment_score": -0.7, "subject": "Repeated billing errors",
            "assigned_to": "Agent Smith", "created_at": _days_ago(3),
            "messages": [
                ("customer", "I've been charged twice this month for my Pro plan. This is the third time this has happened and I'm really angry about it.", _days_ago(3)),
                ("agent", "I sincerely apologize for the billing error, James. I can see the duplicate charge and I'm processing a refund right now.", _days_ago(3)),
                ("customer", "This is unacceptable. I've wasted hours dealing with billing issues. I'm considering canceling.", _days_ago(2)),
                ("agent", "I completely understand your frustration. I've escalated this to our billing team lead and we're investigating the root cause. As compensation, I'd like to offer you a free month.", _days_ago(2)),
            ],
        },
        # Resolved conversations
        {
            "id": "conv_04", "customer_id": "cust_02", "channel": "chat", "status": "resolved",
            "sentiment_score": 0.8, "satisfaction": 5, "subject": "Help with webhook setup",
            "assigned_to": "Agent Brown", "created_at": _days_ago(5), "resolved_at": _days_ago(4),
            "messages": [
                ("customer", "I need help setting up webhooks for ticket events. Where do I configure this?", _days_ago(5)),
                ("bot", "You can configure webhooks from Settings > Integrations in your Herald dashboard. We support events like ticket.created, ticket.updated, and conversation.resolved.", _days_ago(5)),
                ("customer", "Found it! That was really helpful, thanks!", _days_ago(4)),
                ("bot", "You're welcome! Let me know if you need help with the webhook signature verification too.", _days_ago(4)),
            ],
        },
        {
            "id": "conv_05", "customer_id": "cust_05", "channel": "chat", "status": "resolved",
            "sentiment_score": 0.9, "satisfaction": 5, "subject": "Team member invitation",
            "assigned_to": None, "created_at": _days_ago(7), "resolved_at": _days_ago(7),
            "messages": [
                ("customer", "How do I invite new team members to our Herald account?", _days_ago(7)),
                ("bot", "To invite team members, go to Settings > Team Management. Click 'Invite Member', enter their email, and select their role (Admin, Agent, or Viewer). They'll receive an invitation email automatically.", _days_ago(7)),
                ("customer", "Perfect, that's exactly what I needed. Great product!", _days_ago(7)),
            ],
        },
        {
            "id": "conv_06", "customer_id": "cust_06", "channel": "chat", "status": "resolved",
            "sentiment_score": 0.2, "satisfaction": 3, "subject": "Free plan limitations",
            "assigned_to": "Agent Jones", "created_at": _days_ago(10), "resolved_at": _days_ago(9),
            "messages": [
                ("customer", "I've hit the 100 conversation limit on the free plan. What are my options?", _days_ago(10)),
                ("agent", "Hi Tom! On the free plan, the limit resets at the start of each month. If you need more conversations, our Starter plan at $29/month gives you 1000 conversations and 3 agent seats.", _days_ago(10)),
                ("customer", "That's a big jump in price for a solo freelancer. Any middle ground?", _days_ago(9)),
                ("agent", "I understand the concern. We do offer a 14-day free trial of the Starter plan so you can evaluate if the extra capacity is worth it. Would you like me to set that up?", _days_ago(9)),
                ("customer", "Sure, let's try the trial. Thanks.", _days_ago(9)),
            ],
        },
        {
            "id": "conv_07", "customer_id": "cust_08", "channel": "chat", "status": "resolved",
            "sentiment_score": 0.7, "satisfaction": 4, "subject": "Data export for compliance",
            "assigned_to": "Agent Smith", "created_at": _days_ago(14), "resolved_at": _days_ago(13),
            "messages": [
                ("customer", "We need to export all our conversation data for a compliance audit. What's the best way to do this?", _days_ago(14)),
                ("agent", "As an Enterprise customer, you have access to our full data export API. You can export conversations, customer data, and tickets in JSON format. I'd recommend using the /api/export endpoint with date range filters.", _days_ago(14)),
                ("customer", "Excellent, and can we schedule automated exports?", _days_ago(13)),
                ("agent", "Absolutely! Enterprise plans support scheduled exports via API. You can set up a cron job that calls our export endpoint daily. Here's a sample curl command to get you started.", _days_ago(13)),
                ("customer", "This is great, thank you for the quick help!", _days_ago(13)),
            ],
        },
        # Waiting conversations
        {
            "id": "conv_08", "customer_id": "cust_07", "channel": "email", "status": "waiting",
            "sentiment_score": -0.3, "subject": "Account access issue",
            "assigned_to": "Agent Brown", "created_at": _days_ago(2),
            "messages": [
                ("customer", "I can't log into my account. The password reset email never arrives.", _days_ago(2)),
                ("agent", "I'm sorry about that, Lisa. I've verified your email address is correct in our system. Let me manually reset your password and send it to your email directly.", _days_ago(2)),
                ("agent", "I've sent a new password to your email. Please check and let me know if it works.", _days_ago(1)),
            ],
        },
        # More active conversations
        {
            "id": "conv_09", "customer_id": "cust_02", "channel": "chat", "status": "active",
            "sentiment_score": 0.5, "subject": "Custom report building",
            "assigned_to": None, "created_at": _hours_ago(1),
            "messages": [
                ("customer", "Is there a way to build custom analytics reports? I need to track specific metrics for my team.", _hours_ago(1)),
                ("bot", "Yes! On the Pro plan, you can access our Custom Reports builder from the Analytics page. You can create reports with custom date ranges, filters, and metrics. Reports can be exported as CSV or PDF.", _hours_ago(1)),
                ("customer", "Awesome, that sounds great. Can I schedule reports to be emailed weekly?", _hours_ago(1)),
            ],
        },
        {
            "id": "conv_10", "customer_id": "cust_05", "channel": "chat", "status": "active",
            "sentiment_score": 0.4, "subject": "Integration with Slack",
            "assigned_to": "Agent Jones", "created_at": _hours_ago(8),
            "messages": [
                ("customer", "We'd love to get Herald notifications in our Slack workspace. Is that possible?", _hours_ago(8)),
                ("agent", "Absolutely, Priya! We have a native Slack integration. Go to Settings > Integrations > Slack, and click 'Connect'. You can configure which events trigger Slack notifications.", _hours_ago(7)),
                ("customer", "What events can we get notifications for?", _hours_ago(7)),
                ("agent", "You can get notifications for new conversations, ticket escalations, negative sentiment alerts, and customer churn risk changes. Each can be sent to a different Slack channel.", _hours_ago(6)),
            ],
        },
        {
            "id": "conv_11", "customer_id": "cust_01", "channel": "chat", "status": "active",
            "sentiment_score": 0.3, "subject": "SSO configuration",
            "assigned_to": "Agent Smith", "created_at": _hours_ago(4),
            "messages": [
                ("customer", "We need to set up SAML SSO for our team. Can you walk me through the process?", _hours_ago(4)),
                ("agent", "Of course, Sarah! SSO is available on your Enterprise plan. Go to Settings > Security > SSO. You'll need your Identity Provider's metadata XML or the SSO URL, Entity ID, and certificate.", _hours_ago(4)),
                ("customer", "We use Okta. Do you have specific instructions for Okta integration?", _hours_ago(3)),
            ],
        },
        {
            "id": "conv_12", "customer_id": "cust_08", "channel": "chat", "status": "active",
            "sentiment_score": 0.6, "subject": "Bulk customer import",
            "assigned_to": None, "created_at": _hours_ago(2),
            "messages": [
                ("customer", "We're migrating from Intercom and need to import about 50,000 customer records. What's the best approach?", _hours_ago(2)),
                ("bot", "For large imports like that, I'd recommend using our API's batch import endpoint. You can send up to 1000 records per request. We also support direct CSV upload for up to 10,000 records through the dashboard.", _hours_ago(2)),
                ("customer", "The API approach sounds better for our volume. Is there a migration guide?", _hours_ago(1)),
            ],
        },
    ]

    for conv in conversations_data:
        conn.execute(
            """INSERT INTO conversations (id, customer_id, channel, status, sentiment_score, satisfaction, assigned_to, subject, resolved_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                conv["id"], conv["customer_id"], conv["channel"], conv["status"],
                conv.get("sentiment_score"), conv.get("satisfaction"),
                conv.get("assigned_to"), conv.get("subject"),
                conv.get("resolved_at"), conv["created_at"],
            ),
        )

        for role, content, created_at in conv["messages"]:
            msg_id = uuid4().hex
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (msg_id, conv["id"], role, content, created_at),
            )

    # Update conversation counts
    for cid in ["cust_01", "cust_02", "cust_03", "cust_04", "cust_05", "cust_06", "cust_07", "cust_08"]:
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE customer_id = ?", (cid,)
        ).fetchone()["cnt"]
        conn.execute("UPDATE customers SET total_conversations = ? WHERE id = ?", (count, cid))

    # ==================== TICKETS ====================
    tickets_data = [
        ("tkt_01", "conv_03", "cust_04", "Duplicate billing charge", "Charged twice for Pro plan in March. Third occurrence.", "open", "urgent", "billing", "Agent Smith", None, _days_ago(3), _days_ago(3)),
        ("tkt_02", "conv_02", "cust_03", "Chat widget not loading", "Widget fails to load after deployment. CSP issue identified.", "in_progress", "high", "bug", "Agent Jones", None, _hours_ago(6), _hours_ago(4)),
        ("tkt_03", None, "cust_07", "Password reset emails not arriving", "Customer reports password reset emails never arrive. Email verified correct.", "waiting", "medium", "technical", "Agent Brown", None, _days_ago(2), _days_ago(1)),
        ("tkt_04", "conv_04", "cust_02", "Webhook setup assistance", "Customer needed help configuring webhook endpoints for ticket events.", "resolved", "low", "technical", "Agent Brown", "Guided customer through Settings > Integrations. Webhook configured successfully.", _days_ago(5), _days_ago(4)),
        ("tkt_05", None, "cust_06", "Feature request: lower tier plan", "Solo freelancer finding Starter plan too expensive. Suggested trial.", "resolved", "low", "feature", "Agent Jones", "Offered 14-day Starter trial. Customer accepted.", _days_ago(10), _days_ago(9)),
        ("tkt_06", None, "cust_01", "SAML SSO configuration", "Enterprise customer needs help setting up Okta SSO integration.", "open", "medium", "technical", "Agent Smith", None, _hours_ago(4), _hours_ago(4)),
        ("tkt_07", None, "cust_05", "Slack integration setup", "Customer wants to configure Slack notifications for Herald events.", "in_progress", "low", "feature", "Agent Jones", None, _hours_ago(8), _hours_ago(6)),
        ("tkt_08", None, "cust_08", "Bulk data migration from Intercom", "Enterprise customer migrating 50K records. Needs API batch import guidance.", "open", "medium", "technical", None, None, _hours_ago(2), _hours_ago(2)),
    ]

    for tid, conv_id, cust_id, subject, desc, status, priority, category, assigned, resolution, created, updated in tickets_data:
        resolved_at = None
        if status in ("resolved", "closed"):
            resolved_at = updated
        conn.execute(
            """INSERT INTO tickets (id, conversation_id, customer_id, subject, description, status, priority, category, assigned_to, resolution_notes, created_at, updated_at, resolved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tid, conv_id, cust_id, subject, desc, status, priority, category, assigned, resolution, created, updated, resolved_at),
        )

    # ==================== ONBOARDING FLOWS ====================
    flow1_steps = json.dumps([
        {"title": "Create Account", "content": "Sign up for Herald and verify your email address.", "action_type": "setup", "completed": False},
        {"title": "Add Team Members", "content": "Invite your support agents and assign roles (Admin, Agent, Viewer).", "action_type": "setup", "completed": False},
        {"title": "Configure Chatbot", "content": "Set up your chatbot greeting message and customize the chat widget appearance.", "action_type": "configure", "completed": False},
        {"title": "Install Widget", "content": "Add the Herald chat widget to your website by pasting the provided script tag.", "action_type": "install", "completed": False},
        {"title": "Send Test Message", "content": "Send a test message through your widget to verify everything is working correctly.", "action_type": "verify", "completed": False},
    ])

    flow2_steps = json.dumps([
        {"title": "Connect Data Sources", "content": "Import your existing customer data via CSV upload or API integration.", "action_type": "setup", "completed": False},
        {"title": "Set Up Integrations", "content": "Connect Herald to your existing tools: Slack, email, CRM, and webhooks.", "action_type": "configure", "completed": False},
        {"title": "Configure Automation", "content": "Set up ticket auto-assignment rules, escalation policies, and SLA timers.", "action_type": "configure", "completed": False},
    ])

    conn.execute(
        "INSERT INTO onboarding_flows (id, name, description, steps_json, active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
        ("flow_01", "Getting Started", "Basic setup flow for new Herald customers", flow1_steps, _days_ago(200)),
    )
    conn.execute(
        "INSERT INTO onboarding_flows (id, name, description, steps_json, active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
        ("flow_02", "Advanced Setup", "Advanced configuration for Pro and Enterprise customers", flow2_steps, _days_ago(200)),
    )

    # ==================== CUSTOMER ONBOARDING RECORDS ====================
    onboarding_records = [
        ("onb_01", "cust_01", "flow_01", 5, 1, _days_ago(175), _days_ago(170)),   # completed
        ("onb_02", "cust_01", "flow_02", 3, 1, _days_ago(170), _days_ago(165)),   # completed
        ("onb_03", "cust_02", "flow_01", 4, 0, _days_ago(85), None),               # on step 4
        ("onb_04", "cust_03", "flow_01", 2, 0, _days_ago(55), None),               # on step 2
    ]

    for oid, cust_id, flow_id, step, completed, started, completed_at in onboarding_records:
        conn.execute(
            """INSERT INTO customer_onboarding (id, customer_id, flow_id, current_step, completed, started_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (oid, cust_id, flow_id, step, completed, started, completed_at),
        )

    # ==================== COPILOT SUGGESTIONS ====================
    suggestions = [
        ("sug_01", "conv_02", "I've identified the issue — your Content Security Policy is blocking our CDN domain. Add 'cdn.herald.io' to your script-src and connect-src CSP directives. This should resolve the widget loading problem immediately.", 1, _hours_ago(5)),
        ("sug_02", "conv_02", "Let me check our CDN status page to make sure there isn't a broader outage affecting your region. In the meantime, could you share your browser's console output?", 0, _hours_ago(5)),
        ("sug_03", "conv_03", "I sincerely apologize for the recurring billing issue. I've processed an immediate refund and applied a credit for one free month of service as compensation. I'm also escalating this to our engineering team to fix the root cause.", 1, _days_ago(3)),
        ("sug_04", "conv_03", "I understand your frustration, James. Let me connect you with our billing team manager directly so we can resolve this once and for all.", 0, _days_ago(3)),
        ("sug_05", "conv_08", "I've manually generated a new password reset link and sent it to your registered email. If you don't see it within 5 minutes, please check your spam folder. I'll also investigate why the automated reset emails aren't being delivered.", 1, _days_ago(2)),
        ("sug_06", "conv_10", "Our Slack integration supports real-time notifications for new conversations, escalations, and sentiment alerts. You can configure notification channels per event type. Would you like me to walk you through the setup?", 0, _hours_ago(7)),
    ]

    for sid, conv_id, suggestion, used, created in suggestions:
        conn.execute(
            "INSERT INTO copilot_suggestions (id, conversation_id, suggestion, used, created_at) VALUES (?, ?, ?, ?, ?)",
            (sid, conv_id, suggestion, used, created),
        )

    conn.commit()
