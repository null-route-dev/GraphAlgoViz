"""Main application window."""

import copy
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QToolBar,
)

from application.algorithms.registry import AlgorithmRegistry
from application.algorithms.step_result import StepResult
from application.csv_export import export_csv
from application.csv_import import CsvFormatError, import_csv
from application.examples import all_examples, find_example
from application.generators import generate
from application.history import EditHistory, GraphState, snapshot
from application.project_storage import ProjectStorage, ProjectStorageError
from application.services.layout_service import LayoutService
from application.statistics import compute_statistics
from application.use_cases.add_edge import AddEdgeUseCase
from application.use_cases.add_node import AddNodeUseCase
from application.use_cases.remove_edge import RemoveEdgeUseCase
from application.use_cases.remove_node import RemoveNodeUseCase
from application.use_cases.update_edge import UpdateEdgeUseCase
from application.use_cases.update_node import UpdateNodeUseCase
from domain.entities.edge import Edge
from domain.entities.node import Node
from domain.interfaces.graph_repository import GraphRepository
from domain.value_objects.position import Position
from infrastructure.animation.algorithm_animator import AlgorithmAnimator
from infrastructure.settings import AppSettings
from infrastructure.ui.algorithm_panel import AlgorithmPanel, AlgorithmState
from infrastructure.ui.dialogs.edge_attributes_dialog import (
    EdgeAttributesDialog,
)
from infrastructure.ui.dialogs.generate_graph_dialog import (
    GenerateGraphDialog,
)
from infrastructure.ui.dialogs.node_attributes_dialog import (
    NodeAttributesDialog,
)
from infrastructure.ui.dialogs.statistics_dialog import StatisticsDialog
from infrastructure.ui.graph_canvas import (
    ClickEvent,
    ContextEvent,
    GraphCanvas,
    SelectionEvent,
)
from infrastructure.ui.inspector_panel import InspectorPanel
from infrastructure.ui.interaction_mode import InteractionMode
from infrastructure.ui.matrix_view import MatrixView
from infrastructure.ui.theme import apply_theme

MESSAGE_TIMEOUT_MS = 2000
DEFAULT_SPEED = 5
BASE_INTERVAL_MS = 1000

PROJECT_FILTER = "GraphAlgoViz project (*.gaviz);;All files (*)"
PROJECT_SUFFIX = ".gaviz"

CSV_FILTER = "CSV file (*.csv);;All files (*)"
CSV_SUFFIX = ".csv"

EXPORT_FILTER = (
    "PNG image (*.png);;"
    "SVG image (*.svg);;"
    "PDF document (*.pdf);;"
    "JPEG image (*.jpg *.jpeg);;"
    "All files (*)"
)
EXPORT_EXTENSIONS = (".png", ".svg", ".pdf", ".jpg", ".jpeg")
DEFAULT_EXPORT_SUFFIX = ".png"
EXPORT_DPI = 200

UNSAVED_TITLE = "Unsaved changes"
UNSAVED_TEXT = "The project has unsaved changes. Save them before continuing?"

APP_NAME = "GraphAlgoViz"
APP_VERSION = "0.1.0"
ABOUT_TITLE = f"About {APP_NAME}"
ABOUT_TEXT = (
    f"<h3>{APP_NAME} {APP_VERSION}</h3>"
    "<p>Interactive graph editor with step-by-step algorithm "
    "visualization.</p>"
    "<p>Built with Clean Architecture: domain, application, "
    "infrastructure, presentation.</p>"
    "<p>Licensed under the MIT License.</p>"
)

DEFAULT_DARK = True

GRID_SIZE = 0.05
PASTE_OFFSET = 0.05

MODE_SHORTCUTS: dict[InteractionMode, str] = {
    InteractionMode.SELECT: "1",
    InteractionMode.ADD_NODE: "2",
    InteractionMode.ADD_EDGE: "3",
    InteractionMode.DELETE: "4",
}

SHORTCUT_DUPLICATE = "Ctrl+D"
SHORTCUT_RENAME = "F2"
SHORTCUT_SNAP = "Ctrl+G"
SHORTCUT_RUN = "F5"


def _snap(value: float) -> float:
    """Round a coordinate to the nearest grid point.

    Args:
        value: The coordinate to snap.

    Returns:
        The nearest multiple of GRID_SIZE.
    """
    return round(value / GRID_SIZE) * GRID_SIZE


def _resolve_export_path(path: Path) -> Path:
    """Return the export path with a supported image extension.

    Args:
        path: The path chosen by the user.

    Returns:
        A path with a supported image extension.
    """
    if path.suffix.lower() in EXPORT_EXTENSIONS:
        return path
    return path.with_suffix(DEFAULT_EXPORT_SUFFIX)


def _ensure_csv_suffix(path: Path) -> Path:
    """Append the .csv suffix when it is missing.

    Args:
        path: The path chosen by the user.

    Returns:
        The path, with .csv appended if it did not have it.
    """
    if path.suffix.lower() == CSV_SUFFIX:
        return path
    return path.with_suffix(CSV_SUFFIX)


ClipboardData = tuple[list[Node], list[Edge]]


class MainWindow(QMainWindow):
    """Top-level window hosting the canvas, toolbar, and docks.

    The window owns the interaction mode, node positions, edit
    history, selection, clipboard, theme, snap-to-grid flag, edge
    display options, and algorithm state. Every mutation is followed
    by a history commit.
    """

    def __init__(
        self,
        repository: GraphRepository,
        layout_service: LayoutService,
        registry: AlgorithmRegistry,
        storage: ProjectStorage,
        settings: AppSettings,
        add_node_use_case: AddNodeUseCase,
        add_edge_use_case: AddEdgeUseCase,
        remove_node_use_case: RemoveNodeUseCase,
        remove_edge_use_case: RemoveEdgeUseCase,
        update_edge_use_case: UpdateEdgeUseCase,
        update_node_use_case: UpdateNodeUseCase,
        dark: bool = DEFAULT_DARK,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._layout_service = layout_service
        self._registry = registry
        self._storage = storage
        self._settings = settings
        self._add_node_use_case = add_node_use_case
        self._add_edge_use_case = add_edge_use_case
        self._remove_node_use_case = remove_node_use_case
        self._remove_edge_use_case = remove_edge_use_case
        self._update_edge_use_case = update_edge_use_case
        self._update_node_use_case = update_node_use_case

        self._positions = layout_service.circular(repository.get())
        self._mode = InteractionMode.SELECT
        self._pending_edge_source: int | None = None
        self._selected_nodes: set[int] = set()
        self._selected_edge: tuple[int, int] | None = None
        self._drag_node: int | None = None
        self._drag_click: tuple[float, float] | None = None
        self._drag_initial_positions: dict[int, Position] = {}
        self._drag_changed = False
        self._clipboard: ClipboardData | None = None
        self._algorithm_state = AlgorithmState.IDLE
        self._current_interval_ms = BASE_INTERVAL_MS // DEFAULT_SPEED
        self._current_path: Path | None = None
        self._dark = dark
        self._snap_to_grid = settings.snap_to_grid()
        self._bundle_parallel = settings.bundle_parallel_edges()
        self._arrow_at_middle = settings.arrow_at_middle()
        self._editing_enabled = True

        self._history = EditHistory(snapshot(repository.get(), self._positions))
        self._history.mark_saved()

        self.setWindowTitle(APP_NAME)
        self.resize(1100, 700)

        self._canvas = GraphCanvas(
            self,
            on_click=self._handle_canvas_click,
            on_context_menu=self._handle_context_menu,
            on_selection_complete=self._handle_selection_complete,
            on_drag_move=self._handle_canvas_drag_move,
            on_drag_end=self._handle_canvas_drag_end,
            dark=dark,
        )
        self._canvas.set_bundle_parallel(self._bundle_parallel)
        self._canvas.set_arrow_at_middle(self._arrow_at_middle)
        self.setCentralWidget(self._canvas)

        self._animator = AlgorithmAnimator(self)
        self._animator.step_ready.connect(self._on_step_ready)
        self._animator.finished.connect(self._on_algorithm_finished)

        self._mode_actions: list[QAction] = []
        self._view_menu: QMenu | None = None
        self._undo_action: QAction | None = None
        self._redo_action: QAction | None = None
        self._copy_action: QAction | None = None
        self._paste_action: QAction | None = None
        self._delete_action: QAction | None = None
        self._duplicate_action: QAction | None = None
        self._rename_action: QAction | None = None
        self._run_action: QAction | None = None
        self._snap_action: QAction | None = None
        self._bundle_action: QAction | None = None
        self._arrow_action: QAction | None = None
        self._build_menu()
        self._build_toolbar()
        self._build_status_bar()
        self._build_algorithm_panel()
        self._build_inspector_panel()
        self._build_matrix_panel()
        self._add_theme_action()
        self._refresh_canvas()
        self._sync_available_nodes()
        self._update_graph_stats()
        self._update_step_availability()
        self._refresh_action_states()
        self._refresh_inspector()

    @property
    def mode(self) -> InteractionMode:
        """The currently selected interaction mode.

        Returns:
            The active mode.
        """
        return self._mode

    def set_mode(self, mode: InteractionMode) -> None:
        """Switch the interaction mode.

        Args:
            mode: The mode to activate.
        """
        self._mode = mode
        self._pending_edge_source = None
        self._drag_node = None
        self._drag_click = None
        self._drag_changed = False
        if mode is not InteractionMode.SELECT:
            self._selected_nodes.clear()
            self._selected_edge = None
        self._restore_mode_message()
        self._refresh_canvas()
        self._refresh_inspector()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Confirm unsaved changes before closing the window.

        Args:
            event: The close event.
        """
        if self._confirm_discard_changes():
            event.accept()
        else:
            event.ignore()

    def _build_menu(self) -> None:
        """Create the menu bar."""
        file_menu = self.menuBar().addMenu("&File")

        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._handle_new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._handle_open_project)
        file_menu.addAction(open_action)

        import_csv_action = QAction("&Import CSV...", self)
        import_csv_action.triggered.connect(self._handle_import_csv)
        file_menu.addAction(import_csv_action)

        generate_action = QAction("&Generate Graph...", self)
        generate_action.triggered.connect(self._handle_generate_graph)
        file_menu.addAction(generate_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._handle_save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._handle_save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        export_action = QAction("&Export Image...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._handle_export_image)
        file_menu.addAction(export_action)

        export_csv_action = QAction("Export &CSV...", self)
        export_csv_action.triggered.connect(self._handle_export_csv)
        file_menu.addAction(export_csv_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        edit_menu = self.menuBar().addMenu("&Edit")

        self._undo_action = QAction("&Undo", self)
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo_action.triggered.connect(self._handle_undo)
        edit_menu.addAction(self._undo_action)

        self._redo_action = QAction("&Redo", self)
        self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_action.triggered.connect(self._handle_redo)
        edit_menu.addAction(self._redo_action)

        edit_menu.addSeparator()

        self._copy_action = QAction("&Copy", self)
        self._copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self._copy_action.triggered.connect(self._handle_copy)
        edit_menu.addAction(self._copy_action)

        self._paste_action = QAction("&Paste", self)
        self._paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        self._paste_action.triggered.connect(self._handle_paste)
        edit_menu.addAction(self._paste_action)

        self._duplicate_action = QAction("D&uplicate", self)
        self._duplicate_action.setShortcut(QKeySequence(SHORTCUT_DUPLICATE))
        self._duplicate_action.triggered.connect(self._handle_duplicate)
        edit_menu.addAction(self._duplicate_action)

        self._rename_action = QAction("&Rename", self)
        self._rename_action.setShortcut(QKeySequence(SHORTCUT_RENAME))
        self._rename_action.triggered.connect(self._handle_rename)
        edit_menu.addAction(self._rename_action)

        edit_menu.addSeparator()

        self._delete_action = QAction("&Delete Selected", self)
        self._delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        self._delete_action.triggered.connect(self._handle_delete_selected)
        edit_menu.addAction(self._delete_action)

        edit_menu.addSeparator()

        select_all_action = QAction("Select &All", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self._handle_select_all)
        edit_menu.addAction(select_all_action)

        edit_menu.addSeparator()

        self._run_action = QAction("R&un algorithm", self)
        self._run_action.setShortcut(QKeySequence(SHORTCUT_RUN))
        self._run_action.triggered.connect(self._handle_run_shortcut)
        edit_menu.addAction(self._run_action)

        self._view_menu = self.menuBar().addMenu("&View")

        examples_menu = self.menuBar().addMenu("E&xamples")
        for example in all_examples():
            action = QAction(example.display_name, self)
            action.setToolTip(example.description)
            action.triggered.connect(
                lambda checked=False, eid=example.id: self._handle_load_example(eid)
            )
            examples_menu.addAction(action)

        help_menu = self.menuBar().addMenu("&Help")

        about_action = QAction(f"&About {APP_NAME}", self)
        about_action.triggered.connect(self._handle_about)
        help_menu.addAction(about_action)

    def _build_toolbar(self) -> None:
        """Create the toolbar with mode-switching actions."""
        toolbar = QToolBar("Tools", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        group = QActionGroup(self)
        group.setExclusive(True)

        modes = (
            InteractionMode.SELECT,
            InteractionMode.ADD_NODE,
            InteractionMode.ADD_EDGE,
            InteractionMode.DELETE,
        )
        for mode in modes:
            action = QAction(mode.display_name, self)
            action.setCheckable(True)
            action.setChecked(mode is self._mode)
            shortcut = MODE_SHORTCUTS.get(mode)
            if shortcut is not None:
                action.setShortcut(QKeySequence(shortcut))
                action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            action.triggered.connect(lambda checked=False, m=mode: self.set_mode(m))
            group.addAction(action)
            toolbar.addAction(action)
            self._mode_actions.append(action)

    def _build_status_bar(self) -> None:
        """Create the status bar with mode and graph stats."""
        self._status_bar = self.statusBar()
        self._stats_label = QLabel("", self)
        self._stats_label.setContentsMargins(0, 0, 8, 0)
        self._status_bar.addPermanentWidget(self._stats_label)
        self._restore_mode_message()

    def _build_algorithm_panel(self) -> None:
        """Create the algorithm panel and dock it on the right."""
        self._panel = AlgorithmPanel(self._registry, self)
        self._panel.run_requested.connect(self._on_run_requested)
        self._panel.pause_requested.connect(self._on_pause_requested)
        self._panel.step_requested.connect(self._on_step_requested)
        self._panel.step_back_requested.connect(self._on_step_back_requested)
        self._panel.reset_requested.connect(self._on_reset_requested)
        self._panel.speed_changed.connect(self._on_speed_changed)

        self._algorithm_dock = QDockWidget("Algorithm", self)
        self._algorithm_dock.setWidget(self._panel)
        self._algorithm_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._algorithm_dock)
        if self._view_menu is not None:
            self._view_menu.addAction(self._algorithm_dock.toggleViewAction())

    def _build_inspector_panel(self) -> None:
        """Create the inspector panel and dock it on the right."""
        self._inspector = InspectorPanel(self)
        self._inspector.node_label_changed.connect(self._on_inspector_node_label)
        self._inspector.edge_weight_changed.connect(self._on_inspector_edge_weight)
        self._inspector.edge_directed_changed.connect(self._on_inspector_edge_directed)

        self._inspector_dock = QDockWidget("Inspector", self)
        self._inspector_dock.setWidget(self._inspector)
        self._inspector_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._inspector_dock)
        if self._view_menu is not None:
            self._view_menu.addAction(self._inspector_dock.toggleViewAction())

    def _build_matrix_panel(self) -> None:
        """Create the matrix view and dock it at the bottom."""
        self._matrix_view = MatrixView(self)
        self._matrix_dock = QDockWidget("Matrix", self)
        self._matrix_dock.setWidget(self._matrix_view)
        self._matrix_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._matrix_dock)
        self._matrix_dock.hide()
        if self._view_menu is not None:
            self._view_menu.addAction(self._matrix_dock.toggleViewAction())

    def _add_theme_action(self) -> None:
        """Add statistics and display toggles to the View menu."""
        if self._view_menu is None:
            return

        statistics_action = QAction("Statistics...", self)
        statistics_action.triggered.connect(self._handle_statistics)
        self._view_menu.addAction(statistics_action)

        self._view_menu.addSeparator()

        self._snap_action = QAction("Snap to grid", self)
        self._snap_action.setCheckable(True)
        self._snap_action.setChecked(self._snap_to_grid)
        self._snap_action.setShortcut(QKeySequence(SHORTCUT_SNAP))
        self._snap_action.triggered.connect(self._handle_toggle_snap)
        self._view_menu.addAction(self._snap_action)

        self._bundle_action = QAction("Bundle parallel edges", self)
        self._bundle_action.setCheckable(True)
        self._bundle_action.setChecked(self._bundle_parallel)
        self._bundle_action.triggered.connect(self._handle_toggle_bundle)
        self._view_menu.addAction(self._bundle_action)

        self._arrow_action = QAction("Arrow at middle", self)
        self._arrow_action.setCheckable(True)
        self._arrow_action.setChecked(self._arrow_at_middle)
        self._arrow_action.triggered.connect(self._handle_toggle_arrow)
        self._view_menu.addAction(self._arrow_action)

        self._view_menu.addSeparator()

        self._dark_theme_action = QAction("Dark theme", self)
        self._dark_theme_action.setCheckable(True)
        self._dark_theme_action.setChecked(self._dark)
        self._dark_theme_action.triggered.connect(self._handle_toggle_theme)
        self._view_menu.addAction(self._dark_theme_action)

    def _handle_toggle_theme(self, checked: bool) -> None:
        """Switch themes and persist the choice.

        Args:
            checked: True for dark, False for light.
        """
        self._dark = checked
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_theme(app, checked)
        self._canvas.set_dark(checked)
        self._settings.set_dark_theme(checked)
        self._refresh_canvas()

    def _handle_toggle_snap(self, checked: bool) -> None:
        """Enable or disable snap-to-grid.

        Args:
            checked: True to enable snapping.
        """
        self._snap_to_grid = checked
        self._settings.set_snap_to_grid(checked)

    def _handle_toggle_bundle(self, checked: bool) -> None:
        """Enable or disable bundling of parallel edges.

        Args:
            checked: True to enable bundling.
        """
        self._bundle_parallel = checked
        self._settings.set_bundle_parallel_edges(checked)
        self._canvas.set_bundle_parallel(checked)

    def _handle_toggle_arrow(self, checked: bool) -> None:
        """Move directed edge arrows to or from the midpoint.

        Args:
            checked: True to draw arrows at the middle.
        """
        self._arrow_at_middle = checked
        self._settings.set_arrow_at_middle(checked)
        self._canvas.set_arrow_at_middle(checked)

    def _handle_statistics(self) -> None:
        """Compute graph statistics and show them in a dialog."""
        stats = compute_statistics(self._repository.get())
        StatisticsDialog.show_stats(stats, self)

    def _restore_mode_message(self) -> None:
        """Show the current mode in the status bar."""
        self._status_bar.showMessage(f"Mode: {self._mode.display_name}")

    def _show_temporary_message(self, text: str) -> None:
        """Show a short-lived status bar message.

        Args:
            text: The message to display.
        """
        self._status_bar.showMessage(text)
        QTimer.singleShot(MESSAGE_TIMEOUT_MS, self._restore_mode_message)

    def _set_editing_enabled(self, enabled: bool) -> None:
        """Enable or disable editing, undo, redo, and paste.

        Args:
            enabled: True to allow editing, False to forbid it.
        """
        self._editing_enabled = enabled
        for action in self._mode_actions:
            action.setEnabled(enabled)
        self._refresh_action_states()

    def _refresh_action_states(self) -> None:
        """Update the enabled state of the Edit menu actions."""
        has_selection = bool(self._selected_nodes) or (self._selected_edge is not None)
        single_node = len(self._selected_nodes) == 1
        if self._undo_action is not None:
            self._undo_action.setEnabled(
                self._editing_enabled and self._history.can_undo()
            )
        if self._redo_action is not None:
            self._redo_action.setEnabled(
                self._editing_enabled and self._history.can_redo()
            )
        if self._copy_action is not None:
            self._copy_action.setEnabled(
                self._editing_enabled and bool(self._selected_nodes)
            )
        if self._paste_action is not None:
            self._paste_action.setEnabled(
                self._editing_enabled and self._clipboard is not None
            )
        if self._delete_action is not None:
            self._delete_action.setEnabled(self._editing_enabled and has_selection)
        if self._duplicate_action is not None:
            self._duplicate_action.setEnabled(
                self._editing_enabled and bool(self._selected_nodes)
            )
        if self._rename_action is not None:
            self._rename_action.setEnabled(self._editing_enabled and single_node)

    def _sync_available_nodes(self) -> None:
        """Update the panel's node lists from the current graph."""
        node_ids = [node.id for node in self._repository.get().nodes()]
        self._panel.set_available_nodes(node_ids)

    def _update_graph_stats(self) -> None:
        """Update the graph summary in the status bar."""
        graph = self._repository.get()
        nodes = graph.node_count
        edges = graph.edge_count
        self._stats_label.setText(f"Nodes: {nodes}   Edges: {edges}")

    def _update_step_availability(self) -> None:
        """Refresh the panel's step buttons."""
        self._panel.set_step_availability(
            can_step_back=self._animator.can_step_back,
            can_step_forward=self._animator.can_step_forward,
        )

    def _update_window_title(self) -> None:
        """Update the window title."""
        title = APP_NAME
        if self._current_path is not None:
            title = f"{title} - {self._current_path.name}"
        if self._history.is_dirty():
            title = f"{title} *"
        self.setWindowTitle(title)

    def _commit(self) -> None:
        """Snapshot the current state and push it to the edit history."""
        state = snapshot(self._repository.get(), self._positions)
        self._history.push(state)
        self._refresh_action_states()
        self._update_window_title()
        self._refresh_inspector()

    def _restore(self, state: GraphState) -> None:
        """Replace the live graph and positions with a snapshot.

        Args:
            state: The snapshot to restore.
        """
        self._repository.save(copy.deepcopy(state.graph))
        self._positions = dict(state.positions)
        self._pending_edge_source = None
        self._drag_node = None
        self._drag_click = None
        self._selected_nodes.clear()
        self._selected_edge = None
        self._drag_changed = False
        self._sync_available_nodes()
        self._update_graph_stats()
        self._refresh_canvas()
        self._refresh_action_states()
        self._update_window_title()
        self._refresh_inspector()

    def _refresh_inspector(self) -> None:
        """Update the inspector panel to match the current selection."""
        form = self._inspector._form
        row_count = form.rowCount()

        def set_rows(visible: tuple[int, ...]) -> None:
            for index in range(row_count):
                form.setRowVisible(index, index in visible)

        if self._selected_edge is not None:
            edge = self._find_edge(*self._selected_edge)
            if edge is None:
                self._inspector.show_nothing()
                return
            arrow = "\u2192" if edge.directed else "\u2014"
            self._inspector._header.setText(f"Edge {edge.source} {arrow} {edge.target}")
            self._inspector._edge_endpoints_label.setText(
                f"{edge.source} \u2192 {edge.target}"
            )
            self._inspector._edge_weight_spin.blockSignals(True)
            self._inspector._edge_weight_spin.setValue(edge.weight)
            self._inspector._edge_weight_spin.blockSignals(False)
            self._inspector._edge_directed_check.blockSignals(True)
            self._inspector._edge_directed_check.setChecked(edge.directed)
            self._inspector._edge_directed_check.blockSignals(False)
            self._inspector._node_id = None
            self._inspector._edge = (edge.source, edge.target)
            set_rows((3, 4, 5))
            return

        if len(self._selected_nodes) == 1:
            node_id = next(iter(self._selected_nodes))
            graph = self._repository.get()
            if not graph.has_node(node_id):
                self._inspector.show_nothing()
                return
            node = graph.node(node_id)
            degree = len(graph.neighbors(node_id))
            self._inspector._header.setText(f"Node {node_id}")
            self._inspector._node_id_label.setText(str(node_id))
            self._inspector._node_label_edit.blockSignals(True)
            self._inspector._node_label_edit.setText(node.label)
            self._inspector._node_label_edit.blockSignals(False)
            self._inspector._node_degree_label.setText(str(degree))
            self._inspector._node_id = node_id
            self._inspector._edge = None
            set_rows((0, 1, 2))
            return

        if len(self._selected_nodes) > 1:
            self._inspector._header.setText(
                f"{len(self._selected_nodes)} nodes selected"
            )
            self._inspector._node_id = None
            self._inspector._edge = None
            set_rows(())
            return

        self._inspector._header.setText("No selection")
        self._inspector._node_id = None
        self._inspector._edge = None
        set_rows(())

    def _handle_undo(self) -> None:
        """Undo the last committed change."""
        if not self._editing_enabled or not self._history.can_undo():
            return
        self._restore(self._history.undo())
        self._show_temporary_message("Undo")

    def _handle_redo(self) -> None:
        """Redo the last undone change."""
        if not self._editing_enabled or not self._history.can_redo():
            return
        self._restore(self._history.redo())
        self._show_temporary_message("Redo")

    def _handle_export_image(self) -> None:
        """Prompt for a destination and save the canvas as an image."""
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Export image", "", EXPORT_FILTER
        )
        if not path_str:
            return
        path = _resolve_export_path(Path(path_str))
        try:
            self._canvas.save_figure(path, dpi=EXPORT_DPI)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        self._show_temporary_message(f"Exported to {path.name}")

    def _handle_export_csv(self) -> None:
        """Prompt for a destination and save the graph as CSV."""
        path_str, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", CSV_FILTER)
        if not path_str:
            return
        path = _ensure_csv_suffix(Path(path_str))
        try:
            export_csv(self._repository.get(), path)
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        self._show_temporary_message(f"Exported to {path.name}")

    def _handle_import_csv(self) -> None:
        """Prompt for a file and replace the graph with its contents."""
        path_str, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", CSV_FILTER)
        if not path_str:
            return
        path = Path(path_str)
        try:
            graph = import_csv(path)
        except (OSError, CsvFormatError) as exc:
            QMessageBox.warning(self, "Import failed", str(exc))
            return
        if not self._confirm_discard_changes():
            return
        self._repository.save(graph)
        self._positions = self._layout_service.circular(graph)
        self._current_path = None
        self._pending_edge_source = None
        self._drag_node = None
        self._drag_click = None
        self._selected_nodes.clear()
        self._selected_edge = None
        self._drag_changed = False
        self._reset_algorithm()
        self._history.reset(snapshot(self._repository.get(), self._positions))
        self._sync_available_nodes()
        self._refresh_canvas()
        self._update_graph_stats()
        self._refresh_action_states()
        self._update_window_title()
        self._show_temporary_message(
            f"Imported: {graph.node_count} nodes, {graph.edge_count} edges"
        )

    def _handle_load_example(self, example_id: str) -> None:
        """Replace the current project with a pre-built example.

        Args:
            example_id: Stable identifier of the example to load.
        """
        if not self._confirm_discard_changes():
            return
        example = find_example(example_id)
        graph, positions = example.build()
        self._repository.save(graph)
        self._positions = positions
        self._current_path = None
        self._pending_edge_source = None
        self._drag_node = None
        self._drag_click = None
        self._selected_nodes.clear()
        self._selected_edge = None
        self._drag_changed = False
        self._reset_algorithm()
        self._history.reset(snapshot(self._repository.get(), self._positions))
        self._sync_available_nodes()
        self._refresh_canvas()
        self._update_graph_stats()
        self._refresh_action_states()
        self._update_window_title()
        self._show_temporary_message(f"Loaded example: {example.display_name}")

    def _handle_generate_graph(self) -> None:
        """Generate a random graph and replace the current project."""
        request = GenerateGraphDialog.get_request(parent=self)
        if request is None:
            return
        try:
            graph = generate(request)
        except ValueError as exc:
            QMessageBox.warning(self, "Generate failed", str(exc))
            return
        if not self._confirm_discard_changes():
            return
        self._repository.save(graph)
        self._positions = self._layout_service.circular(graph)
        self._current_path = None
        self._pending_edge_source = None
        self._drag_node = None
        self._drag_click = None
        self._selected_nodes.clear()
        self._selected_edge = None
        self._drag_changed = False
        self._reset_algorithm()
        self._history.reset(snapshot(self._repository.get(), self._positions))
        self._sync_available_nodes()
        self._refresh_canvas()
        self._update_graph_stats()
        self._refresh_action_states()
        self._update_window_title()
        self._show_temporary_message(
            f"Generated: {graph.node_count} nodes, {graph.edge_count} edges"
        )

    def _handle_copy(self) -> None:
        """Copy the selected nodes and their internal edges."""
        if not self._selected_nodes:
            return
        graph = self._repository.get()
        nodes = [graph.node(nid) for nid in self._selected_nodes if graph.has_node(nid)]
        node_ids = {node.id for node in nodes}
        edges = [
            edge
            for edge in graph.edges()
            if edge.source in node_ids and edge.target in node_ids
        ]
        self._clipboard = (nodes, edges)
        self._refresh_action_states()
        self._show_temporary_message(
            f"Copied {len(nodes)} node(s), {len(edges)} edge(s)"
        )

    def _handle_paste(self) -> None:
        """Paste the clipboard contents with new ids and shifted positions."""
        if self._clipboard is None:
            return
        nodes, edges = self._clipboard
        new_ids = self._paste_selection(nodes, edges)
        self._show_temporary_message(f"Pasted {len(new_ids)} node(s)")

    def _handle_duplicate(self) -> None:
        """Duplicate the selected nodes in place.

        The clipboard is not touched, so the user's previous copy
        remains available.
        """
        if not self._selected_nodes:
            return
        graph = self._repository.get()
        nodes = [graph.node(nid) for nid in self._selected_nodes if graph.has_node(nid)]
        node_ids = {node.id for node in nodes}
        edges = [
            edge
            for edge in graph.edges()
            if edge.source in node_ids and edge.target in node_ids
        ]
        new_ids = self._paste_selection(nodes, edges)
        self._show_temporary_message(f"Duplicated {len(new_ids)} node(s)")

    def _handle_rename(self) -> None:
        """Open the rename dialog for the single selected node."""
        if len(self._selected_nodes) != 1:
            return
        node_id = next(iter(self._selected_nodes))
        self._handle_edit_node(node_id)

    def _handle_run_shortcut(self) -> None:
        """Trigger the algorithm panel's Run button."""
        if not self._panel._run_button.isEnabled():
            self._show_temporary_message("Run is not available")
            return
        self._panel._run_button.click()

    def _paste_selection(
        self,
        nodes: list[Node],
        edges: list[Edge],
    ) -> list[int]:
        """Create copies of the given nodes and edges in the graph.

        Args:
            nodes: The nodes to copy.
            edges: The edges to copy. Both endpoints must be in
                ``nodes``.

        Returns:
            The list of new node ids, in the same order as ``nodes``.
        """
        if not nodes:
            return []
        graph = self._repository.get()
        id_map: dict[int, int] = {}
        new_ids: list[int] = []
        for node in nodes:
            new_id = graph.next_id()
            self._add_node_use_case.execute(node_id=new_id, label=node.label)
            old_pos = self._positions.get(node.id, Position(0.5, 0.5))
            new_x = old_pos.x + PASTE_OFFSET
            new_y = old_pos.y + PASTE_OFFSET
            if self._snap_to_grid:
                new_x = _snap(new_x)
                new_y = _snap(new_y)
            self._positions[new_id] = Position(x=new_x, y=new_y)
            id_map[node.id] = new_id
            new_ids.append(new_id)
        for edge in edges:
            self._add_edge_use_case.execute(
                source=id_map[edge.source],
                target=id_map[edge.target],
                weight=edge.weight,
                directed=edge.directed,
            )
        self._selected_nodes = set(new_ids)
        self._selected_edge = None
        self._commit()
        self._sync_available_nodes()
        self._update_graph_stats()
        self._refresh_canvas()
        return new_ids

    def _handle_select_all(self) -> None:
        """Select every node in the graph."""
        if self._mode is not InteractionMode.SELECT:
            self.set_mode(InteractionMode.SELECT)
        self._selected_nodes = {node.id for node in self._repository.get().nodes()}
        self._selected_edge = None
        self._refresh_action_states()
        self._refresh_canvas()
        self._refresh_inspector()

    def _handle_delete_selected(self) -> None:
        """Delete the current selection.

        If an edge is selected, only that edge is removed. Otherwise
        every selected node and its incident edges are removed.
        """
        if self._selected_edge is not None:
            source, target = self._selected_edge
            self._selected_edge = None
            self._handle_delete_edge((source, target))
            return
        if not self._selected_nodes:
            return
        graph = self._repository.get()
        count = 0
        for nid in list(self._selected_nodes):
            if graph.has_node(nid):
                self._remove_node_use_case.execute(node_id=nid)
                self._positions.pop(nid, None)
                count += 1
        self._selected_nodes.clear()
        self._commit()
        self._sync_available_nodes()
        self._update_graph_stats()
        self._refresh_canvas()
        self._show_temporary_message(f"Deleted {count} node(s)")

    def _confirm_discard_changes(self) -> bool:
        """Ask the user what to do with unsaved changes.

        Returns:
            True if it is safe to proceed, False if cancelled.
        """
        if not self._history.is_dirty():
            return True
        box = QMessageBox(self)
        box.setWindowTitle(UNSAVED_TITLE)
        box.setText(UNSAVED_TEXT)
        box.setIcon(QMessageBox.Icon.Warning)
        save_button = box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        discard_button = box.addButton(
            "Discard", QMessageBox.ButtonRole.DestructiveRole
        )
        cancel_button = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(save_button)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save_button:
            return self._handle_save_project()
        if clicked is discard_button:
            return True
        if clicked is cancel_button:
            return False
        return False

    def _handle_about(self) -> None:
        """Show a modal About dialog."""
        QMessageBox.about(self, ABOUT_TITLE, ABOUT_TEXT)

    def _reset_algorithm(self) -> None:
        """Stop and clear any running algorithm."""
        self._animator.reset()
        self._algorithm_state = AlgorithmState.IDLE
        self._panel.set_state(AlgorithmState.IDLE)
        self._panel.set_info("")
        self._set_editing_enabled(True)
        self._update_step_availability()
        self._matrix_view.clear_matrix()
        self._matrix_dock.hide()

    def _handle_new_project(self) -> None:
        """Reset the application to an empty project."""
        if not self._confirm_discard_changes():
            return
        self._repository.clear()
        self._positions = {}
        self._current_path = None
        self._pending_edge_source = None
        self._drag_node = None
        self._drag_click = None
        self._selected_nodes.clear()
        self._selected_edge = None
        self._clipboard = None
        self._drag_changed = False
        self._reset_algorithm()
        self._history.reset(snapshot(self._repository.get(), self._positions))
        self._sync_available_nodes()
        self._refresh_canvas()
        self._update_graph_stats()
        self._refresh_action_states()
        self._update_window_title()
        self._refresh_inspector()
        self._show_temporary_message("New project")

    def _handle_open_project(self) -> None:
        """Prompt for a file and load the project from it."""
        if not self._confirm_discard_changes():
            return
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Open project", "", PROJECT_FILTER
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            graph, positions = self._storage.load(path)
        except ProjectStorageError as exc:
            QMessageBox.warning(self, "Open failed", str(exc))
            return
        self._repository.save(graph)
        self._positions = positions
        self._current_path = path
        self._pending_edge_source = None
        self._drag_node = None
        self._drag_click = None
        self._selected_nodes.clear()
        self._selected_edge = None
        self._clipboard = None
        self._drag_changed = False
        self._reset_algorithm()
        self._history.reset(snapshot(self._repository.get(), self._positions))
        self._sync_available_nodes()
        self._refresh_canvas()
        self._update_graph_stats()
        self._refresh_action_states()
        self._update_window_title()
        self._refresh_inspector()
        self._show_temporary_message(f"Opened {path.name}")

    def _handle_save_project(self) -> bool:
        """Save the current project."""
        if self._current_path is None:
            return self._handle_save_project_as()
        return self._save_to(self._current_path)

    def _handle_save_project_as(self) -> bool:
        """Prompt for a path and save."""
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Save project", "", PROJECT_FILTER
        )
        if not path_str:
            return False
        path = Path(path_str)
        if path.suffix != PROJECT_SUFFIX:
            path = path.with_suffix(PROJECT_SUFFIX)
        return self._save_to(path)

    def _save_to(self, path: Path) -> bool:
        """Write the project to the given path."""
        try:
            self._storage.save(self._repository.get(), self._positions, path)
        except ProjectStorageError as exc:
            QMessageBox.warning(self, "Save failed", str(exc))
            return False
        self._current_path = path
        self._history.mark_saved()
        self._update_window_title()
        self._show_temporary_message(f"Saved to {path.name}")
        return True

    def _handle_canvas_click(self, event: ClickEvent) -> None:
        """Dispatch a canvas click according to the active mode.

        Args:
            event: The click event.
        """
        if self._algorithm_state is not AlgorithmState.IDLE:
            return
        if self._mode is InteractionMode.SELECT:
            self._handle_select_click(event)
        elif self._mode is InteractionMode.ADD_NODE:
            self._handle_add_node(event.x, event.y)
        elif self._mode is InteractionMode.ADD_EDGE:
            self._handle_add_edge(event.node_id)
        elif self._mode is InteractionMode.DELETE:
            self._handle_delete(event.node_id, event.edge)

    def _handle_select_click(self, event: ClickEvent) -> None:
        """Handle a click in SELECT mode.

        Args:
            event: The click event.
        """
        if event.node_id is not None:
            self._selected_edge = None
            if event.double:
                self._handle_edit_node(event.node_id)
                return
            if event.shift:
                if event.node_id in self._selected_nodes:
                    self._selected_nodes.discard(event.node_id)
                else:
                    self._selected_nodes.add(event.node_id)
                self._refresh_action_states()
                self._refresh_canvas()
                self._refresh_inspector()
                return
            if event.node_id not in self._selected_nodes:
                self._selected_nodes = {event.node_id}
                self._refresh_action_states()
                self._refresh_canvas()
                self._refresh_inspector()
            self._start_drag(event)
            return

        if event.edge is not None:
            if event.double:
                self._handle_edit_edge(event.edge)
                return
            if not event.shift:
                self._selected_nodes.clear()
            self._selected_edge = event.edge
            self._refresh_action_states()
            self._refresh_canvas()
            self._refresh_inspector()
            return

        if not event.shift and (
            self._selected_nodes or self._selected_edge is not None
        ):
            self._selected_nodes.clear()
            self._selected_edge = None
            self._refresh_action_states()
            self._refresh_canvas()
            self._refresh_inspector()

    def _start_drag(self, event: ClickEvent) -> None:
        """Begin dragging the currently selected nodes.

        Args:
            event: The click that started the drag.
        """
        if event.node_id is None:
            return
        self._drag_node = event.node_id
        self._drag_click = (event.x, event.y)
        self._drag_initial_positions = {
            nid: self._positions[nid]
            for nid in self._selected_nodes
            if nid in self._positions
        }
        self._drag_changed = False

    def _handle_selection_complete(self, event: SelectionEvent) -> None:
        """Handle a completed rubber-band selection.

        Args:
            event: The selection event.
        """
        if self._algorithm_state is not AlgorithmState.IDLE:
            return
        if self._mode is not InteractionMode.SELECT:
            return
        chosen: set[int] = set()
        for node in self._repository.get().nodes():
            position = self._positions.get(node.id)
            if position is None:
                continue
            if (
                event.x1 <= position.x <= event.x2
                and event.y1 <= position.y <= event.y2
            ):
                chosen.add(node.id)
        if event.additive:
            self._selected_nodes |= chosen
        else:
            self._selected_nodes = chosen
        self._selected_edge = None
        self._refresh_action_states()
        self._refresh_canvas()
        self._refresh_inspector()
        if chosen:
            self._show_temporary_message(f"Selected {len(chosen)} node(s)")

    def _handle_context_menu(self, event: ContextEvent) -> None:
        """Show a context menu for the clicked element.

        Args:
            event: The context event with target and screen position.
        """
        if self._algorithm_state is not AlgorithmState.IDLE:
            return
        menu = QMenu(self)
        if event.node_id is not None:
            node_id = event.node_id
            menu.addAction(
                "Edit label",
                lambda: self._handle_edit_node(node_id),
            )
            menu.addAction(
                "Delete node",
                lambda: self._handle_delete_node(node_id),
            )
            menu.addAction(
                "Set as start node",
                lambda: self._handle_set_start_node(node_id),
            )
        elif event.edge is not None:
            edge = event.edge
            menu.addAction(
                "Edit attributes",
                lambda: self._handle_edit_edge(edge),
            )
            menu.addAction(
                "Delete edge",
                lambda: self._handle_delete_edge(edge),
            )
        else:
            x, y = event.x, event.y
            menu.addAction(
                "Add node here",
                lambda: self._handle_add_node(x, y),
            )
        from PySide6.QtCore import QPoint

        menu.exec(QPoint(event.global_x, event.global_y))

    def _handle_set_start_node(self, node_id: int) -> None:
        """Set the algorithm panel's start node to the given id.

        Args:
            node_id: Identifier of the node to mark as start.
        """
        self._panel.set_start_node(node_id)
        self._show_temporary_message(f"Start node set to {node_id}")

    def _handle_canvas_drag_move(self, x: float, y: float) -> None:
        """Move the currently dragged node and its selected peers.

        Args:
            x: Horizontal coordinate of the cursor.
            y: Vertical coordinate of the cursor.
        """
        if self._mode is not InteractionMode.SELECT:
            return
        if self._drag_node is None or self._drag_click is None:
            return
        anchor = self._drag_initial_positions.get(self._drag_node)
        if anchor is None:
            return
        new_x = anchor.x + (x - self._drag_click[0])
        new_y = anchor.y + (y - self._drag_click[1])
        if self._snap_to_grid:
            new_x = _snap(new_x)
            new_y = _snap(new_y)
        delta_x = new_x - anchor.x
        delta_y = new_y - anchor.y
        for nid, original in self._drag_initial_positions.items():
            self._positions[nid] = Position(
                x=original.x + delta_x,
                y=original.y + delta_y,
            )
        self._drag_changed = True
        self._refresh_canvas()

    def _handle_canvas_drag_end(self) -> None:
        """Finish any active drag."""
        self._drag_node = None
        self._drag_click = None
        self._drag_initial_positions = {}
        if self._drag_changed:
            self._drag_changed = False
            self._commit()

    def _handle_add_node(self, x: float, y: float) -> None:
        """Add a node at the clicked position.

        Args:
            x: Horizontal coordinate of the click.
            y: Vertical coordinate of the click.
        """
        if self._snap_to_grid:
            x = _snap(x)
            y = _snap(y)
        graph = self._repository.get()
        new_id = graph.next_id()
        node = self._add_node_use_case.execute(node_id=new_id)
        self._positions[node.id] = Position(x=x, y=y)
        self._commit()
        self._sync_available_nodes()
        self._update_graph_stats()
        self._refresh_canvas()
        self._show_temporary_message(f"Added node {node.id}")

    def _handle_edit_node(self, node_id: int) -> None:
        """Open a dialog to edit the node's label.

        Args:
            node_id: Id of the node to edit.
        """
        graph = self._repository.get()
        if not graph.has_node(node_id):
            return
        current = graph.node(node_id)
        new_label = NodeAttributesDialog.get_label(
            initial_label=current.label,
            node_id=node_id,
            parent=self,
        )
        if new_label is None:
            return
        self._update_node_use_case.execute(node_id=node_id, label=new_label)
        self._commit()
        self._refresh_canvas()
        self._show_temporary_message(f"Node {node_id} label updated")

    def _handle_add_edge(self, node_id: int | None) -> None:
        """Add an edge between two consecutively clicked nodes.

        Clicking the same node twice creates a self-loop.

        Args:
            node_id: Id of the node under the cursor, or None.
        """
        if node_id is None:
            self._pending_edge_source = None
            self._show_temporary_message("Add edge: cancelled")
            return

        if self._pending_edge_source is None:
            self._pending_edge_source = node_id
            self._show_temporary_message(
                f"Add edge: source is node {node_id}, click target"
            )
            return

        source = self._pending_edge_source
        self._pending_edge_source = None

        attributes = EdgeAttributesDialog.get_attributes(parent=self)
        if attributes is None:
            self._show_temporary_message("Add edge: cancelled")
            return

        self._add_edge_use_case.execute(
            source=source,
            target=node_id,
            weight=attributes.weight,
            directed=attributes.directed,
        )
        self._commit()
        self._update_graph_stats()
        self._refresh_canvas()
        self._show_temporary_message(
            f"Added edge {source} -> {node_id} (weight {attributes.weight:g})"
        )

    def _handle_edit_edge(self, edge: tuple[int, int]) -> None:
        """Open a dialog to change the attributes of an existing edge.

        Args:
            edge: Endpoints of the edge to edit.
        """
        source, target = edge
        current = self._find_edge(source, target)
        if current is None:
            return
        attributes = EdgeAttributesDialog.get_attributes(
            initial_weight=current.weight,
            initial_directed=current.directed,
            parent=self,
        )
        if attributes is None:
            self._show_temporary_message("Edit edge: cancelled")
            return
        self._update_edge_use_case.execute(
            source=source,
            target=target,
            weight=attributes.weight,
            directed=attributes.directed,
        )
        self._commit()
        self._refresh_canvas()
        self._show_temporary_message(
            f"Edge {source} -> {target} updated (weight {attributes.weight:g})"
        )

    def _find_edge(self, source: int, target: int) -> Edge | None:
        for edge in self._repository.get().edges():
            if edge.source == source and edge.target == target:
                return edge
            if not edge.directed and edge.source == target and edge.target == source:
                return edge
        return None

    def _handle_delete(
        self,
        node_id: int | None,
        edge: tuple[int, int] | None,
    ) -> None:
        """Remove the node or edge under the cursor.

        Args:
            node_id: Id of the node under the cursor, or None.
            edge: Endpoints of the edge under the cursor, or None.
        """
        if node_id is not None:
            self._handle_delete_node(node_id)
            return
        if edge is not None:
            self._handle_delete_edge(edge)
            return
        self._show_temporary_message("Delete: nothing under cursor")

    def _handle_delete_node(self, node_id: int) -> None:
        """Remove a node and all edges incident to it.

        Args:
            node_id: Id of the node to remove.
        """
        self._remove_node_use_case.execute(node_id=node_id)
        self._positions.pop(node_id, None)
        self._selected_nodes.discard(node_id)
        if self._pending_edge_source == node_id:
            self._pending_edge_source = None
        self._commit()
        self._sync_available_nodes()
        self._update_graph_stats()
        self._refresh_canvas()
        self._show_temporary_message(f"Deleted node {node_id}")

    def _handle_delete_edge(self, edge: tuple[int, int]) -> None:
        """Remove the edge between two nodes.

        Args:
            edge: Endpoints of the edge to remove.
        """
        source, target = edge
        self._remove_edge_use_case.execute(source=source, target=target)
        if self._selected_edge == (source, target):
            self._selected_edge = None
        self._commit()
        self._update_graph_stats()
        self._refresh_canvas()
        self._show_temporary_message(f"Deleted edge {source} -> {target}")

    def _on_inspector_node_label(self, node_id: int, label: str) -> None:
        """Apply a label change coming from the inspector.

        Args:
            node_id: Id of the edited node.
            label: The new label.
        """
        graph = self._repository.get()
        if not graph.has_node(node_id):
            return
        if graph.node(node_id).label == label:
            return
        self._update_node_use_case.execute(node_id=node_id, label=label)
        self._commit()
        self._refresh_canvas()
        self._show_temporary_message(f"Node {node_id} label updated")

    def _on_inspector_edge_weight(
        self, source: int, target: int, weight: float
    ) -> None:
        """Apply a weight change coming from the inspector.

        Args:
            source: Source node id.
            target: Target node id.
            weight: The new weight.
        """
        current = self._find_edge(source, target)
        if current is None:
            return
        if current.weight == weight:
            return
        self._update_edge_use_case.execute(
            source=current.source,
            target=current.target,
            weight=weight,
            directed=current.directed,
        )
        self._commit()
        self._refresh_canvas()
        self._show_temporary_message(
            f"Edge {source} -> {target} weight set to {weight:g}"
        )

    def _on_inspector_edge_directed(
        self, source: int, target: int, directed: bool
    ) -> None:
        """Apply a directed flag change coming from the inspector.

        Args:
            source: Source node id.
            target: Target node id.
            directed: The new directed flag.
        """
        current = self._find_edge(source, target)
        if current is None:
            return
        if current.directed == directed:
            return
        self._update_edge_use_case.execute(
            source=current.source,
            target=current.target,
            weight=current.weight,
            directed=directed,
        )
        self._commit()
        self._refresh_canvas()
        self._show_temporary_message(f"Edge {source} -> {target} updated")

    def _on_run_requested(
        self,
        algorithm_id: str,
        start_node_id: int,
        target_node_id: object,
    ) -> None:
        """Start or resume an algorithm run.

        Args:
            algorithm_id: Identifier of the algorithm.
            start_node_id: Id of the start node.
            target_node_id: Id of the target node, or None.
        """
        if self._algorithm_state in (
            AlgorithmState.PAUSED,
            AlgorithmState.FINISHED,
        ):
            self._animator.resume()
            self._algorithm_state = AlgorithmState.RUNNING
            self._panel.set_state(AlgorithmState.RUNNING)
            self._set_editing_enabled(False)
            self._update_step_availability()
            return

        target: int | None = target_node_id if isinstance(target_node_id, int) else None
        graph = self._repository.get()
        try:
            algorithm = self._registry.create(
                algorithm_id, graph, start_node_id, target
            )
        except (KeyError, ValueError) as exc:
            self._show_temporary_message(str(exc))
            return

        self._mode = InteractionMode.SELECT
        self._pending_edge_source = None
        self._drag_node = None
        self._drag_click = None
        self._selected_nodes.clear()
        self._selected_edge = None
        self._drag_changed = False
        self._set_editing_enabled(False)
        self._algorithm_state = AlgorithmState.RUNNING
        self._panel.set_state(AlgorithmState.RUNNING)
        self._panel.set_info("")
        self._matrix_view.clear_matrix()
        self._animator.start(algorithm, self._current_interval_ms)
        self._update_step_availability()
        self._refresh_inspector()

    def _on_pause_requested(self) -> None:
        """Pause the running algorithm."""
        self._animator.pause()
        self._algorithm_state = AlgorithmState.PAUSED
        self._panel.set_state(AlgorithmState.PAUSED)
        self._update_step_availability()

    def _on_step_requested(self) -> None:
        """Advance the paused or finished algorithm by one step."""
        if self._algorithm_state not in (
            AlgorithmState.PAUSED,
            AlgorithmState.FINISHED,
        ):
            return
        self._animator.step_forward()
        if self._animator.can_step_forward:
            self._algorithm_state = AlgorithmState.PAUSED
        else:
            self._algorithm_state = AlgorithmState.FINISHED
        self._panel.set_state(self._algorithm_state)
        self._update_step_availability()

    def _on_step_back_requested(self) -> None:
        """Return to the previous state in the algorithm's history."""
        if self._algorithm_state not in (
            AlgorithmState.PAUSED,
            AlgorithmState.FINISHED,
        ):
            return
        self._animator.step_back()
        self._algorithm_state = AlgorithmState.PAUSED
        self._panel.set_state(AlgorithmState.PAUSED)
        self._update_step_availability()

    def _on_reset_requested(self) -> None:
        """Discard the current algorithm and return to idle."""
        self._reset_algorithm()
        self._refresh_canvas()

    def _on_speed_changed(self, interval_ms: int) -> None:
        """Update the animation speed.

        Args:
            interval_ms: New delay between steps in milliseconds.
        """
        self._current_interval_ms = interval_ms
        self._animator.set_interval(interval_ms)

    def _on_step_ready(self, result: object) -> None:
        """Render the latest algorithm step.

        Args:
            result: A StepResult emitted by the animator.
        """
        if not isinstance(result, StepResult):
            return
        self._panel.set_info(result.info)
        self._canvas.draw_graph(
            graph=self._repository.get(),
            positions=self._positions,
            highlighted_nodes=result.visited,
            current_node=result.current,
            highlighted_edges=result.tree_edges,
            labels=result.labels,
            node_colors=result.node_colors,
            current_edge=result.current_edge,
            edge_labels=result.edge_labels,
        )
        self._update_matrix_view(result)
        self._update_step_availability()

    def _update_matrix_view(self, result: StepResult) -> None:
        """Update the matrix dock if the step provides matrix data.

        Args:
            result: The StepResult of the current step.
        """
        if not result.matrix:
            return
        node_ids = [node.id for node in self._repository.get().nodes()]
        self._matrix_view.set_matrix(
            node_ids=node_ids,
            matrix=result.matrix,
            highlight_cell=result.highlight_cell,
            highlight_axis=result.current,
        )
        if not self._matrix_dock.isVisible():
            self._matrix_dock.show()

    def _on_algorithm_finished(self) -> None:
        """Switch to the finished state when the algorithm completes."""
        self._algorithm_state = AlgorithmState.FINISHED
        self._panel.set_state(AlgorithmState.FINISHED)
        self._update_step_availability()

    def _refresh_canvas(self) -> None:
        """Redraw the canvas from the current graph and positions."""
        self._canvas.draw_graph(
            graph=self._repository.get(),
            positions=self._positions,
            selected_nodes=frozenset(self._selected_nodes),
            selected_edge=self._selected_edge,
        )
