# 🤖 Rounds Analytics Bot

**AI-powered Slack bot for mobile app analytics with natural language to SQL conversion.**

## ⚡ Quick Start

```bash
# 1. Setup
git clone <repo> && cd rounds
pip install -r requirements.txt
cp env_template .env  # Add your tokens

# 2. Database  
docker-compose up -d
python main.py init-db && python main.py reset-db

# 3. Slack Setup
# Get tokens from https://api.slack.com/apps
# Add bot to workspace with required permissions

# 4. Run
python main.py start-bot
```

## 🎯 Features

- **Natural Language** → SQL conversion
- **Smart Responses** with context
- **CSV Exports** on demand
- **Query Caching** for performance
- **LangSmith Tracing** for monitoring

## 🔧 Tech Stack

**Backend:** Python, FastAPI, PostgreSQL, Redis  
**AI:** OpenAI GPT-4, LangChain  
**Slack:** Bolt SDK with Socket Mode  
**Observability:** LangSmith  

## 📊 Usage Examples

```
/analytics How many apps do we have?
@Rounds Analytics Bot Which platform performs better?
Compare iOS vs Android revenue last week
Show me top apps by installs in the US
```

## 🚀 Features

| Component | Status | Description |
|-----------|--------|-------------|
| 🧠 AI Engine | ✅ | GPT-4 NL→SQL conversion |
| 💬 Slack Bot | ✅ | Interactive responses & exports |
| 📊 Analytics | ✅ | App performance insights |
| 🚀 Performance | ✅ | Redis caching + optimization |
| 📈 Monitoring | ✅ | LangSmith integration |

## 🔧 Configuration

### Environment Variables Setup

1. **Copy the template:** `cp env_template .env`
2. **Fill in your values** using the examples below:

```bash
# =============================================================================
# SLACK CONFIGURATION
# =============================================================================
# Get these from https://api.slack.com/apps when creating your Slack app
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_APP_TOKEN=xapp-your-app-token-here

# =============================================================================
# OPENAI CONFIGURATION
# =============================================================================
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
OPENAI_MODEL=gpt-4-1106-preview

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
DATABASE_URL=postgresql://rounds_user:rounds_password@localhost:5434/rounds_analytics
DATABASE_HOST=localhost
DATABASE_PORT=5434
DATABASE_NAME=rounds_analytics
DATABASE_USER=rounds_user
DATABASE_PASSWORD=rounds_password

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================
REDIS_URL=redis://localhost:6381/0

# =============================================================================
# LANGSMITH OBSERVABILITY (Optional)
# =============================================================================
# Enable for advanced AI monitoring and debugging
LANGCHAIN_TRACING_V2=false
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your-langsmith-api-key-here
LANGCHAIN_PROJECT=rounds-chatbot

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================
DEBUG=true
LOG_LEVEL=INFO
MAX_QUERY_HISTORY=10
```

### 🔐 Security Notes

- **Never commit** your `.env` file to version control
- **Rotate tokens** regularly for production deployments
- **Use environment-specific** configurations for dev/staging/prod
- **Enable LangSmith** for production monitoring and debugging

## 📁 Architecture

```
rounds/
├── ai/                 # SQL generation & validation
├── slack_bot/          # Slack integration & UI
├── database/           # Models & data management  
├── observability/      # LangSmith tracking
└── main.py            # Application entry point
```

---

# 🛣️ Roadmap & Future Development

## 📅 Development Phases

### ✅ Phase 1: Core MVP (Completed)
**Goal:** Functional analytics bot with essential features

- [x] **AI Engine** - NL→SQL conversion with GPT-4
- [x] **Slack Integration** - Bot with commands & mentions  
- [x] **Data Export** - CSV downloads
- [x] **Caching** - Redis query optimization
- [x] **Observability** - LangSmith integration

---

### 🔄 Phase 2: Enhanced UX (Next 2-4 weeks)
**Goal:** Better user experience and reliability

- [ ] **Smart Visualizations** - Auto-generate charts/graphs
- [ ] **Conversation Context** - Multi-turn query sessions
- [ ] **Query Suggestions** - AI-powered recommendations
- [ ] **Error Recovery** - Better handling of failed queries
- [ ] **Performance Dashboard** - Real-time metrics

---

### 📋 Phase 3: Advanced Analytics (Month 2)
**Goal:** Deeper insights and automation

- [ ] **Scheduled Reports** - Daily/weekly automated summaries
- [ ] **Anomaly Detection** - Alert on unusual patterns
- [ ] **Comparative Analysis** - Period-over-period insights
- [ ] **Custom Dashboards** - User-defined analytics views
- [ ] **Mobile Responsiveness** - Optimized for mobile Slack

---

### 🚀 Phase 4: Enterprise Ready (Month 3+)
**Goal:** Production-scale deployment

- [ ] **Multi-Workspace** - Support multiple Slack workspaces
- [ ] **Role-Based Access** - Permission management
- [ ] **Data Connectors** - Integrate external data sources
- [ ] **API Gateway** - REST API for external integrations
- [ ] **Advanced Security** - SSO, audit logs, compliance

---

## 🎯 Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Query Success Rate | >95% | ~90% |
| Response Time | <3s | ~4s |
| User Adoption | 80% daily active | N/A |
| Cost per Query | <$0.05 | ~$0.08 |

## 🔧 Technical Improvements

### Performance
- [ ] **Query Optimization** - Smarter SQL generation
- [ ] **Parallel Processing** - Multiple queries simultaneously  
- [ ] **CDN Integration** - Faster file downloads

### Reliability  
- [ ] **Health Monitoring** - Proactive issue detection
- [ ] **Graceful Degradation** - Fallback mechanisms
- [ ] **Load Balancing** - Multi-instance deployment

### Developer Experience
- [ ] **Testing Suite** - Comprehensive test coverage
- [ ] **Documentation** - API docs & integration guides
- [ ] **CI/CD Pipeline** - Automated deployment

---

Built for **Rounds Interview Challenge** 🎯
