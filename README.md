# GraphAlgoViz

**Step‑by‑step graph algorithm visualization with clean architecture.**

---

## About

GraphAlgoViz is a desktop application for creating and visualizing graphs, with support for running algorithms step by step. The project is in early development, so the feature set and direction may evolve over time.

The goal is to keep the core graph logic and algorithms independent of the user interface, making the codebase easy to test and extend.

---

## Planned Features

- Interactive graph editing (add/remove nodes and edges, drag to reposition).
- Automatic graph layouts.
- Step‑by‑step execution of graph algorithms with visual feedback.
- Playback controls: play, pause, step forward, adjust speed.
- Save and load graph projects.

---

## Architecture

The project follows **Clean Architecture** principles and is organized into four layers:

- **Domain** – core entities and interfaces, no external dependencies.
- **Application** – use cases, services, and algorithm implementations.
- **Infrastructure** – concrete repositories, UI, rendering, and animation.
- **Presentation** – user interface and controllers.

---

## Project Structure

```
src/
├── domain/           # Core entities and interfaces
├── application/      # Use cases, services, algorithms
├── infrastructure/   # Repositories, UI, rendering, animation
├── presentation/     # Controllers and views
└── main.py           # Entry point
```

---

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/null-route-dev/GraphAlgoViz.git
   cd GraphAlgoViz
   ```
2. Create and activate a virtual environment (recommended).
3. Install dependencies (see `requirements.txt`).
4. Run the application:
   ```bash
   python main.py
   ```

---

## Status

Early development. APIs, structure, and features are subject to change.

---

## License

MIT License – see [LICENSE](LICENSE) for details.
