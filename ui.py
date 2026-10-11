"""Tkinter-интерфейс модели лабиринта."""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Mapping

from game_logic import (
    AlwaysAccept,
    AlwaysReject,
    DEFAULT_EXITS,
    ExitSeeking,
    FarthestFromExitsProposal,
    GameResult,
    MAZE_EDGES,
    Maze,
    MazeGame,
    Node,
    Player1ProposalStrategy,
    Player2Strategy,
    RandomProposal,
    RandomDecision,
    StandardStrategy,
    parse_exit_nodes,
)


# Координаты узлов с изображения задания. Они не участвуют в расчёте игры.
MAZE_COORDINATES: Mapping[Node, tuple[int, int]] = {
    1: (107, 108), 2: (231, 60), 3: (384, 47), 4: (536, 60),
    5: (659, 108), 6: (719, 230), 7: (187, 243), 8: (322, 212),
    9: (445, 212), 10: (580, 243), 11: (291, 341), 12: (475, 341),
    13: (383, 416), 14: (274, 477), 15: (383, 524), 16: (493, 476),
    17: (187, 585), 18: (321, 616), 19: (445, 616), 20: (579, 585),
    21: (47, 599), 22: (108, 721), 23: (230, 770), 24: (384, 782),
    25: (536, 770), 26: (659, 721),
}


class MazeApp:
    """Графический интерфейс одного непрерывного сеанса моделирования."""

    PLAYER1_STRATEGIES: tuple[str, ...] = (
        "Самая дальняя от выходов",
        "Случайный узел",
    )

    STRATEGIES: tuple[str, ...] = (
        "Стандартный (5+, 6-, 2+, 4-, 4+, 1-, 1+, 2-)",
        "Случайная",
        "Всегда принимать",
        "Всегда отклонять",
        "Принимать только выходы",
    )

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Модель рефлексивного управления — лабиринт")
        self.root.geometry("1400x850")
        self.root.minsize(900, 600)
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        self.maze = Maze.default()
        self.rng = random.Random()
        self.current_game_number = 0
        self.current_params: tuple[str, str, int, frozenset[Node]] | None = None
        self.history: list[GameResult] = []
        self.current_position = 13
        self._draw_job: str | None = None

        self.player1_strategy_var = tk.StringVar(value=self.PLAYER1_STRATEGIES[0])
        self.strategy_var = tk.StringVar(value=self.STRATEGIES[0])
        self.rounds_var = tk.StringVar(value="25")
        self.exits_var = tk.StringVar(value=", ".join(map(str, sorted(DEFAULT_EXITS))))
        self.status_var = tk.StringVar(value="Введите параметры и запустите моделирование.")

        self._build_layout()
        self._draw_maze()

    def _build_layout(self) -> None:
        # Sash-панели можно перетаскивать, а центральный Canvas автоматически
        # перерисовывается по фактическому размеру доступной области.
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        settings = ttk.LabelFrame(self.main_pane, text="Параметры игры", padding=12)
        settings.columnconfigure(0, weight=1)
        self.main_pane.add(settings, weight=0)

        ttk.Label(settings, text="Стратегия И1:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.player1_strategy_combo = ttk.Combobox(
            settings,
            textvariable=self.player1_strategy_var,
            values=self.PLAYER1_STRATEGIES,
            state="readonly",
            width=31,
        )
        self.player1_strategy_combo.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(settings, text="Стратегия И2:").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.strategy_combo = ttk.Combobox(
            settings,
            textvariable=self.strategy_var,
            values=self.STRATEGIES,
            state="readonly",
            width=31,
        )
        self.strategy_combo.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(settings, text="Количество раундов:").grid(row=4, column=0, sticky="w", pady=(0, 4))
        self.rounds_spinbox = ttk.Spinbox(settings, from_=1, to=1000, textvariable=self.rounds_var, width=10)
        self.rounds_spinbox.grid(row=5, column=0, sticky="w", pady=(0, 12))

        ttk.Label(settings, text="Выходные узлы:").grid(row=6, column=0, sticky="w", pady=(0, 4))
        self.exits_entry = ttk.Entry(settings, textvariable=self.exits_var, width=33)
        self.exits_entry.grid(row=7, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(settings, text="Например: 2, 5, 25, 22", foreground="#666666").grid(
            row=8, column=0, sticky="w", pady=(0, 16)
        )

        self.start_button = ttk.Button(settings, text="Начать моделирование", command=self.start_session)
        self.start_button.grid(row=9, column=0, sticky="ew", pady=(0, 8))
        self.new_button = ttk.Button(settings, text="Новые параметры", command=self.finish_session, state="disabled")
        self.new_button.grid(row=10, column=0, sticky="ew")
        ttk.Separator(settings).grid(row=11, column=0, sticky="ew", pady=16)
        ttk.Label(settings, textvariable=self.status_var, wraplength=230).grid(row=12, column=0, sticky="w")

        graph_frame = ttk.LabelFrame(self.main_pane, text="Лабиринт", padding=8)
        graph_frame.rowconfigure(0, weight=1)
        graph_frame.columnconfigure(0, weight=1)
        self.main_pane.add(graph_frame, weight=4)
        self.graph_canvas = tk.Canvas(graph_frame, background="white", highlightthickness=0)
        self.graph_canvas.grid(row=0, column=0, sticky="nsew")
        self.graph_canvas.bind("<Configure>", self._on_graph_resize)

        result_frame = ttk.LabelFrame(self.main_pane, text="Результаты", padding=8)
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)
        self.main_pane.add(result_frame, weight=2)
        self.result_text = tk.Text(result_frame, width=42, height=35, wrap="word", state="disabled")
        self.result_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.result_text.configure(yscrollcommand=scrollbar.set)

        self.continue_frame = ttk.Frame(result_frame)
        self.continue_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Label(self.continue_frame, text="Продолжить моделирование?").pack(side="left", padx=(0, 8))
        ttk.Button(self.continue_frame, text="Да", command=self.continue_session).pack(side="left", padx=2)
        ttk.Button(self.continue_frame, text="Нет", command=self.finish_session).pack(side="left", padx=2)
        self.continue_frame.grid_remove()

    def _on_graph_resize(self, _event: tk.Event[tk.Misc]) -> None:
        if self._draw_job is not None:
            self.root.after_cancel(self._draw_job)
        self._draw_job = self.root.after_idle(self._draw_maze)

    def _set_inputs_enabled(self, enabled: bool) -> None:
        self.player1_strategy_combo.configure(state="readonly" if enabled else "disabled")
        self.strategy_combo.configure(state="readonly" if enabled else "disabled")
        self.rounds_spinbox.configure(state="normal" if enabled else "disabled")
        self.exits_entry.configure(state="normal" if enabled else "disabled")
        self.start_button.configure(state="normal" if enabled else "disabled")
        self.new_button.configure(state="disabled" if enabled else "normal")

    def _draw_maze(self) -> None:
        self._draw_job = None
        self.graph_canvas.delete("all")
        width = max(self.graph_canvas.winfo_width(), 300)
        height = max(self.graph_canvas.winfo_height(), 300)
        margin = 30
        scale = min((width - 2 * margin) / 768, (height - 2 * margin) / 782)
        scale = max(scale, 0.05)
        offset_x = (width - 768 * scale) / 2
        offset_y = (height - 782 * scale) / 2

        def point(node: Node) -> tuple[float, float]:
            x, y = MAZE_COORDINATES[node]
            return offset_x + x * scale, offset_y + y * scale

        for first, second in MAZE_EDGES:
            x1, y1 = point(first)
            x2, y2 = point(second)
            self.graph_canvas.create_line(x1, y1, x2, y2, fill="#b8c4d0", width=max(1, int(scale * 1.5)))

        exits = self.current_params[3] if self.current_params else DEFAULT_EXITS
        radius = max(8, min(20, 18 * scale))
        font_size = max(7, min(12, int(10 * max(scale, 0.7))))
        for node in sorted(MAZE_COORDINATES):
            x, y = point(node)
            if node == self.current_position:
                fill, outline, outline_width = "#ffd45c", "#b78300", 3
            elif node in exits:
                fill, outline, outline_width = "#d8f3dc", "#3d8b52", 2
            else:
                fill, outline, outline_width = "#eef4fb", "#4d82b8", 2
            self.graph_canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill=fill, outline=outline, width=outline_width,
            )
            self.graph_canvas.create_text(x, y, text=str(node), font=("Segoe UI", font_size, "bold"))

        self.graph_canvas.create_text(
            10, 10, anchor="nw",
            text="Жёлтый — текущая позиция; зелёные — выходы",
            fill="#555555",
        )

    def _write_result(self, text: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")
        self.result_text.see("end")

    def _player1_strategy_from_selection(self) -> Player1ProposalStrategy:
        if self.player1_strategy_var.get() == self.PLAYER1_STRATEGIES[1]:
            return RandomProposal()
        return FarthestFromExitsProposal()

    def _strategy_from_selection(self) -> Player2Strategy:
        selected = self.strategy_var.get()
        if selected == self.STRATEGIES[0]:
            return StandardStrategy()
        if selected == self.STRATEGIES[1]:
            return RandomDecision()
        if selected == self.STRATEGIES[2]:
            return AlwaysAccept()
        if selected == self.STRATEGIES[3]:
            return AlwaysReject()
        if selected == self.STRATEGIES[4]:
            return ExitSeeking()
        return StandardStrategy()

    def _result_text_for(self, result: GameResult) -> str:
        assert self.current_params is not None
        strategy1, strategy2, rounds, exits = self.current_params
        accepted_path = ["13"]
        for move in result.moves:
            if move.accepted:
                accepted_path.append(str(move.proposed_node))
        details = "\n".join(
            f"Раунд {move.round_number}, предложение {move.proposal_number}: "
            f"{move.from_node} → {move.proposed_node} {'+' if move.accepted else '-'}"
            for move in result.moves
        ) or "Предложений не было."
        return (
            f"Игра №{result.game_number}\n"
            f"Стратегия И1: {strategy1}\n"
            f"Стратегия И2: {strategy2}\n"
            f"Количество раундов: {rounds}\n"
            f"Выходы: {', '.join(map(str, sorted(exits)))}\n\n"
            f"Победитель: {result.winner}\n"
            f"Раунд завершения: {result.rounds}\n"
            f"Финальный узел: {result.final_position}\n"
            f"Путь принятых переходов: {' → '.join(accepted_path)}\n\n"
            f"История предложений:\n{details}"
        )

    def start_session(self) -> None:
        try:
            rounds = int(self.rounds_var.get())
            if rounds <= 0:
                raise ValueError("Количество раундов должно быть положительным")
            exits = parse_exit_nodes(self.exits_var.get())
            strategy1 = self._player1_strategy_from_selection()
            strategy = self._strategy_from_selection()
        except ValueError as error:
            messagebox.showerror("Некорректные параметры", str(error), parent=self.root)
            return

        self.current_params = (self.player1_strategy_var.get(), self.strategy_var.get(), rounds, exits)
        self.current_game_number = 0
        self.history.clear()
        self.current_position = 13
        self._set_inputs_enabled(False)
        self.status_var.set("Сеанс активен. Кнопка «Да» запускает следующую игру с теми же параметрами.")
        self._play_next_game(strategy1, strategy, rounds, exits)

    def _play_next_game(
        self,
        player_1: Player1ProposalStrategy,
        strategy: Player2Strategy,
        rounds: int,
        exits: frozenset[Node],
    ) -> None:
        self.current_game_number += 1
        result = MazeGame(self.maze, exits=exits, max_rounds=rounds).play(
            game_number=self.current_game_number,
            player_2=strategy,
            player_1=player_1,
            rng=self.rng,
        )
        self.history.append(result)
        self.current_position = result.final_position
        self._draw_maze()
        self._write_result(self._result_text_for(result))
        self.continue_frame.grid()

    def continue_session(self) -> None:
        if self.current_params is None:
            return
        _player1_name, _strategy2_name, rounds, exits = self.current_params
        self._play_next_game(self._player1_strategy_from_selection(), self._strategy_from_selection(), rounds, exits)

    def finish_session(self) -> None:
        self.current_params = None
        self.continue_frame.grid_remove()
        self._set_inputs_enabled(True)
        self.status_var.set("Сеанс завершён. Можно ввести новые параметры.")
        self.current_position = 13
        self._write_result("")
        self._draw_maze()


def run_ui() -> None:
    root = tk.Tk()
    MazeApp(root)
    root.mainloop()
