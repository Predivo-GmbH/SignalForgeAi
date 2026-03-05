# Privacy Policy

**Last Updated:** March 5, 2026

This Privacy Policy describes how SignalForge ("we", "us", "our") collects, uses, stores, and protects your personal information when you use our AI-powered cryptocurrency trading platform ("the Service").

SignalForge is a personal trading tool designed for automated signal generation, portfolio management, and performance tracking.

---

## 1. Data Controller

SignalForge operates as a self-hosted trading platform. The data controller is the individual or organization operating the SignalForge instance.

**Contact:** support@signalforge.dev

---

## 2. Data We Collect

### 2.1 Account Information
- **Email address** -- used for authentication and account recovery
- **Password** -- stored as a bcrypt hash; we never store plaintext passwords
- **Two-Factor Authentication (2FA) secrets** -- encrypted at rest using Fernet symmetric encryption

### 2.2 Trading Activity
- **Strategies** -- strategy configurations, parameters, and activation status
- **Signals** -- generated trading signals from the signal engine pipeline
- **Trades** -- executed and paper trade records, including entry/exit prices, timestamps, and outcomes
- **Positions** -- current and historical portfolio positions
- **Backtest results** -- historical strategy performance data
- **AI Advisor interactions** -- market analysis requests and responses (usage costs tracked)

### 2.3 Broker Credentials
- **API keys and secrets** -- encrypted at rest using Fernet symmetric encryption
- **Broker connection metadata** -- exchange name, connection purpose (read/trade), activation status

### 2.4 System Data
- **Authentication tokens** -- JWT session tokens with expiration
- **API request logs** -- request timestamps and endpoints (no request bodies logged in production)

---

## 3. How We Use Your Data

We use the data we collect exclusively for the following purposes:

- **Authentication and authorization** -- verifying your identity and securing your account
- **Automated trading** -- executing trading strategies via connected broker APIs
- **Signal generation** -- running the 6-layer technical analysis pipeline on market data
- **Portfolio analysis** -- tracking holdings, performance, and risk metrics
- **Performance tracking** -- recording trade outcomes for analytics and strategy refinement
- **AI-powered insights** -- providing market analysis and strategy recommendations via the AI Advisor
- **Self-learning loop** -- analyzing trade patterns and adjusting risk parameters based on historical results

---

## 4. Data Storage and Security

### 4.1 Encryption
- **Passwords** are hashed using bcrypt with automatic salting
- **Broker API credentials** are encrypted at rest using Fernet symmetric encryption (AES-128-CBC with HMAC)
- **2FA secrets** are encrypted at rest using Fernet symmetric encryption
- **JWT tokens** are signed using HS256 with a server-side secret key

### 4.2 Infrastructure
- All data is stored on a dedicated server (not shared hosting)
- The database (TimescaleDB) runs in an isolated Docker container
- Redis is used for session caching and rate limiting, with data stored in memory only
- All inter-service communication occurs within an isolated Docker network

### 4.3 Access Controls
- API endpoints are protected by JWT authentication
- Live trading operations require active TOTP two-factor authentication
- Broker API keys can be scoped with separate read-only and trade-capable credentials

---

## 5. Third-Party Services

### 5.1 What We Do NOT Use
- **No third-party analytics** (no Google Analytics, Mixpanel, or similar)
- **No tracking cookies** or advertising pixels
- **No data brokers** or data sharing with third parties for marketing purposes

### 5.2 External Services
- **Cryptocurrency exchanges** (e.g., Binance) -- market data retrieval and order execution via your API keys
- **Anthropic Claude API** -- AI-powered market analysis (only market data and strategy parameters are sent; no personal information is transmitted)
- **CoinGecko API** -- cryptocurrency metadata (market cap, icons, rankings); no user data is sent

---

## 6. Cookies and Tracking

SignalForge does **not** use cookies for tracking or analytics. The only client-side storage used is:

- **JWT authentication tokens** stored in browser memory for session management
- **Local storage** for UI preferences (theme, language settings)

---

## 7. Data Retention

We retain your data according to the following schedule:

| Data Category | Retention Period |
|---------------|-----------------|
| Account information | Lifetime of your account |
| Trading data (signals, trades, orders, positions) | Lifetime of your account |
| AI interaction logs | 90 days |
| Authentication logs | 90 days |
| Backups containing personal data | 14 days after creation |

Upon account deletion, all personal data is permanently removed from our active
database within 24 hours. Backup copies containing your data are automatically
purged within 14 days of creation.

---

## 8. Your Rights

Under applicable data protection regulations (including GDPR), you have the following rights:

### 8.1 Right of Access
You can access all your data through the platform's data export functionality:
- **API endpoint:** `GET /api/auth/user/export` -- exports your complete data in JSON format
- **Dashboard access:** all trading data, signals, and performance metrics are visible in the application

### 8.2 Right to Erasure
You can request complete deletion of your account and all associated data:
- **API endpoint:** `DELETE /api/auth/user` -- permanently deletes your account and all data
- This action is irreversible and removes all trading history, strategies, signals, broker connections, and personal information

### 8.3 Right to Data Portability
You can export your data in a machine-readable format (JSON) using the data export endpoint referenced in Section 8.1.

### 8.4 Right to Rectification
You can update your account information (email, password) through the Settings page or API endpoints.

### 8.5 Right to Restrict Processing
You can deactivate individual strategies to stop signal generation and trading for specific configurations without deleting your data.

---

## 9. Data Processing Legal Basis (GDPR)

We process your data based on the following legal grounds:

- **Contractual necessity** -- processing required to provide the trading platform service you signed up for
- **Legitimate interest** -- security monitoring, performance analytics, and service improvement
- **Consent** -- for optional features such as the AI Advisor

---

## 10. International Data Transfers

SignalForge is a self-hosted application. Your data is stored on the server where your instance is deployed. No data is transferred to other jurisdictions unless:

- You connect to a cryptocurrency exchange API hosted in another country (necessary for trading functionality)
- The AI Advisor sends market data to Anthropic's API for analysis (no personal data is included in these requests)

---

## 11. Data Breach Notification

In the event of a data breach that affects your personal information, we will:

1. Investigate and contain the breach as quickly as possible
2. Notify affected users via email within 72 hours of discovery
3. Report to relevant data protection authorities as required by law

---

## 12. Children's Privacy

SignalForge is not intended for use by individuals under the age of 18. We do not knowingly collect data from minors. If you believe a minor has created an account, please contact us immediately.

---

## 13. Changes to This Policy

We may update this Privacy Policy from time to time to reflect changes in our practices or legal requirements. When we make material changes:

- We will notify registered users via email
- The "Last Updated" date at the top of this document will be revised
- Continued use of the Service after notification constitutes acceptance of the updated policy

---

## 14. Contact Us

If you have questions about this Privacy Policy or wish to exercise your data protection rights, please contact:

**Email:** support@signalforge.dev

---

*This Privacy Policy applies to the SignalForge trading platform. By using the Service, you acknowledge that you have read and understood this policy.*
