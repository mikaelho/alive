NOTES
=====

## PyView Key Concepts

PyView implements the Phoenix LiveView paradigm for Python:
- Server holds all state, browser renders HTML
- WebSocket connection enables real-time bidirectional updates
- Only changed DOM parts are sent to clients

### Lifecycle

1. **HTTP Request**: `mount()` called with unconnected socket
2. **WebSocket Connection**: `mount()` called again with connected socket
3. **Event Handling**: User interactions trigger `handle_event()`
4. **Real-time Updates**: Pub/sub messages trigger `handle_info()`

Use `is_connected(socket)` to check if WebSocket is established (for subscriptions, scheduling).

### Pub/Sub for Multi-Client Sync

```python
# Subscribe during mount
if is_connected(socket):
    await socket.subscribe("cards")

# Broadcast changes
await socket.broadcast("cards", {"action": "update", "data": ...})

# Receive in handle_info
async def handle_info(self, event: InfoEvent, socket):
    if event.name == "cards":
        # Update local context from event.payload
```

### Event Handling

HTML attributes:
- `phx-click="event_name"` - button clicks
- `phx-change="event_name"` - input changes
- `phx-submit="event_name"` - form submissions
- `phx-blur`, `phx-focus`, `phx-keyup` - other interactions
- `phx-value-*` - pass data with events

### Templates

- Jinja2-like syntax in `.html` files
- Auto-discovered when in same directory as LiveView class
- Variables: `{{variable}}`
- Loops: `{% for item in items %}...{% endfor %}`
- Conditionals: `{% if condition %}...{% endif %}`

---

## Architecture Decisions

### Shared State Model

Global state object containing:
- `cards`: List of card dicts with `id`, `title`, `content`
- `edit_locks`: Dict mapping `(card_id, field)` -> `session_id`

### Conflict Detection Flow

1. User clicks to edit a field
2. Server checks `edit_locks` for existing lock
3. If locked by another session: reject, exit edit mode
4. If unlocked: acquire lock, broadcast lock state to all clients
5. On save/cancel: release lock, broadcast update

### Component Behavior

**Text Field:**
- Display mode: renders markdown as HTML (server-side using `markdown` library)
- Edit mode: shows raw markdown in input
- Tracks edit state per client (local) + lock state (shared)

**Card:**
- Uses text field for title and text area for content
- Each field independently editable

**Card List:**
- Up/down buttons for reordering
- Reorder broadcasts new order to all clients
- Edit state follows card identity, not position

---

## Tech Stack

- Python 3.14 (enables t-string templates if needed)
- PyView for LiveView functionality
- `markdown` library for server-side rendering
- Minimal project structure (no cookiecutter)

---

## Open Questions (Resolved)

| Question | Answer |
|----------|--------|
| State persistence | In-memory for now |
| Real-time mechanism | PyView handles WebSockets |
| Markdown rendering | Server-side with `markdown` lib |
| Conflict handling | Exit edit mode on conflict |
| Reorder UI | Up/down buttons |
| User identification | None for now |
| Page structure | Single shared page |
