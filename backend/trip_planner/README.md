# Trip Planner - AI Agent System

Production-grade AI trip planning agent with multi-tier memory system, tool integration, and context management.

## 📁 Project Structure

```
trip_planner/
├── Core Agent Components
│   ├── __init__.py          # Package initialization & exports
│   ├── orchestrate.py       # LangGraph state machine (agent loop)
│   ├── role.py              # Agent persona/system prompt
│   ├── llm.py               # LLM initialization (Qwen + embeddings)
│   ├── tools.py             # External tools (search, weather)
│   └── context.py           # Context window management
│
├── Memory System (Production-Grade)
│   ├── memory.py            # Re-exports for backward compatibility
│   └── memory/              # Multi-tier memory implementation
│       ├── README.md        # Memory system quick start
│       ├── OVERVIEW.md      # Architecture documentation
│       ├── MEMORY_ARCHITECTURE.md  # Complete system guide
│       ├── schema.sql       # PostgreSQL database schema
│       ├── legacy.py        # JSONL-based SimpleMemory
│       ├── models.py        # Data models
│       ├── connections.py   # Connection managers
│       ├── manager.py       # Memory orchestrator
│       ├── intra_session.py # Redis (fast, temporary)
│       ├── inter_session.py # PostgreSQL + Qdrant (persistent)
│       └── preferences.py   # User preferences (cached)
│
├── Entry Points
│   ├── main.py              # CLI interface for testing
│   ├── session.py           # Session management for evaluation
│   └── user.py              # User interface helpers
│
├── Documentation
│   ├── docs/                # General documentation
│   │   ├── IMPLEMENTATION_SUMMARY.md
│   │   ├── MEMORY_README.md
│   │   └── Dockerfile
│   └── examples/            # Example outputs & screenshots
│
└── Utilities
    └── version.py           # Version information
```

## 🚀 Quick Start

### Basic Usage (CLI)
```bash
# Run interactive CLI
python -m trip_planner.main

# Example query
> Plan a 3-day trip to Paris, check weather and search for attractions
```

### As a Module
```python
from trip_planner import make_app
from trip_planner.tools import TOOLS
from trip_planner.llm import init_llm
from langchain_core.messages import SystemMessage, HumanMessage

# Initialize
llm = init_llm(TOOLS)
app = make_app(llm, TOOLS, context_scale=5)

# Run agent
state = {"messages": [
    SystemMessage(content="You are a travel planner"),
    HumanMessage(content="Plan a trip to Tokyo")
]}
result = app(state)
```

## 🧠 Memory System

### Three-Tier Architecture

**Intra-Session** (Redis):
- Fast, temporary storage for active conversations
- TTL: 2 hours (configurable)
- Use case: Current conversation context

**Inter-Session** (PostgreSQL + Qdrant):
- Persistent conversation storage
- Semantic vector search across all past conversations
- Use case: "Remember when we planned a trip to Europe?"

**User Preferences** (PostgreSQL + Redis cache):
- Long-term user-specific data
- Two-tier caching for performance
- Use case: Travel style, budget preferences, dietary restrictions

### Configuration

Set in `.env`:
```bash
# Memory Mode
USE_LEGACY_MEMORY=True  # True = JSONL, False = Production

# Production (if USE_LEGACY_MEMORY=False)
REDIS_HOST=localhost
PG_HOST=localhost
QDRANT_HOST=localhost
```

See [memory/README.md](./memory/README.md) for detailed documentation.

## 🛠️ Core Components

### Orchestrator (`orchestrate.py`)
- **LangGraph** state machine for agent loop
- Implements ReAct pattern (Reason → Act → Observe)
- Automatic tool calling and response generation

### Tools (`tools.py`)
- `search_tool`: Web search (Wikipedia → DuckDuckGo fallback)
- `weather_tool`: Weather forecasts (Open-Meteo API)
- Extensible: Add new tools by decorating functions with `@tool`

### Context Management (`context.py`)
- Smart context window trimming
- Preserves complete tool call sequences
- Keeps recent user messages
- Configurable window size

### LLM Integration (`llm.py`)
- **Model**: Qwen (via DashScope API)
- **Embeddings**: Azure OpenAI text-embedding-3-small
- Tool binding for function calling

## 📊 Key Features

- ✅ **ReAct Agent**: Think → Act → Observe loop
- ✅ **Tool Integration**: Search, weather, extensible
- ✅ **Smart Context**: Trimming with message preservation
- ✅ **Three-Tier Memory**: Fast, persistent, searchable
- ✅ **Production Ready**: Connection pooling, caching
- ✅ **Type Safe**: Full type hints
- ✅ **Well Documented**: 1500+ lines of docs

## 🎯 Usage Examples

### CLI Mode
```bash
# Interactive mode
python -m trip_planner.main

# With long-term memory
USE_LTM=1 python -m trip_planner.main

# Configure context size
MAX_TURNS_IN_CONTEXT=10 python -m trip_planner.main
```

### Evaluation Mode
```python
from trip_planner.session import Session

session = Session(
    background_info="User prefers luxury travel",
    verbose=True
)

result = session.chat(
    user_request="Plan a weekend in Paris",
    context_size=6,
    use_ltm=True,
    store_to_cache=True
)
```

## 🔧 Configuration

Environment variables (set in `.env`):

```bash
# LLM Configuration
DASHSCOPE_API_KEY=your_key
QWEN_MODEL=qwen-plus
QWEN_TEMPERATURE=0.7
QWEN_MAX_TOKENS=1000

# Embeddings
EMBEDDING_DEPLOYMENT=text-embedding-3-small
EMBEDDING_API_KEY=your_azure_key
EMBEDDING_AZURE_ENDPOINT=https://your-endpoint.openai.azure.com/

# Agent Configuration
USE_LTM=True                # Enable long-term memory
MAX_TURNS_IN_CONTEXT=5      # Context window size
VERBOSE=True                # Debug output

# Memory System (Production)
USE_LEGACY_MEMORY=True      # False for production system
REDIS_HOST=localhost
PG_DATABASE=trip_planner
QDRANT_COLLECTION=conversations
```

## 📚 Documentation

- **Quick Start**: This file
- **Memory System**: [memory/README.md](./memory/README.md)
- **Architecture**: [memory/OVERVIEW.md](./memory/OVERVIEW.md)
- **Full Docs**: [memory/MEMORY_ARCHITECTURE.md](./memory/MEMORY_ARCHITECTURE.md)
- **Database**: [memory/schema.sql](./memory/schema.sql)
- **Implementation**: [docs/IMPLEMENTATION_SUMMARY.md](./docs/IMPLEMENTATION_SUMMARY.md)

## 🧪 Testing

```bash
# Test imports
python -c "from trip_planner import make_app; print('✓ Imports work')"

# Test memory system
python -c "from trip_planner.memory import SimpleMemory; print('✓ Memory works')"

# Run CLI
python -m trip_planner.main
```

## 🏗️ Architecture

### Agent Loop (LangGraph)
```
User Input
    ↓
SystemMessage (role) + HumanMessage
    ↓
┌─────────────┐
│   Agent     │ ← Thinks about what to do
└─────────────┘
    ↓ Need tool?
    Yes → Call Tool → ToolMessage
    ↓         ↓
    └─────────┘ (loop back to agent)
    ↓
    No → Generate Response
    ↓
AIMessage (final answer)
```

### Memory Flow
```
Active Conversation (Redis)
    ↓ TTL expires
Persistent Storage (PostgreSQL)
    ↓ Async
Embedding Generation
    ↓
Vector Database (Qdrant)
    ↓
Future: Semantic Search
```

## 📦 Dependencies

Core:
- `langchain` - Agent framework
- `langgraph` - State machine
- `langchain-openai` - LLM integration
- `numpy` - Vector operations

Production Memory (optional):
- `redis` - Fast caching
- `sqlalchemy` - PostgreSQL ORM
- `qdrant-client` - Vector search

Install:
```bash
# Core only
pip install -r ../requirements.txt

# With production memory
pip install redis sqlalchemy psycopg2-binary qdrant-client
```

## 🔍 Code Overview

| File | Lines | Purpose |
|------|-------|---------|
| `orchestrate.py` | 34 | LangGraph state machine |
| `context.py` | 186 | Context window management |
| `tools.py` | 139 | External tool integrations |
| `session.py` | 263 | Evaluation session management |
| `main.py` | 96 | CLI entry point |
| `llm.py` | 29 | LLM initialization |
| `memory.py` | 51 | Memory re-exports |
| `role.py` | 5 | Agent persona |
| `user.py` | 24 | UI helpers |
| `__init__.py` | 14 | Package exports |

Memory system: ~1200 lines across 11 files (see [memory/](./memory/))

## 🚀 Production Deployment

See [memory/MEMORY_ARCHITECTURE.md](./memory/MEMORY_ARCHITECTURE.md) for:
- Infrastructure setup (Redis, PostgreSQL, Qdrant)
- Connection pooling configuration
- Monitoring and alerting
- Performance optimization
- Security best practices

## 💡 Extending the System

### Add New Tool
```python
# In tools.py
@tool("my_tool")
def my_tool(param: str) -> str:
    """Tool description for LLM."""
    return f"Result: {param}"

# Add to TOOLS list
TOOLS = [search_tool, weather_tool, my_tool]
```

### Custom Memory Store
```python
# Implement in memory/
class CustomMemoryStore:
    def save_message(self, session_id, message):
        # Your implementation
        pass
```

### Modify Agent Behavior
```python
# In role.py
role_template = "You are a [custom role]..."

# In orchestrate.py
def call_agent(state):
    # Custom pre-processing
    result = llm_invoke(state["messages"])
    # Custom post-processing
    return {"messages": [result]}
```

## 🤝 Contributing

1. Follow existing code style
2. Add type hints
3. Document new functions
4. Update README if adding features
5. Test backward compatibility

## 📝 License

[Your License Here]

---

**Version**: See [version.py](./version.py)  
**Last Updated**: 2025-11-07  
**Status**: ✅ Production Ready
