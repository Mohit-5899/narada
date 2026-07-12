# Agent System Boilerplate

A first-principles, transferable build spec distilled from reading the Hermes Agent codebase. Reproduce this architecture in any language/stack. No marketing, no abstraction-for-abstraction's-sake. Every subsystem here exists because the naive version breaks in production.

> **How to read this:** Each section has `WHAT / WHY / HOW / KEY DECISIONS`. The HOW blocks are pseudocode close to Python — translate to your language. The KEY DECISIONS sections are the non-obvious choices that separate a toy agent from a production one.

---

## Table of Contents

1. [The Foundation — What an agent actually is](#1-the-foundation)
2. [The Six Loops](#2-the-six-loops)
3. [The Core Loop — `run_conversation`](#3-the-core-loop)
4. [Subsystem A: Session Store (persistence)](#4-subsystem-a-session-store)
5. [Subsystem B: Context Engine](#5-subsystem-b-context-engine)
6. [Subsystem C: Provider Adapters](#6-subsystem-c-provider-adapters)
7. [Subsystem D: Tool Registry](#7-subsystem-d-tool-registry)
8. [Subsystem E: Execution Environments (sandboxes)](#8-subsystem-e-execution-environments)
9. [Subsystem F: Memory](#9-subsystem-f-memory)
10. [Subsystem G: Skills](#10-subsystem-g-skills)
11. [Subsystem H: Self-Improvement Loop](#11-subsystem-h-self-improvement-loop)
12. [Subsystem I: Streaming & Interrupts](#12-subsystem-i-streaming--interrupts)
13. [Subsystem J: Plugin Hooks](#13-subsystem-j-plugin-hooks)
14. [Subsystem K: Multi-Surface Entry Points](#14-subsystem-k-multi-surface-entry-points)
15. [Subsystem L: Subagents (delegation)](#15-subsystem-l-subagents-delegation)
16. [Subsystem M: Cost & Billing](#16-subsystem-m-cost--billing)
17. [Hard-Won Defenses](#17-hard-won-defenses)
18. [Wire Format Contracts](#18-wire-format-contracts)
19. [Configuration Surface](#19-configuration-surface)
20. [Build Order](#20-build-order)
21. [Anti-Patterns to Avoid](#21-anti-patterns-to-avoid)

---

## 1. The Foundation

### The fundamental truth

> An LLM is a **stateless, pure function**: `messages → next_message`. An "agent" is just **a loop that calls this function in a way that lets it call your code (tools) and observe the results**.

Everything else — memory, sessions, providers, skills, sandboxes — is plumbing around that one loop. If you remember nothing else, remember this. The architecture below is what production-grade plumbing looks like.

### Minimum viable agent

```python
def agent(user_msg, history, model, tools):
    history.append({"role": "user", "content": user_msg})
    while True:
        response = llm.call(history, tools=tools)
        history.append(response.assistant_message)
        if not response.tool_calls:
            return response.content        # ← done
        for tc in response.tool_calls:
            result = tool_registry[tc.name](tc.args)
            history.append({"role": "tool", "id": tc.id, "content": result})
        # loop
```

**That's the entire core.** Everything in the rest of this document is the answer to a specific production problem you'll hit if you ship the version above.

---

## 2. The Six Loops

Hold these in your head. Every line of code you'll write belongs to one of them.

```
1. PROCESS LOOP — daemon stays alive forever (gateway / API server)
   2. SESSION LOOP — one conversation lasts many user turns
      3. AGENT TURN LOOP — one user message = many API calls (tool calls)
         4. TOOL EXECUTION LOOP — one tool call may spawn a subagent (back to #3)
   5. SELF-REVIEW LOOP — fires after a turn closes, on borrowed time
6. CURATOR LOOP — runs daily, separate process, cleans up the library
```

Each loop has its own:

| | Exit condition | State store | Failure mode |
|---|---|---|---|
| 1 Process | SIGTERM / kill | Process memory | OOM, crash |
| 2 Session | User /reset, idle expiry | SQLite row | Corrupt DB |
| 3 Turn | No tool_calls returned, budget exhausted | In-memory messages list | Runaway tools |
| 4 Tool exec | Result returned or timeout | Tool result string | Infinite delegation |
| 5 Self-review | Review agent's own exit | Shared memory store | Bad facts saved |
| 6 Curator | Daily cron tick | Skills directory | Over-consolidation |

Build them in this order: 3 → 2 → 4 → 1 → 5 → 6. (Section 20 expands.)

---

## 3. The Core Loop

### What it is

`run_conversation(user_msg) → final_response`. This is the function that owns Loop #3.

### Skeleton (with the production wrapping)

```python
def run_conversation(self, user_message, conversation_history=None, stream_callback=None):
    # ── PHASE 1: pre-flight setup ──────────────────────────────────────
    ensure_db_session()                                         # SessionDB row exists
    user_message = sanitize_surrogates(user_message)            # strip lone UTF-16
    cleanup_dead_connections()                                  # zombie TCP from prior outages
    messages = list(conversation_history or [])
    user_idx = len(messages)
    messages.append({"role": "user", "content": user_message})

    # ── PHASE 2: system prompt (cached for prefix-cache stability) ────
    if self._cached_system_prompt is None:
        if conversation_history:
            self._cached_system_prompt = session_db.get(session_id).system_prompt
        else:
            self._cached_system_prompt = build_system_prompt()
            session_db.update_system_prompt(session_id, self._cached_system_prompt)

    # ── PHASE 3: preflight compression ─────────────────────────────────
    if compression_enabled and estimate_tokens(messages, tools) >= threshold:
        for _ in range(3):   # may need multiple passes on big sessions
            messages = context_engine.compress(messages)
            if estimate_tokens(messages, tools) < threshold:
                break

    # ── PHASE 4: memory prefetch (once per turn, cached) ──────────────
    memory_snippet = memory_manager.prefetch_all(user_message)

    # ── PHASE 5: pre-llm-call plugin hook ──────────────────────────────
    plugin_context = invoke_hook("pre_llm_call", messages=messages, ...)

    # ── PHASE 6: the loop ──────────────────────────────────────────────
    iteration_budget = IterationBudget(self.max_iterations)   # shared with subagents
    api_call_count = 0
    final_response = None

    while api_call_count < self.max_iterations and iteration_budget.remaining > 0:
        if self.interrupt_requested:
            break

        iteration_budget.consume()
        api_call_count += 1

        # 6a. Drain pending /steer commands (user input during model thinking)
        drain_pending_steer_into_last_tool_message(messages)

        # 6b. Defensive cleanup before EVERY API call
        repair_corrupted_tool_call_arguments(messages)
        repair_message_alternation(messages)                  # tool→user→user bugs

        # 6c. Build API copy (do NOT mutate `messages`)
        api_messages = []
        for idx, msg in enumerate(messages):
            api_msg = msg.copy()
            if idx == user_idx:
                api_msg["content"] += "\n\n" + memory_snippet + "\n\n" + plugin_context
            copy_reasoning_content_for_api(msg, api_msg)
            strip_provider_specific_fields(api_msg)
            api_messages.append(api_msg)
        api_messages = [{"role": "system", "content": effective_system_prompt}] + api_messages

        # 6d. Provider-specific normalization
        api_messages = sanitize_orphaned_tool_results(api_messages)
        api_messages = drop_thinking_only_assistant_turns(api_messages)
        api_messages = normalize_whitespace_and_tool_call_json(api_messages)
        if use_prompt_caching:
            api_messages = apply_anthropic_cache_breakpoints(api_messages)

        # 6e. The actual call
        response = interruptible_api_call(api_messages, stream_callback)

        context_engine.update_from_response(response.usage)
        messages.append(response.assistant_message)
        session_db.save_message(response.assistant_message)

        # 6f. Done?
        if not response.tool_calls:
            final_response = response.content
            break

        # 6g. Execute tools (parallel if batch is independent)
        execute_tool_calls(response.tool_calls, messages, task_id)

    # ── PHASE 7: post-turn ─────────────────────────────────────────────
    check_skill_nudge_trigger()                                # _iters_since_skill
    check_memory_nudge_trigger()                               # _turns_since_memory
    if final_response and not interrupted and (nudge_fired):
        spawn_background_review(messages_snapshot=list(messages))

    invoke_hook("on_session_end", ...)
    return {"final_response": final_response, "messages": messages, ...}
```

### Key decisions

1. **Cache the system prompt byte-for-byte.** On continuing sessions, load it from the session store. Rebuilding it picks up memory the model already wrote — and that breaks Anthropic prefix caching, doubling input cost.

2. **Mutate a copy for the API call, never `messages` itself.** Memory snippets, plugin context, system prompt — all injected into `api_messages`, never the persisted history. Otherwise replays show injections as if the user typed them.

3. **Run the API call inside `while`, not after.** A turn is not "one API call." A turn is "many API calls until the model stops requesting tools." Loop boundary = no `tool_calls` field.

4. **Iteration budget is shared with subagents.** A subagent that burns 30 iterations subtracts from the parent's remaining 60. Single shared counter prevents runaway delegation trees.

5. **Run nudge triggers AFTER `final_response`.** The user has their answer; self-improvement work runs on borrowed time.

6. **Sanitize on every iteration, not just on entry.** Tool results can be corrupted, providers can return weird sequences, model can emit malformed JSON. Defense in depth.

---

## 4. Subsystem A: Session Store

### WHAT
Durable record of every conversation, message, tool call, token count, and cost — keyed by session id.

### WHY
- The LLM is stateless; persistence is the only memory across process restarts
- Gateway servers create a fresh agent per inbound message — they NEED to reload history
- Replayability for debugging and trajectory mining
- Search across past sessions (FTS5)

### HOW

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,           -- 'cli', 'telegram', 'discord', 'cron', ...
    user_id TEXT,
    model TEXT,
    model_config TEXT,              -- JSON snapshot of provider/api_mode/etc.
    system_prompt TEXT,             -- cached, see Sec 3 key decision #1
    parent_session_id TEXT,         -- for subagent lineage
    started_at REAL NOT NULL,
    ended_at REAL,
    end_reason TEXT,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    estimated_cost_usd REAL,
    actual_cost_usd REAL,
    title TEXT,
    api_call_count INTEGER DEFAULT 0,
    FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,             -- 'system' | 'user' | 'assistant' | 'tool'
    content TEXT,
    tool_call_id TEXT,              -- for role='tool', pairs with the assistant call
    tool_calls TEXT,                -- JSON: for role='assistant' with function calls
    tool_name TEXT,                 -- for role='tool', the function name
    timestamp REAL NOT NULL,
    token_count INTEGER,
    finish_reason TEXT,
    reasoning TEXT,                 -- model's chain-of-thought (display)
    reasoning_content TEXT,         -- for sending back to provider on next turn
    reasoning_details TEXT          -- provider-specific signed reasoning
);

-- Full-text search across all messages → enables /session_search tool
CREATE VIRTUAL TABLE messages_fts USING fts5(content);

CREATE INDEX idx_sessions_source ON sessions(source);
CREATE INDEX idx_sessions_parent ON sessions(parent_session_id);
CREATE INDEX idx_messages_session ON messages(session_id, timestamp);
```

### Key decisions

1. **One row per message, not per turn.** Tool results are separate rows. Trajectory is byte-recoverable.

2. **Store reasoning separately from content.** Modern reasoning models emit both. Providers like Moonshot/DeepSeek require `reasoning_content` to be sent BACK on the next turn for coherence. Store all three columns (`reasoning`, `reasoning_content`, `reasoning_details`) because their semantics differ across providers.

3. **`parent_session_id` builds the subagent tree.** Lets the curator see *"this agent spawned 14 subagents this week."*

4. **Pre-compute token + cost columns.** Don't recompute on every billing query. Update them after each API call.

5. **FTS5 is the agent's own time machine.** Expose it as a `session_search` tool so the agent can find "that thing from 3 weeks ago."

6. **Embedded SQLite over a server DB.** No daemon, no network hop, ACID, file-portable. Don't reach for Postgres until you need multi-writer concurrency.

---

## 5. Subsystem B: Context Engine

### WHAT
An ABC that owns: token tracking, "when to compress" policy, and "how to compress" logic. Pluggable.

### WHY
- Context windows fill up. The LLM 400s if you exceed them.
- Different strategies make sense for different workloads (summarize vs. DAG vs. eviction).
- Decoupling lets you experiment without touching the loop.

### HOW

```python
class ContextEngine(ABC):
    name: str
    last_prompt_tokens: int = 0
    last_completion_tokens: int = 0
    threshold_tokens: int = 0
    context_length: int = 0
    threshold_percent: float = 0.75      # compress at 75% full
    protect_first_n: int = 3             # always keep first N messages (system, user, first response)
    protect_last_n: int = 6              # always keep last N messages

    @abstractmethod
    def update_from_response(self, usage: dict): ...        # called after each API call

    @abstractmethod
    def should_compress(self, prompt_tokens=None) -> bool: ...

    @abstractmethod
    def compress(self, messages, focus_topic=None) -> list[Message]: ...

    def should_compress_preflight(self, messages) -> bool:
        return False                                          # cheap rough check before API

    def on_session_start(self, session_id, **kwargs): ...
    def on_session_end(self, session_id, messages): ...
    def on_session_reset(self): ...

    def get_tool_schemas(self) -> list:    return []         # engines can expose their own tools
    def handle_tool_call(self, name, args) -> str: ...

    def update_model(self, model, context_length, ...): ...  # called on model switch
```

### Default implementation: ContextCompressor

- Track running token usage from API response `usage` field
- When `prompt_tokens >= threshold_tokens` (default 75% of context window), trigger compression
- Compression: take messages `[protect_first_n : -protect_last_n]`, send them to an auxiliary LLM with a "summarize this conversation segment, preserve facts and decisions" prompt, replace them with a single synthetic `{"role": "assistant", "content": "<summary>"}` message
- Bump `compression_count` so the UI can show "compressed 3x this session"
- May run **multiple passes** if even after summarization the result is still too big (small context window, huge history)

### Alternative implementation: LCM (Latent Conversation Model)

Builds a DAG instead of summarizing. Exposes tools `lcm_grep`, `lcm_describe`, `lcm_expand` so the agent can fetch sub-conversations from the graph on demand. Plugin lives in `plugins/context_engine/lcm/`.

### Key decisions

1. **The engine OWNS token tracking.** Don't scatter `total_tokens += response.usage.input_tokens` across the codebase. One write site.

2. **Always preserve head + tail.** First N messages anchor identity (system + opening). Last N anchor recency. Compression destroys the middle.

3. **Pre-flight compression is real.** When a user switches from a 1M-context model to a 200K-context one mid-session, the next API call would 400. Run a cheap estimate before the call; compress proactively.

4. **Engines can expose tools.** The agent calling `lcm_expand("kubernetes")` to fetch a sub-graph is just a tool call. Generalizes nicely.

5. **`update_model` is a separate method.** Switching models mid-session changes `context_length` and `threshold_tokens`. Don't make callers compute this.

---

## 6. Subsystem C: Provider Adapters

### WHAT
Two layers of abstraction so the agent loop never sees raw provider JSON:
- **`api_mode`**: a string flag selected per session (e.g. `anthropic_messages`, `chat_completions`, `codex_responses`, `bedrock_converse`)
- **Transport registry**: maps `api_mode` → class that knows how to call + normalize

### WHY
Every LLM provider has a different:
- Endpoint shape (`/v1/chat/completions` vs `/v1/messages` vs `/v1/responses`)
- Tool-call schema (OpenAI's `tool_calls` array vs Anthropic's `content` blocks)
- Streaming protocol (SSE format differences)
- Field names (`max_tokens` vs `max_output_tokens` vs `max_tokens_to_sample`)
- Reasoning representation (`thinking` blocks vs `reasoning_content` field vs `reasoning_details`)
- Auth scheme (Bearer / AWS SigV4 / OAuth / API key in URL)

But the agent loop only wants `(messages) → NormalizedResponse`.

### HOW

```python
# ─── Normalized types (the agent loop only ever sees these) ────────
@dataclass
class ToolCall:
    id: str
    function_name: str
    function_arguments: str          # JSON string, may need repair

@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0

@dataclass
class NormalizedResponse:
    content: str
    tool_calls: list[ToolCall]
    usage: Usage
    finish_reason: str               # 'stop' | 'tool_calls' | 'length' | 'content_filter'
    reasoning: str | None            # for display
    reasoning_content: str | None    # for sending back on next turn
    raw_provider_response: dict      # escape hatch

# ─── Transport contract ────────────────────────────────────────────
class Transport(ABC):
    @abstractmethod
    def build_request(self, api_messages: list, tools: list, **kwargs) -> dict: ...
    @abstractmethod
    def call(self, request: dict) -> dict: ...               # raw provider call
    @abstractmethod
    def normalize_response(self, raw: dict) -> NormalizedResponse: ...
    @abstractmethod
    def stream_call(self, request: dict): ...                # async generator of deltas

# ─── Registry (plugin pattern, side-effect-on-import) ──────────────
_REGISTRY: dict[str, type[Transport]] = {}
_discovered = False

def register_transport(api_mode: str, cls: type[Transport]):
    _REGISTRY[api_mode] = cls

def get_transport(api_mode: str) -> Transport | None:
    global _discovered
    if not _discovered:
        _discover_transports()
    cls = _REGISTRY.get(api_mode)
    return cls() if cls else None

def _discover_transports():
    global _discovered; _discovered = True
    import transports.anthropic    # side-effect: register_transport("anthropic_messages", ...)
    import transports.openai       # side-effect: register_transport("chat_completions", ...)
    import transports.codex        # side-effect: register_transport("codex_responses", ...)
    import transports.bedrock      # side-effect: register_transport("bedrock_converse", ...)

# ─── api_mode auto-detection (in Agent.__init__) ───────────────────
def detect_api_mode(provider, base_url, explicit) -> str:
    if explicit in {"chat_completions", "codex_responses", "anthropic_messages", "bedrock_converse"}:
        return explicit
    host = urlparse(base_url).hostname.lower() if base_url else ""
    if host == "api.anthropic.com" or base_url.endswith("/anthropic"):
        return "anthropic_messages"
    if host == "chatgpt.com" and "/backend-api/codex" in base_url.lower():
        return "codex_responses"
    if host == "api.x.ai":
        return "codex_responses"
    if host.startswith("bedrock-runtime."):
        return "bedrock_converse"
    return "chat_completions"
```

### Key decisions

1. **Two layers, not one.** *Transport* handles wire protocol + response shape. *Adapter* (a layer above) handles request kwargs + auth. Don't conflate.

2. **Auto-detect from base_url first, accept explicit override.** Users typo provider names; URLs are authoritative.

3. **Side-effect-on-import registration.** A new transport is one file. No central switch statement to edit.

4. **Eager-warm the transport cache in `__init__`.** Don't discover import errors mid-conversation. Call `get_transport(self.api_mode)` once at startup.

5. **`NormalizedResponse.raw_provider_response` is an escape hatch.** Some tool needs the provider's signed-reasoning blob? It can dig in. The 99% case stays clean.

6. **Tool call schema is `(id, name, arguments_as_json_string)`.** Always a string, never a parsed dict — JSON repair is the agent's job, not the transport's. Different transports normalize to this same shape.

---

## 7. Subsystem D: Tool Registry

### WHAT
Singleton dict of `{tool_name → ToolEntry}` populated at import time. Schema goes to the model; handler runs when the model calls it.

### WHY
- Models call functions by name; you need a lookup
- Tools need metadata (`max_result_size`, `is_async`, `requires_credential_check`)
- MCP can mutate the registry at runtime (new server connects → new tools appear)
- Plugins can register tools without editing core

### HOW

```python
@dataclass
class ToolEntry:
    name: str
    toolset: str                          # 'file', 'web', 'memory', ...
    schema: dict                          # JSON Schema sent to model
    handler: Callable[[dict, ...], str]   # MUST return a string (JSON usually)
    is_async: bool = False
    check_fn: Callable[[], bool] | None = None    # 'is API key configured?'
    max_result_size_chars: int | None = None
    emoji: str = "⚡"

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolEntry] = {}
        self._toolset_checks: dict[str, Callable] = {}
        self._toolset_aliases: dict[str, str] = {}
        self._lock = threading.RLock()           # MCP can mutate from another thread
        self._generation = 0                     # bumped on every mutation

    def register(self, name, toolset, schema, handler, **kwargs):
        with self._lock:
            self._tools[name] = ToolEntry(name, toolset, schema, handler, **kwargs)
            self._generation += 1

    def dispatch(self, name, args, **kwargs) -> str:
        entry = self.get_entry(name)
        if not entry:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            if entry.is_async:
                return run_async(entry.handler(args, **kwargs))
            return entry.handler(args, **kwargs)
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    def get_schemas_for_session(self, enabled_toolsets) -> list[dict]:
        """Return only schemas for tools whose toolset is enabled AND check_fn passes."""
        return [
            {"type": "function", "function": e.schema}
            for e in self._tools.values()
            if e.toolset in enabled_toolsets
            and (not e.check_fn or e.check_fn())
        ]

# ─── Tools self-register at import ──────────────────────────────
@register_tool("read_file", toolset="file", schema=READ_FILE_SCHEMA)
def read_file_handler(args, task_id=None):
    path = args["path"]
    if not is_safe_path(path):
        return json.dumps({"error": "path outside allowed roots"})
    with open(path) as f:
        return json.dumps({"content": f.read()})
```

### Key decisions

1. **Handlers return strings.** Always JSON. Errors are `{"error": "..."}`. No exceptions cross the boundary back to the agent loop. Consistent format → less branching in the loop.

2. **Lock + generation counter.** MCP servers can connect mid-session and dynamically add tools. Reads need a stable snapshot; writes need exclusivity; cached schema lists can invalidate on `generation` change.

3. **`check_fn` for runtime availability.** A `gmail_send` tool's schema shouldn't appear if `GMAIL_OAUTH_TOKEN` is missing. The model gets confused by tools it can't call.

4. **`toolset` grouping + enable/disable per session.** Telegram should not see `terminal`. CLI might. Per-session toolset filter is non-negotiable.

5. **`max_result_size_chars` is per-tool.** Web search returns 100KB; file read might return 10MB. Cap them differently before they balloon the context.

6. **Two dispatch paths in the agent.** Some tools need agent state (`memory_store`, `todo_store`, `delegate_to_subagent`) — handle inline. Stateless tools go through `registry.dispatch`. See `_invoke_tool` in Section 3.

---

## 8. Subsystem E: Execution Environments

### WHAT
A swappable sandbox for any tool that runs shell/code. Same interface for `local`, `docker`, `ssh`, `modal`, `daytona`, `singularity`, `vercel_sandbox`.

### WHY
- Telegram users shouldn't be able to `rm -rf /` on the server
- Research runs need reproducibility (Docker, Singularity)
- Long-running agent runs need cost-efficient serverless (Modal, Daytona hibernate-on-idle)
- Local is fast for trusted dev work

### HOW — the spawn-per-call model

> **Every command spawns a fresh `bash -c` process. A session snapshot (env vars, functions, aliases) is captured once at init and re-sourced before each command. CWD persists via in-band stdout markers (remote) or a temp file (local).**

This is the genius of the design. Read it twice.

```python
class BaseEnvironment(ABC):
    @abstractmethod
    def run(self, command: str, timeout: int = 60, workdir: str | None = None) -> CommandResult:
        """Execute `command` and return its result. Each call = fresh subprocess."""

    @abstractmethod
    def write_file(self, path: str, content: bytes): ...
    @abstractmethod
    def read_file(self, path: str) -> bytes: ...

    def _snapshot_session(self):
        """Capture env vars, shell functions, aliases ONCE at init.
        Stored as a string of bash directives to be re-sourced before each command."""
        return self.run("declare -p; declare -F; alias", _bootstrap=True).stdout

    def _resource_session(self, snapshot, command, cwd_marker):
        return f"""
        eval '{snapshot}'                              # restore env
        cd '{cwd}'                                     # restore CWD from prior call
        {command}
        echo "__CWD__$(pwd)__"                         # emit new CWD for next call
        """

class LocalEnvironment(BaseEnvironment):
    def __init__(self):
        self.session_snapshot = self._snapshot_session()
        self.cwd = os.getcwd()
        self.cwd_marker_file = "/tmp/hermes_cwd_<task_id>"

    def run(self, command, timeout=60, workdir=None):
        wrapped = self._resource_session(self.session_snapshot, command, self.cwd)
        proc = subprocess.run(["bash", "-c", wrapped], timeout=timeout, capture_output=True)
        # Parse CWD marker from output for next call
        m = re.search(r"__CWD__(.+?)__", proc.stdout.decode())
        if m: self.cwd = m.group(1)
        clean_stdout = re.sub(r"__CWD__.+?__", "", proc.stdout.decode())
        return CommandResult(stdout=clean_stdout, stderr=proc.stderr.decode(), exit_code=proc.returncode)
```

### Implementations

| Backend | What it is | When to use |
|---|---|---|
| `LocalEnvironment` | `bash -c` on host | Default; trusted dev |
| `DockerEnvironment` | `docker exec` into a long-lived container | Untrusted code, reproducibility |
| `SSHEnvironment` | `ssh host bash -c` | Remote VM |
| `SingularityEnvironment` | HPC-style container | Research clusters |
| `ModalEnvironment` | `modal.Function.remote()` | Serverless GPU, on-demand |
| `DaytonaEnvironment` | Daytona sandbox API | Hibernate-on-idle (~$0 when idle) |
| `VercelSandboxEnvironment` | Firecracker microVM | Untrusted agent code at scale |

### Key decisions

1. **No persistent shell.** Each command is its own `bash -c` process. Zero state leakage, no zombie processes, no shell-state bugs. The cost is a few ms per call — worth it.

2. **Snapshot + re-source instead of persistent shell.** You get the *feel* of a persistent shell (env vars set by `export FOO=bar` still work next call) without any of the failure modes.

3. **In-band CWD marker.** `echo "__CWD__$(pwd)__"` at the end of every wrapped command. Parse it out of stdout. The user sees the clean output; the agent maintains state.

4. **The factory picks based on config.** `TERMINAL_ENV=docker hermes ...` → DockerEnvironment. No code change.

5. **Tools call `env.run("...")` and don't care which backend.** Adding `RunPodEnvironment` is one file.

---

## 9. Subsystem F: Memory

### WHAT
Three independent layers, each with different lifetime and purpose:

| Layer | Storage | Lifetime | Updated by | Read by |
|---|---|---|---|---|
| **In-context** | `messages` list | This turn only | Agent loop builds it | The LLM, every API call |
| **Built-in memory** | `MEMORY.md` + `USER.md` files | Across sessions | `memory` tool calls | Injected into system prompt |
| **External memory provider** | Plugin (Honcho/Byterover/Hindsight/...) | Across sessions, queryable | Background review + provider sync | `prefetch_all()` per turn |

### WHY
- LLM has zero memory between API calls — you must rebuild context every time
- Some facts are durable user preferences (Layer 2)
- Some facts need rich query / dialectic / embedding-based recall (Layer 3)
- Multiple layers because they fail differently and you want redundancy

### HOW — built-in memory (Layer 2)

```python
class MemoryStore:
    """Hierarchical key-value memory persisted as Markdown files."""

    def __init__(self, memory_char_limit=2200, user_char_limit=1375):
        self.memory_path = hermes_home / "MEMORY.md"
        self.user_path = hermes_home / "USER.md"
        self.memory: dict[str, str] = {}
        self.user_profile: dict[str, str] = {}
        self.memory_char_limit = memory_char_limit
        self.user_char_limit = user_char_limit

    def load_from_disk(self):
        # Parse MEMORY.md and USER.md (simple section-based MD)
        ...

    def add(self, target: str, content: str):     # 'memory' | 'user_profile'
        ...

    def replace(self, target: str, old: str, new: str): ...
    def delete(self, target: str, content: str): ...

    def render_for_system_prompt(self) -> str:
        return f"""
        # YOUR MEMORY
        {self.memory_path.read_text()}

        # USER PROFILE
        {self.user_path.read_text()}
        """
```

Exposed as a tool:

```python
@register_tool("memory", toolset="memory", schema=MEMORY_SCHEMA)
def memory_tool(args, store):
    action = args["action"]   # 'add' | 'replace' | 'delete' | 'view'
    target = args["target"]   # 'memory' | 'user_profile'
    content = args["content"]
    if action == "add":
        return store.add(target, content)
    # ...
```

### HOW — external memory provider (Layer 3)

```python
class MemoryProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool: ...
    @abstractmethod
    def initialize(self, session_id, user_id, gateway_session_key, ...): ...
    @abstractmethod
    def prefetch_all(self, query: str) -> str: ...    # called once per turn
    @abstractmethod
    def get_tool_schemas(self) -> list[dict]: ...     # provider-specific tools
    @abstractmethod
    def handle_tool_call(self, name, args) -> str: ...
    @abstractmethod
    def on_memory_write(self, action, target, content, metadata): ...
    @abstractmethod
    def on_session_end(self): ...
    @abstractmethod
    def shutdown(self): ...

class MemoryManager:
    """Coordinates one active provider + bridges built-in memory writes to it."""
    def __init__(self):
        self.providers: list[MemoryProvider] = []
    def add_provider(self, p): self.providers.append(p)
    def prefetch_all(self, query): return "\n".join(p.prefetch_all(query) for p in self.providers)
    def has_tool(self, name): ...
    def handle_tool_call(self, name, args): ...
```

### Key decisions

1. **`prefetch_all` runs ONCE per turn, before the tool loop.** Result is cached. Reused on every iteration. Calling it per-iteration = 10x latency + cost.

2. **Memory snippet is injected into the USER MESSAGE at API-call time, never into stored history.**
   ```python
   for idx, msg in enumerate(messages):
       api_msg = msg.copy()
       if idx == user_idx:
           api_msg["content"] += "\n\n" + memory_snippet
       api_messages.append(api_msg)
   ```
   Why not the system prompt? Because that breaks the prefix cache. Every memory update would change the system prompt, invalidating the cache and doubling input cost. The user message is fresh every turn anyway.

3. **Built-in memory in the system prompt is ONLY the snapshot loaded at session start.** It updates on disk after `memory` tool calls, but the in-conversation system prompt stays the same (for cache stability). The next session reads the updated snapshot.

4. **`memory_write_origin` provenance.** Every write is tagged: `assistant_tool` (model called the tool), `background_review` (self-improvement fork), `user_explicit` (user said "remember this"). Lets the curator distinguish gospel from hunch.

5. **One external provider at a time.** Per-config selection. Don't mix Honcho + Byterover in one session — their stores diverge and you can't reason about correctness.

---

## 10. Subsystem G: Skills

### WHAT
A **skill** is a markdown file with YAML frontmatter, optionally bundled with `references/`, `templates/`, and `scripts/` directories. Skills are *how-to knowledge* the agent loads when relevant.

### WHY
- Memory captures *who the user is*. Skills capture *how to do this class of task*.
- They're triggered by description matching, not by tool calls. The agent loads them automatically.
- They form a curated library that grows with experience — but only with safeguards (see Sec 11).

### Skill file layout

```
~/.hermes/skills/
├── postgres/                      ← umbrella skill (class-level)
│   ├── SKILL.md                   ← required: frontmatter + body
│   ├── references/
│   │   ├── deadlock-debugging.md  ← session-specific detail / quoted research
│   │   └── rls-policies.md
│   ├── templates/
│   │   └── migration.sql          ← copy-and-modify starter
│   └── scripts/
│       └── check-locks.sh         ← agent runs this directly
└── react-debugging/
    └── SKILL.md
```

### SKILL.md format

```yaml
---
name: postgres
description: Debugging Postgres performance, deadlocks, slow queries, RLS policies.
                                          Triggered when user mentions postgres / pg / supabase performance.
state: active              # active | stale | archived
created_at: 2026-04-12T18:23:00Z
last_activity_at: 2026-05-13T09:15:00Z
created_by: agent          # agent | user
pinned: false              # if true, curator never archives
---

# Postgres Debugging Skill

## When to use
... triggers ...

## Approach
1. Always check `pg_stat_activity` first ...
2. ...

## Pitfalls
- The user prefers `EXPLAIN (ANALYZE, BUFFERS)` not `EXPLAIN ANALYZE` ...

## Files
- `references/deadlock-debugging.md` — full incident transcript
- `scripts/check-locks.sh` — instant lock inspector
```

### Key decisions

1. **Filesystem is the source of truth.** Skills are markdown files. Editable by humans with any editor. Diff-able. Git-able. No proprietary blob.

2. **Frontmatter `description` IS the trigger.** No vector search needed for the agent to find skills — they're auto-listed in the system prompt by description, and the model picks. Vector search can be added later for huge libraries.

3. **Umbrella > leaf.** The skill prompt explicitly enforces *class-level* naming. NOT `fix-pr-1234`. NOT `migration-error-on-tuesday`. The umbrella `postgres` accumulates `references/`, `templates/`, `scripts/` for each new lesson.

4. **Three support-file types, three semantics:**
   - `references/<topic>.md` — read-this content (transcripts, quoted docs, knowledge bank)
   - `templates/<name>.<ext>` — copy-and-modify starters
   - `scripts/<name>.<ext>` — re-runnable code the skill invokes
   Don't mix them. Each goes in its own dir.

5. **State machine: `active → stale → archived`** (with reactivation on use). Skills that haven't been used in N days fade automatically. Don't proliferate forever.

6. **`pinned: true` means the curator never touches it.** User says "this is gospel, keep it forever."

7. **`created_by: agent` vs `user`.** User-created skills get more deference from the curator. Agent-created skills can be consolidated/archived aggressively.

---

## 11. Subsystem H: Self-Improvement Loop

### WHAT
Three mechanisms that make the agent learn from its conversations:
- **In-turn nudges** that trigger after enough activity passes without organic learning
- **Background review fork** that runs on its own thread, with limited tools
- **Curator daemon** that runs daily, consolidates skills, prunes stale ones

### WHY
Without this, every session restarts with the same blind spots. With it (and with the anti-patterns to avoid), the agent gets *demonstrably* better at your specific workflow over weeks.

### HOW — nudge counters

```python
class Agent:
    def __init__(self, ...):
        self._memory_nudge_interval = 10        # user turns
        self._turns_since_memory = 0
        self._skill_nudge_interval = 10         # tool iterations
        self._iters_since_skill = 0

    def run_conversation(self, user_message, ...):
        self._turns_since_memory += 1

        should_review_memory = (self._turns_since_memory >= self._memory_nudge_interval)
        if should_review_memory:
            self._turns_since_memory = 0

        # ... main loop ...
        while ...:
            if "skill_manage" in valid_tool_names:
                self._iters_since_skill += 1
            # ... API call, tool exec ...

        # Inside the tool exec loop, reset nudges if the tool fired organically:
        # if function_name == "memory":      self._turns_since_memory = 0
        # if function_name == "skill_manage": self._iters_since_skill = 0

        # AFTER final response is delivered:
        should_review_skills = (self._iters_since_skill >= self._skill_nudge_interval)
        if should_review_skills:
            self._iters_since_skill = 0

        if final_response and (should_review_memory or should_review_skills):
            self._spawn_background_review(
                messages_snapshot=list(messages),
                review_memory=should_review_memory,
                review_skills=should_review_skills,
            )
```

### HOW — the background review fork

```python
def _spawn_background_review(self, messages_snapshot, review_memory, review_skills):
    import threading

    prompt = pick_review_prompt(review_memory, review_skills)

    def _run_review():
        try:
            with redirect_stdout(devnull), redirect_stderr(devnull):
                set_approval_callback(auto_deny_dangerous)        # safety
                review_agent = Agent(
                    model=self.model,
                    max_iterations=16,                            # short budget
                    quiet_mode=True,
                    api_mode=self.api_mode,
                    base_url=self.base_url,
                    api_key=self.api_key,
                    credential_pool=self._credential_pool,
                    parent_session_id=self.session_id,            # lineage
                    enabled_toolsets=["memory", "skills"],        # ONLY these
                )
                review_agent._memory_write_origin = "background_review"  # provenance
                review_agent._memory_store = self._memory_store           # SHARED
                review_agent._memory_nudge_interval = 0                   # no recursion
                review_agent._skill_nudge_interval = 0

                review_agent.run_conversation(
                    user_message=prompt,
                    conversation_history=messages_snapshot,
                )
        except Exception as e:
            logger.warning("background review failed: %s", e)

    threading.Thread(target=_run_review, daemon=True).start()
```

### HOW — the review prompts (THE WISDOM)

The prompts encode what to save and **what NOT to save**. This is the non-obvious part. Examples from the actual code:

**What to save (skill review):**
- User corrected your style/tone/format/verbosity → "Frustration is a FIRST-CLASS skill signal"
- Non-trivial technique, fix, workaround that a future session would benefit from
- A skill loaded this session turned out wrong → "Patch it NOW"

**What NOT to save (anti-patterns):**
- Environment-dependent failures (missing binaries, fresh-install errors, unconfigured credentials) → "The user can fix these — they are not durable rules"
- Negative claims about tools ("browser tools don't work") → "These harden into refusals the agent cites against itself for months after the actual problem was fixed"
- Session-specific transient errors that resolved → "If retrying worked, the lesson is the retry pattern, not the failure"
- One-off task narratives → "Not a class of work that warrants a skill"

**Preference order for where the lesson lives:**
1. Patch a skill loaded in this session (it was in play, it's the right one)
2. Update an existing umbrella via `skill_view` + `skill_manage patch`
3. Add a support file (`references/`, `templates/`, `scripts/`) under an existing umbrella
4. Create a new umbrella skill — only if no existing one covers the class. **Name must be class-level, never session-specific.**

### HOW — the curator daemon

Runs on a configurable cadence (default 24h). Two responsibilities:

**Mechanical state machine** (no LLM call):
```python
def apply_automatic_transitions(now=None):
    for skill in agent_created_skills():
        if skill.pinned: continue
        anchor = skill.last_activity_at or skill.created_at
        if anchor <= archive_cutoff and skill.state != "archived":
            skill.archive()
        elif anchor <= stale_cutoff and skill.state == "active":
            skill.state = "stale"
        elif anchor > stale_cutoff and skill.state == "stale":
            skill.state = "active"               # reactivated by use
```

**LLM consolidation pass** (forks an agent):
- Reads the full skill index
- Identifies near-duplicates and overlapping skills
- Merges them under umbrellas (e.g. three Postgres skills → one umbrella with three `references/` files)
- Has a **DRY-RUN mode** that produces a report for human review before mutating

### Key decisions

1. **Two separate counters (memory turns vs. skill iterations).** Memory tracks *what the user revealed about themselves*; skills track *what techniques emerged*. Different signals, different cadences.

2. **Review fires AFTER `final_response`.** User never waits for self-improvement.

3. **Review forks a NEW Agent instance.** Not a special "review mode." Reusing the same loop machinery means the review agent can call tools, retry, compress — all the same defenses.

4. **Forked agent gets `enabled_toolsets=["memory", "skills"]` only.** Can't accidentally shell out, browse the web, or send messages.

5. **stdout/stderr to /dev/null + auto-deny approval.** The review runs silently and can't be hijacked.

6. **Shared `_memory_store` reference.** The fork writes to the same place the next foreground turn will read from.

7. **`_memory_write_origin` provenance is permanent.** Curator can challenge background-review writes more aggressively than user-explicit ones.

8. **Anti-pattern list is bigger than the to-save list.** Saving the wrong thing is more harmful than saving nothing. The prompts spend more words on "don't save X" than on "save Y."

9. **Curator dry-run mode.** Mass-mutating the skill library is high-blast-radius. The dry-run produces a report; a separate `hermes curator run` (no `--dry-run`) applies it.

10. **No recursion.** Review agent has its own nudge intervals set to 0. A review never triggers another review.

---

## 12. Subsystem I: Streaming & Interrupts

### WHAT
Two modes: non-streaming (one HTTP call → full response) and streaming (SSE → token deltas). Both must be interruptible.

### WHY
- TUIs need to show the model thinking live
- TTS pipelines need to start synthesis mid-response
- A user sending a follow-up message MUST preempt the in-flight model call, not queue behind it

### HOW

```python
class Agent:
    def __init__(self, ...):
        self._interrupt_requested = False
        self._interrupt_message = None
        self._execution_thread_id = None

    def interrupt(self, message=None):
        """Called from another thread (CLI keypress, gateway new message)."""
        self._interrupt_requested = True
        self._interrupt_message = message
        # Optionally signal the executing thread to wake up

    def _interruptible_api_call(self, api_kwargs):
        """Non-streaming: poll for interrupt between request and response.
        Practical implementation: run the API call in a thread, poll interrupt flag."""
        future = thread_pool.submit(self._raw_api_call, api_kwargs)
        while not future.done():
            if self._interrupt_requested:
                future.cancel()                # may not actually cancel HTTP
                raise InterruptedError
            time.sleep(0.05)
        return future.result()

    def _interruptible_api_call_streaming(self, api_kwargs):
        for delta in self._raw_streaming_call(api_kwargs):
            if self._interrupt_requested:
                return                          # generator exits, connection closes
            if delta.text:
                self._stream_delta_callback(delta.text)
            if delta.reasoning:
                self._thinking_callback(delta.reasoning)
            if delta.tool_call:
                self._tool_gen_callback(delta.tool_call)
```

### Callback surface

```python
# All optional, all set by the surface (CLI/gateway/cron) at Agent init:
stream_delta_callback(delta_text)       # token-by-token output
thinking_callback(reasoning_text)       # chain-of-thought for display
reasoning_callback(reasoning_full)      # complete reasoning blob
tool_start_callback(name, args)         # spinner: "running tool X"
tool_progress_callback(name, snippet)   # streaming tool output
tool_complete_callback(name, result)    # final result + duration
clarify_callback(question, choices)     # interactive: ask user for input mid-turn
step_callback(api_call_idx, prev_tools) # gateway: emit "agent:step" event
status_callback(message)                # generic "still alive" pings
interim_assistant_callback(partial)     # gateway: show partial replies in chat
```

### Key decisions

1. **The agent doesn't OWN a UI.** It owns callbacks. CLI, gateway, web — each provides its own.

2. **Interrupts are best-effort.** You can't cancel an HTTP request mid-flight reliably. What you CAN do is stop reading the response and discard it. The agent's job is to detect interrupt → discard → return cleanly to the loop top.

3. **Per-thread interrupt scoping.** `_execution_thread_id` records which thread is running the loop. Cross-thread interrupts use this so a subagent's interrupt doesn't kill the parent.

4. **`clarify_callback` is special.** It blocks the agent loop waiting for user input. The CLI implements it with `input()`; the gateway implements it by sending the question to Telegram, then sleeping until the user replies, then continuing. Same agent code.

5. **`step_callback` is the gateway's hook into the loop.** After every API call, the gateway gets `(call_idx, [prev_tool_calls_and_results])`. It uses this to stream typing indicators, post intermediate messages, etc.

---

## 13. Subsystem J: Plugin Hooks

### WHAT
Named extension points where third-party code can run. Side-effect or return-value based.

### WHY
- Allows extending without forking
- Observability (a plugin sends every tool call to a tracing system)
- Modification (a plugin rewrites tool results before they're seen by the model)
- Blocking (a plugin says "no, don't run that command")

### The 12 hooks

| Hook | When | Plugin can |
|---|---|---|
| `on_session_start` | First message of a new session | Initialize state |
| `pre_llm_call` | Before each API call | Return `{"context": "..."}` to inject into user message |
| `pre_tool_call` | Before each tool dispatch | Return `{"block": "reason"}` to refuse the tool |
| `post_tool_call` | After tool returns | Observe (latency, result) |
| `transform_tool_result` | After tool returns | Return a new string to replace result |
| `on_memory_write` | After memory tool fires | Mirror to external store |
| `on_skill_change` | After skill_manage fires | Mirror to git, etc. |
| `on_compression` | After context compression | Log savings |
| `on_provider_switch` | After model switch | Reset state |
| `on_subagent_spawn` | When delegate_task forks | Track lineage |
| `on_interrupt` | When user interrupts | Cleanup |
| `on_session_end` | Last line of `run_conversation` | Flush, close DB |

### HOW

```python
_HOOKS: dict[str, list[Callable]] = {}

def register_hook(name: str, fn: Callable):
    _HOOKS.setdefault(name, []).append(fn)

def invoke_hook(name: str, **kwargs) -> list:
    results = []
    for fn in _HOOKS.get(name, []):
        try:
            results.append(fn(**kwargs))
        except Exception as e:
            logger.warning(f"hook {name} failed: {e}")    # FAIL OPEN
    return results

def get_pre_tool_call_block_message(tool_name, args, **kwargs) -> str | None:
    for r in invoke_hook("pre_tool_call", tool_name=tool_name, args=args, **kwargs):
        if isinstance(r, dict) and r.get("block"):
            return r["block"]
    return None
```

### Key decisions

1. **Hooks fail open.** A buggy plugin raising an exception MUST NOT kill the agent loop. Catch, log, continue.

2. **`pre_llm_call` injects into USER message, not system.** Same reasoning as memory injection — preserve prefix cache.

3. **`transform_tool_result` runs AFTER `post_tool_call`.** Observers see the original result; transformers can rewrite it. Order matters.

4. **`pre_tool_call` blocking is a `dict` return.** Not an exception. Exceptions are for bugs; blocks are policy. Different semantics.

5. **Hooks are single-process.** Don't try to do IPC inside a hook. If your plugin needs to call an external service, it should be fast (<100ms) or async.

---

## 14. Subsystem K: Multi-Surface Entry Points

### WHAT
Different ways the same `Agent.run_conversation` gets invoked: CLI, gateway (Telegram/Discord/Slack/...), MCP server, ACP server, cron job, batch trajectory generator.

### WHY
- One agent, many surfaces = consistent behavior across channels
- Session continuity across surfaces (start on Telegram, continue on CLI)
- Reuse: one fix to the agent loop helps all surfaces

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Surface layer (each owns its own I/O + lifecycle)              │
│  - CLI: prompt-toolkit REPL                                      │
│  - Gateway: long-running daemon, platform adapters               │
│  - MCP: stdio JSON-RPC server                                    │
│  - ACP: WebSocket server                                         │
│  - Cron: triggered by scheduler                                  │
│  - Batch: reads dataset, runs N agents in parallel               │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (constructs callbacks + calls)
┌──────────────────────────────────────────────────────────────────┐
│  Agent.run_conversation(user_message, history=...)              │
│  - shared by all surfaces                                        │
│  - reads/writes the SAME SessionDB                               │
│  - injects same memory, same skills                              │
└──────────────────────────────────────────────────────────────────┘
```

### Gateway specifics

The messaging gateway is the most complex surface. It has its own concerns:

```python
class GatewayRunner:
    def __init__(self):
        self.session_store = SessionStore()      # gateway-specific (platform, chat_id, user_id) → session_id
        self.platform_adapters = {
            "telegram": TelegramAdapter(),
            "discord": DiscordAdapter(),
            "slack": SlackAdapter(),
            # ...
        }
        for adapter in self.platform_adapters.values():
            adapter.bind(self.on_message)

    def on_message(self, platform, chat_id, user_id, content, attachments):
        # 1. Resolve session
        session_key = f"{platform}:{chat_id}:{user_id}"
        session_id = self.session_store.get_or_create(session_key)

        # 2. Load history
        history = session_db.get_messages(session_id)

        # 3. Build agent (fresh instance per inbound message in gateway mode)
        agent = Agent(
            session_id=session_id,
            platform=platform,
            user_id=user_id,
            chat_id=chat_id,
            ...
        )
        agent.step_callback = lambda i, prev: self.emit_typing(platform, chat_id)
        agent.tool_progress_callback = lambda *a: self.emit_progress(platform, chat_id, *a)

        # 4. Run
        result = agent.run_conversation(content, conversation_history=history)

        # 5. Deliver
        self.platform_adapters[platform].send_message(chat_id, result["final_response"])
```

### Platform adapter contract

```python
class BasePlatformAdapter(ABC):
    @abstractmethod
    def start_listening(self, on_message: Callable): ...
    @abstractmethod
    def send_message(self, chat_id, content, **kwargs): ...
    @abstractmethod
    def send_typing_indicator(self, chat_id): ...
    @abstractmethod
    def authenticate_chat(self, chat_id, user_id) -> bool: ...
    @abstractmethod
    def split_long_message(self, content, max_len) -> list[str]: ...
    @abstractmethod
    def render_markdown(self, md: str) -> str: ...     # platform-specific MD dialect
```

### Key decisions

1. **Gateway creates a fresh Agent per inbound message.** Why not reuse? Because:
   - Telegram and Discord can deliver out-of-order with retries — stateful agents leak
   - Process restarts shouldn't lose conversations
   - Memory is in SessionDB anyway, not in the agent instance
   
   The cost is ~50ms of init. Worth it for correctness.

2. **Session key is `platform:chat_id:user_id`.** This is what enables "same conversation on different surfaces" — both CLI and Telegram bot can map to the same session_id via the user_id.

3. **Platform adapters own their own auth.** Telegram has chat_id allow-lists. Slack has bot tokens. Don't centralize auth at the gateway — let each adapter enforce its own.

4. **Markdown rendering varies per platform.** Telegram MarkdownV2 ≠ Discord MD ≠ Slack mrkdwn. Adapter responsibility.

5. **Long-message splitting per platform.** Telegram caps at 4096 chars, Discord at 2000, Slack at 40000. Adapter splits.

6. **Approval flows = inline keyboards.** Adapter renders `clarify_callback("Run rm -rf?", ["yes", "no"])` as Telegram inline buttons. Generic interface, platform-specific UI.

---

## 15. Subsystem L: Subagents (Delegation)

### WHAT
A tool that spawns a new Agent instance to handle a sub-task. Parent waits for child's final response, then continues.

### WHY
- Parallelism: spawn 5 subagents to research 5 topics simultaneously
- Context isolation: subagent has its own messages list, doesn't pollute parent
- Scoped tools: subagent can have a different toolset (e.g. "research" agent has web search but no shell)

### HOW

```python
@register_tool("delegate_task", toolset="meta", schema=DELEGATE_SCHEMA)
def delegate_task(args, parent_agent):
    goal = args["goal"]
    context = args.get("context", "")
    toolsets = args.get("toolsets")
    max_iterations = args.get("max_iterations")
    tasks = args.get("tasks")          # if list, parallel; else single

    if tasks:
        results = []
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(_spawn_one, parent_agent, goal, t, context, toolsets, max_iterations)
                       for t in tasks]
            for f in futures:
                results.append(f.result())
        return json.dumps({"results": results})
    else:
        return _spawn_one(parent_agent, goal, None, context, toolsets, max_iterations)

def _spawn_one(parent, goal, task, context, toolsets, max_iters):
    subagent = Agent(
        model=parent.model,
        api_mode=parent.api_mode,
        base_url=parent.base_url,
        api_key=parent.api_key,
        credential_pool=parent._credential_pool,
        parent_session_id=parent.session_id,           # lineage in SessionDB
        iteration_budget=parent.iteration_budget,      # SHARED budget!
        enabled_toolsets=toolsets,
        max_iterations=max_iters or parent.max_iterations,
        quiet_mode=True,
    )
    user_msg = f"{context}\n\nGoal: {goal}\n\n{task or ''}"
    result = subagent.run_conversation(user_msg)
    return result["final_response"]
```

### Key decisions

1. **Iteration budget is shared.** Parent and all descendants pull from the same `IterationBudget(90)`. A runaway subagent doesn't get to burn forever just because the parent had budget left.

2. **`parent_session_id` is recorded in SessionDB.** Forms a tree. Lets you visualize and debug.

3. **Subagent inherits parent's credentials, not env vars.** Re-resolving from env can fail for OAuth or credential-pool setups. Pass the live runtime explicitly.

4. **`quiet_mode=True`** so subagent output doesn't interleave with parent's stream.

5. **Parallel via ThreadPoolExecutor.** Cap concurrency at ~5 to avoid rate-limit cliffs.

6. **The subagent's return is just a string.** Parent appends it as a tool result. No special protocol.

7. **File-state registry.** If parent + subagent both edit `foo.py`, you need conflict detection. A registry keyed by `(task_id, path)` records who touched what.

---

## 16. Subsystem M: Cost & Billing

### WHAT
Per-session and per-call token + cost tracking, model pricing lookup, budget enforcement.

### WHY
- Users hit "why is this so expensive" pretty fast
- Different providers price tokens differently (cache_read is 10% of input, e.g.)
- Budget alerts prevent runaway spend
- RL training needs cost-per-trajectory

### HOW

```python
# Pricing table (loaded from disk, periodically refreshed from models.dev)
PRICING = {
    "anthropic/claude-opus-4.7": {
        "input": 15.00 / 1_000_000,         # $ per token
        "output": 75.00 / 1_000_000,
        "cache_read": 1.50 / 1_000_000,
        "cache_write": 18.75 / 1_000_000,
        "reasoning": 75.00 / 1_000_000,
    },
    # ...
}

def estimate_cost(model, usage: Usage) -> float:
    p = PRICING.get(model, PRICING["default"])
    return (
        usage.input_tokens * p["input"]
        + usage.output_tokens * p["output"]
        + usage.cache_read_tokens * p["cache_read"]
        + usage.cache_write_tokens * p["cache_write"]
        + usage.reasoning_tokens * p["reasoning"]
    )

# After every API call:
cost_delta = estimate_cost(self.model, response.usage)
session_db.update_session(self.session_id,
    input_tokens = session.input_tokens + response.usage.input_tokens,
    estimated_cost_usd = session.estimated_cost_usd + cost_delta,
    # ...
)

# Budget enforcement (config):
if session.estimated_cost_usd > self.cost_budget_usd:
    raise BudgetExceeded
```

### Key decisions

1. **Track cache tokens separately.** They're 10% the price of fresh input tokens. Lumping them together hides massive savings.

2. **`estimated` vs `actual`.** Estimated from pricing table. Actual reconciled later from provider billing API (often delayed). Show both.

3. **Per-session and per-call.** Some workloads want session-level budget; some want per-call.

4. **Pricing is data, not code.** A YAML/JSON file refreshed daily from models.dev. New models don't require a code change.

5. **Cost columns in `sessions` table.** Update after every API call. Don't recompute from messages on every UI query.

---

## 17. Hard-Won Defenses

These are the 15+ sanitization passes that run BEFORE every API call. Each one fixes a real production bug. If you skip these, you'll rediscover them painfully.

### Pre-API-call defenses (in order)

1. **Surrogate stripping** — Lone UTF-16 surrogates from Word/Google Docs paste crash JSON serialization. Strip before serializing.
   ```python
   text = re.sub(r"[\ud800-\udfff]", "", text)
   ```

2. **Tool-call argument repair** — Interrupted streams leave corrupt JSON in `tool_calls[i].function.arguments`. Attempt repair; if it fails, drop the arg and add a marker so the model knows to retry.

3. **Message alternation repair** — History wedged into `tool→user` or `user→user` (e.g. after compression bug) returns empty content from most providers. Detect and merge consecutive same-role messages.

4. **Orphaned tool-result removal** — A `role: tool` message without a matching `role: assistant` with that `tool_call_id` is an orphan. Strip or stub it.

5. **Drop thinking-only assistant turns** — Anthropic 400s if the last block of an assistant message is a `thinking` block. Drop assistant turns with no content/tool_calls AND merge adjacent user messages.

6. **Strip provider-specific fields** — Mistral/Fireworks reject unknown fields. Strip `call_id`, `response_item_id`, `_thinking_prefill`, `reasoning_details` for strict providers.

7. **Whitespace normalization** — `content.strip()` on every message. KV-cache hit rates depend on byte-exact prefixes.

8. **Tool-call JSON sorting** — `json.dumps(args, sort_keys=True, separators=(",", ":"))` so `{"a":1,"b":2}` and `{"b":2,"a":1}` produce the same bytes.

9. **Anthropic cache breakpoints** — Inject `cache_control: {"type": "ephemeral"}` on system message and last 3 message boundaries. ~75% input cost reduction on multi-turn.

10. **Dead TCP cleanup** — Pre-turn check for zombie sockets from prior provider outages. Force-close them so the next call doesn't hang.

11. **Pending /steer drain** — User typed `/steer be brief` while the model was thinking. Inject into the last tool message before the next API call.

12. **Reasoning content copy** — Moonshot/DeepSeek need `reasoning_content` sent back. Copy from stored `reasoning_details` into the API copy.

13. **Empty-content retry counter** — Some providers return empty content occasionally. Retry up to N times (different N per provider).

14. **Length-continue retry** — If `finish_reason == "length"` and the response was clearly truncated mid-tool-call, prefix the next call with the partial output.

15. **Codex incomplete-response retry** — OpenAI Codex Responses API has its own truncation modes. Detect + retry.

### General principles

1. **Defense in depth.** Sanitize on entry, sanitize before every API call, sanitize after parsing the response. Each layer catches what the others miss.

2. **Repair, don't reject.** A corrupt tool-call argument shouldn't kill the conversation. Try to repair; if you can't, drop the arg with a marker so the model retries cleanly.

3. **Log everything you sanitize.** When the same sanitization fires 50 times in a row, that's the signal of a deeper bug.

4. **Sanitize the API copy, not the persisted history.** Replays must reproduce the exact bytes. Sanitization is request-time only.

---

## 18. Wire Format Contracts

### Message schema (OpenAI-flavored, transport-normalized)

```typescript
type Message =
  | { role: "system";    content: string }
  | { role: "user";      content: string | ContentBlock[] }
  | { role: "assistant"; content: string | null;
                          tool_calls?: ToolCall[];
                          reasoning?: string;
                          reasoning_content?: string;        // for provider replay
                          reasoning_details?: Signed[];      // provider-specific
                          finish_reason?: string }
  | { role: "tool";      tool_call_id: string;
                          name?: string;
                          content: string }                  // ALWAYS string (JSON usually)

type ContentBlock =
  | { type: "text"; text: string }
  | { type: "image_url"; image_url: { url: string } }
  | { type: "input_audio"; input_audio: { data: string; format: string } }

type ToolCall = {
  id: string;
  type: "function";
  function: { name: string; arguments: string }   // arguments is a JSON STRING
}
```

### Tool schema (JSON Schema)

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read a file from disk. Returns content as string.",
    "parameters": {
      "type": "object",
      "properties": {
        "path": { "type": "string", "description": "Absolute path" },
        "start_line": { "type": "integer", "default": 1 },
        "max_lines": { "type": "integer", "default": 1000 }
      },
      "required": ["path"]
    }
  }
}
```

### Normalized response (from transport)

```python
@dataclass
class NormalizedResponse:
    content: str | None
    tool_calls: list[ToolCall]
    usage: Usage
    finish_reason: str
    reasoning: str | None
    reasoning_content: str | None
    reasoning_details: list | None
    raw_provider_response: dict
```

### Streaming delta

```python
@dataclass
class StreamDelta:
    text: str | None
    reasoning: str | None
    tool_call_partial: dict | None       # {"index": 0, "function": {"arguments": "..."}}
    finish_reason: str | None
    usage: Usage | None                  # only on final delta
```

### Key decisions

1. **`tool_calls[i].function.arguments` is a STRING.** Not a parsed dict. The agent does the parsing (with repair). This matches the OpenAI wire format.

2. **`role: "tool"` content is a STRING.** Even if your handler returns a dict, serialize to JSON before appending. Models reason better about consistent shapes.

3. **`reasoning` vs `reasoning_content` vs `reasoning_details`.** Three columns because:
   - `reasoning` is for *display* (the user sees it)
   - `reasoning_content` is for *provider replay* on the next turn (Moonshot needs this)
   - `reasoning_details` is *signed/structured* (OpenRouter, Anthropic thinking blocks)

4. **Empty content → `null`, not `""`.** Some providers distinguish. Mirror their convention.

---

## 19. Configuration Surface

What needs to be configurable. Don't bury these as constants.

```yaml
# config.yaml
agent:
  model: anthropic/claude-opus-4.7
  base_url: ""                           # auto-detect if empty
  api_key_env: ANTHROPIC_API_KEY
  api_mode: auto                         # auto | chat_completions | anthropic_messages | ...
  max_iterations: 90                     # tool-call iterations per turn
  tool_delay: 1.0                        # seconds between sequential tool calls
  max_tokens: null                       # provider default
  reasoning_config:
    effort: medium                       # none | low | medium | high
  service_tier: null                     # priority routing on OpenAI
  prompt_caching: auto
  tool_use_enforcement: auto

context:
  engine: compressor                     # compressor | lcm | <custom>
  threshold_percent: 0.75
  protect_first_n: 3
  protect_last_n: 6

memory:
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
  nudge_interval: 10                     # user turns
  provider: ""                           # honcho | byterover | hindsight | ""

skills:
  creation_nudge_interval: 10            # tool iterations
  stale_after_days: 30
  archive_after_days: 90

curator:
  enabled: true
  interval_hours: 24
  min_idle_hours: 1.0
  dry_run_first: true

cost:
  session_budget_usd: 5.00
  per_call_budget_usd: 0.50

terminal:
  env: local                             # local | docker | ssh | modal | daytona | ...
  sandbox_dir: ~/.hermes/sandboxes
  modal_mode: direct                     # direct | nous_managed

toolsets:
  enabled: [file, web, terminal, memory, skills, todo]
  disabled: []
  per_platform:
    telegram: [file, web, memory, skills, todo]   # no terminal!
    cli: [file, web, terminal, memory, skills, todo, browser]
```

### Key decisions

1. **Per-platform toolset overrides.** Don't expose `terminal` over Telegram unless the user is a power user and explicitly opted in.

2. **`api_mode: auto` with explicit override.** 90% of users never need to know it exists.

3. **Cost budgets are real config.** Not just nice-to-have.

4. **Nudge intervals are config, not code.** Some users want skill nudges every 5 iterations; some want 50.

---

## 20. Build Order

If you're starting from zero and want to ship something useful in a week, build in this order. Each step is testable on its own.

### Week 1: A working agent

1. **Day 1: Provider transport + normalized response** (Section 6)
   Pick ONE provider. Get `messages → NormalizedResponse` working. Hard-code the API mode. No registry yet.

2. **Day 2: Tool registry + ONE tool** (Section 7)
   Pick `read_file`. Get registration + dispatch working.

3. **Day 3: The core loop** (Section 3, just phases 6a–6g)
   No memory, no compression, no streaming. Just the while-loop with tool calls.

4. **Day 4: Session store** (Section 4)
   SQLite. Schema. Load history, save messages.

5. **Day 5: 5 more tools** (file ops, shell-local, web search, list_files, todo)
   Get a feel for handler patterns. Don't worry about sandboxing yet — assume local.

6. **Day 6: Streaming + interrupts** (Section 12)
   Add `stream_callback`. Add a Ctrl-C handler.

7. **Day 7: Polish** — CLI surface that wraps it all.

### Week 2: Production-grade

8. **Day 8: Context engine** (Section 5) — token tracking, simple compression.
9. **Day 9: System-prompt caching** (Section 3 key decision #1, Section 17 #9).
10. **Day 10: Sanitization passes** (Section 17) — at least the first 8.
11. **Day 11: Plugin hooks** (Section 13) — pre/post tool call, on_session_start/end.
12. **Day 12: Execution environments** (Section 8) — abstract `LocalEnvironment`, add `DockerEnvironment`.
13. **Day 13: Multi-provider** — transport registry, api_mode auto-detection.
14. **Day 14: Memory** (Section 9) — built-in MEMORY.md, basic injection.

### Week 3: Self-improvement + scale

15. **Day 15: Skills** (Section 10) — SKILL.md format, auto-listing in system prompt.
16. **Day 16: Subagents** (Section 15) — delegate_task tool, shared iteration budget.
17. **Day 17: Self-improvement loop** (Section 11) — nudge counters, background review fork.
18. **Day 18: The review prompts** — the wisdom (the anti-pattern list).
19. **Day 19: Curator daemon** — state machine, dry-run mode.
20. **Day 20: Multi-surface** (Section 14) — gateway, one platform adapter.
21. **Day 21: Cost tracking** (Section 16).

### Week 4: Hardening

22. Remaining sanitization passes.
23. External memory provider plugin (Honcho or your choice).
24. More platform adapters (Discord, Slack).
25. MCP server surface.
26. Trajectory recording for RL training.
27. Performance: connection pooling, prompt cache tuning, KV-cache normalization.

### Skip on first iteration

- Streaming (use non-streaming until you need TTS)
- LCM context engine (compressor is enough)
- Vector search over skills (description matching is enough until you have 100+ skills)
- Curator (run manual review for the first month)
- Reasoning model integrations beyond one

---

## 21. Anti-Patterns to Avoid

These are the failure modes people hit when building this. Learn from them.

### Architecture anti-patterns

1. **Storing state on the Agent instance instead of in the session store.**
   The agent should be reconstructible from `(session_id, config)`. Anything not durable IS lost on restart. Don't be surprised when a gateway restart loses conversations.

2. **Injecting memory into the system prompt instead of the user message.**
   Breaks Anthropic prefix caching. Doubles input token cost. Memory updates every turn → cache invalidates every turn → no savings ever.

3. **Persistent shells.**
   "Let's just keep a bash session open per agent." Then a runaway command hangs forever. Then env state leaks across turns. Then the process count explodes. Use spawn-per-call (Section 8).

4. **Calling memory `prefetch_all` per tool iteration.**
   10 iterations = 10x latency + cost. Cache it for the turn.

5. **One giant `model_dispatcher.py` switch statement.**
   New provider = new code change in 5 files. Use the transport registry (Section 6).

6. **Mutating `messages` for the API call.**
   Replays show injections as if the user typed them. Always copy.

### Self-improvement anti-patterns

7. **Saving environment-dependent failures as memory.**
   "MEMORY: file_read doesn't work on Tuesdays." Future-you cites this against itself for months. Don't.

8. **Saving negative claims about tools.**
   "MEMORY: browser tools are broken." Then the user actually fixes the browser, and the agent refuses to use it. Don't save negatives.

9. **Saving session-specific narratives as skills.**
   `fix-pr-1234-supabase-migration.md` is not a skill. `supabase` is. Use umbrellas.

10. **Letting the review agent run unbounded tools.**
    Background review can ONLY call memory + skills tools. If it can call shell, it can `rm -rf`. If it can browse, it can leak secrets. Lock it down (Section 11).

11. **Letting the review agent's output go to the user.**
    Stdout/stderr to /dev/null. The user wants their answer, not a status report on self-improvement.

12. **Running the review BEFORE delivering the final response.**
    User waits longer for nothing. AFTER `final_response` is set, ALWAYS.

13. **Reviews triggering reviews.**
    Review agent has `_memory_nudge_interval = 0`. Otherwise: stack overflow on a long conversation.

### Tool-call anti-patterns

14. **Letting tool handlers raise exceptions to the loop.**
    The loop is fragile enough without catching arbitrary errors. Handlers MUST return strings, even for errors. `json.dumps({"error": str(e)})`.

15. **Returning unbounded results.**
    A grep across a 50MB log returns 50MB to the model, which then truncates mid-stream. Cap per-tool with `max_result_size_chars`.

16. **Trusting tool arguments.**
    The model produces JSON. Sometimes corrupt JSON. Always parse with try/except and repair.

17. **Mixing sync and async tools without bridging.**
    `_run_async` (Section 7) bridges sync handler API to async implementations. Don't make the loop async — keep it sync, bridge inside the dispatcher.

### Streaming anti-patterns

18. **Updating the UI in the agent loop.**
    The loop knows nothing about UI. It exposes callbacks. UI lives in the surface layer (CLI/gateway/web).

19. **Trying to cancel HTTP mid-flight reliably.**
    You can't. Stop reading, drop the response, loop back. The provider may still bill you for the tokens; accept it.

### Provider anti-patterns

20. **Hardcoding one provider's quirks into the loop.**
    Every defensive pass should be transport-aware. Mistral rejects unknown fields → strip them ONLY for chat_completions transport, not anthropic.

21. **Caching responses indiscriminately.**
    Tool results depend on world state. Two `read_file` calls return different content. Don't cache them.

22. **Auto-retrying on every 4xx.**
    `400 invalid_request` will keep being invalid. Retry only on `429`, `5xx`, network errors.

### Memory anti-patterns

23. **Storing PII in memory without thought.**
    The user's password ends up in `MEMORY.md`. The agent reads it. The next turn echoes it back. Have an explicit allowlist of what memory can contain.

24. **Letting the model decide what to write to memory without guardrails.**
    See Section 11 anti-pattern list. The prompt MUST tell the model what NOT to save.

25. **Mixing built-in memory + external provider writes without a clear order.**
    Bridge built-in writes to the external provider, but make the bridge one-way. Otherwise circular update detection becomes its own bug.

### Skill anti-patterns

26. **No state machine.**
    Skills accumulate forever, the system prompt balloons, every turn is slow and expensive.

27. **No curator.**
    Same as above, but slower.

28. **Letting the curator run without dry-run on first deploy.**
    A bug in the consolidation prompt can nuke half your library. Dry-run, review, then apply.

29. **Embedding skills in code.**
    Skills are markdown files. Human-editable. Git-able. Diff-able. Don't put them in Python.

### Subagent anti-patterns

30. **Unbounded delegation depth.**
    Parent delegates to child, child delegates to grandchild, grandchild delegates to... cap at 3 levels deep AND share the iteration budget.

31. **Subagent re-resolving credentials from env.**
    OAuth refresh tokens that the parent already used become invalid. Pass the parent's live runtime explicitly.

32. **Concurrent file edits without registry.**
    Parent edits `foo.py`, subagent edits `foo.py`. Whoever writes last wins. Use a file-state registry to detect.

---

## Appendix: The 30-second pitch (for product folks)

> *We built an LLM-based agent that learns from every conversation. After each turn, it asks itself "did I just learn something durable about this user or this class of task?" If yes, it writes it down — to a memory file or as a new skill in a library. The next conversation starts already knowing what the previous one taught it.*
>
> *To keep this safe at scale, we have anti-poisoning guardrails (don't save environment failures or negative tool claims), a state machine that decays unused skills, and a daily curator that consolidates duplicates into umbrellas. Every change is provenance-tagged and reversible.*
>
> *The agent works the same way across CLI, Telegram, Slack, Discord, Email, and an MCP server. One conversation can continue across surfaces. It runs anywhere — local, Docker, serverless, RL eval clusters.*

## Appendix: References to the real code

If you want to read the actual implementation that this boilerplate distills:

| Concept here | File in hermes-agent |
|---|---|
| Core loop | `run_agent.py` → `AIAgent.run_conversation` (line ~11410) |
| Session store schema | `hermes_state.py` (lines 186–265) |
| Context engine ABC | `agent/context_engine.py` |
| Transport registry | `agent/transports/__init__.py` |
| Tool registry | `tools/registry.py` |
| Sandbox base | `tools/environments/base.py` |
| Built-in memory | `tools/memory_tool.py` |
| External memory mgr | `agent/memory_manager.py` |
| Self-improvement nudges | `run_agent.py` lines 1888–1998, 11610, 11892, 15129 |
| Background review fork | `run_agent.py` `_spawn_background_review` (line 4117) |
| Review prompts | `run_agent.py` `_MEMORY_REVIEW_PROMPT`, `_SKILL_REVIEW_PROMPT`, `_COMBINED_REVIEW_PROMPT` (line 3871+) |
| Curator daemon | `agent/curator.py` |
| Gateway runner | `gateway/run.py` `GatewayRunner` |
| Telegram adapter | `gateway/platforms/telegram.py` |
| Subagent spawning | `tools/delegate_tool.py` |
| Sanitization passes | `run_agent.py` lines 11951–12108 |

---

*This document is a living spec. Update it when you discover a new anti-pattern or load-bearing decision in your own implementation. The wisdom in Section 11 (anti-patterns the review agent must avoid) is the hardest-won part — extend it as you ship.*
