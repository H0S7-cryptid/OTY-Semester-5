"""Игровая логика модели лабиринта без зависимости от пользовательского интерфейса."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


Node = int
Decision = bool
VALID_NODES = frozenset(range(1, 27))
DEFAULT_START = 13
DEFAULT_EXITS = frozenset({2, 5, 22, 25})


# Связи лабиринта с изображения задания.
MAZE_EDGES: tuple[tuple[Node, Node], ...] = (
    (1, 2), (1, 7), (1, 21),
    (2, 3), (2, 8),
    (3, 4), (3, 8), (3, 9),
    (4, 5), (4, 9), (4, 10),
    (5, 6), (5, 10),
    (6, 10), (6, 26),
    (7, 8), (7, 11), (7, 17),
    (8, 9), (8, 11),
    (9, 10), (9, 12),
    (10, 12), (10, 20),
    (11, 12), (11, 13), (11, 14),
    (12, 13), (12, 16),
    (13, 14), (13, 15), (13, 16),
    (14, 15), (14, 17),
    (15, 16), (15, 18), (15, 19),
    (16, 20),
    (17, 18), (17, 21), (17, 22),
    (18, 19), (18, 23), (18, 24),
    (19, 20), (19, 24), (19, 25),
    (20, 26),
    (21, 22), (22, 23), (23, 24), (24, 25), (25, 26),
)


@dataclass(frozen=True)
class Maze:
    """Неориентированный лабиринт с поиском кратчайших расстояний."""

    adjacency: Mapping[Node, frozenset[Node]]

    @classmethod
    def from_edges(
        cls,
        edges: Iterable[tuple[Node, Node]],
        nodes: Iterable[Node] = VALID_NODES,
    ) -> "Maze":
        adjacency: dict[Node, set[Node]] = {node: set() for node in nodes}
        for first, second in edges:
            if first == second:
                raise ValueError(f"Петля узла {first} не поддерживается")
            adjacency.setdefault(first, set()).add(second)
            adjacency.setdefault(second, set()).add(first)
        return cls({node: frozenset(neighbors) for node, neighbors in adjacency.items()})

    @classmethod
    def default(cls) -> "Maze":
        return cls.from_edges(MAZE_EDGES)

    def neighbors(self, node: Node) -> tuple[Node, ...]:
        if node not in self.adjacency:
            raise ValueError(f"Узел {node} отсутствует в лабиринте")
        return tuple(sorted(self.adjacency[node]))

    def has_edge(self, first: Node, second: Node) -> bool:
        return second in self.adjacency.get(first, frozenset())

    def shortest_distances(self, source: Node) -> Mapping[Node, int]:
        """Вернуть длины кратчайших путей от source до всех узлов."""

        if source not in self.adjacency:
            raise ValueError(f"Узел {source} отсутствует в лабиринте")
        distances: dict[Node, int] = {source: 0}
        queue: deque[Node] = deque([source])
        while queue:
            current = queue.popleft()
            for neighbor in self.adjacency[current]:
                if neighbor not in distances:
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)
        return distances

    def distances_to_exits(self, exits: Iterable[Node]) -> Mapping[Node, int]:
        """Расстояние каждого узла до ближайшего из заданных выходов."""

        exits_set = frozenset(exits)
        if not exits_set:
            raise ValueError("Нужен хотя бы один выход")
        if not exits_set.issubset(self.adjacency):
            raise ValueError("Все выходы должны присутствовать в лабиринте")

        distances: dict[Node, int] = {exit_node: 0 for exit_node in exits_set}
        queue: deque[Node] = deque(exits_set)
        while queue:
            current = queue.popleft()
            for neighbor in self.adjacency[current]:
                if neighbor not in distances:
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)
        return distances

    def distance_profile(self, node: Node, exits: Iterable[Node]) -> tuple[int, ...]:
        """Расстояния от node до каждого выхода в отсортированном порядке."""

        distances = [self.shortest_distances(exit_node)[node] for exit_node in sorted(set(exits))]
        if not distances:
            raise ValueError("Нужен хотя бы один выход")
        return tuple(distances)


class Player2Strategy(ABC):
    """Алгоритм реакции игрока 2 на предложение игрока 1."""

    name: str

    @abstractmethod
    def accept(
        self,
        *,
        game_number: int,
        round_number: int,
        current: Node,
        proposed: Node,
        exits: frozenset[Node],
        rng: random.Random,
    ) -> Decision:
        """Вернуть True, если игрок 2 согласен перейти в proposed."""


class AlwaysAccept(Player2Strategy):
    name = "always-accept"

    def accept(self, **_: object) -> Decision:
        return True


class AlwaysReject(Player2Strategy):
    name = "always-reject"

    def accept(self, **_: object) -> Decision:
        return False


class RandomDecision(Player2Strategy):
    name = "random"

    def __init__(self, probability: float = 0.5) -> None:
        if not 0.0 <= probability <= 1.0:
            raise ValueError("Вероятность принятия должна быть от 0 до 1")
        self.probability = probability

    def accept(self, *, rng: random.Random, **_: object) -> Decision:
        return rng.random() < self.probability


class ExitSeeking(Player2Strategy):
    name = "exit-seeking"

    def accept(self, *, proposed: Node, exits: frozenset[Node], **_: object) -> Decision:
        return proposed in exits


class StandardStrategy(Player2Strategy):
    """Стандартный периодический алгоритм согласия И2.

    Цикл состоит из серий: 5 «да», 6 «нет», 2 «да», 4 «нет»,
    4 «да», 1 «нет», 1 «да», 2 «нет».
    """

    name = "standard"
    RUNS: tuple[tuple[Decision, int], ...] = (
        (True, 5), (False, 6), (True, 2), (False, 4),
        (True, 4), (False, 1), (True, 1), (False, 2),
    )
    PATTERN: tuple[Decision, ...] = tuple(decision for decision, count in RUNS for _ in range(count))

    def accept(self, *, round_number: int, **_: object) -> Decision:
        return self.PATTERN[(round_number - 1) % len(self.PATTERN)]


class CustomPattern(Player2Strategy):
    name = "custom"

    def __init__(self, pattern: str, fallback: Player2Strategy | None = None) -> None:
        normalized = pattern.replace(" ", "").replace(",", "")
        if not normalized or any(symbol not in "+-" for symbol in normalized):
            raise ValueError("Шаблон должен содержать только символы '+' и '-'")
        self.pattern = tuple(symbol == "+" for symbol in normalized)
        self.fallback = fallback or RandomDecision()

    def accept(
        self,
        *,
        round_number: int,
        rng: random.Random,
        game_number: int,
        current: Node,
        proposed: Node,
        exits: frozenset[Node],
    ) -> Decision:
        if round_number <= len(self.pattern):
            return self.pattern[round_number - 1]
        return self.fallback.accept(
            game_number=game_number,
            round_number=round_number,
            current=current,
            proposed=proposed,
            exits=exits,
            rng=rng,
        )


class Player1ProposalStrategy(ABC):
    """Алгоритм выбора предложения первым игроком."""

    name: str

    @abstractmethod
    def choose(
        self,
        *,
        maze: Maze,
        current: Node,
        candidates: Sequence[Node],
        exits: frozenset[Node],
        rng: random.Random,
    ) -> Node:
        """Выбрать один узел из candidates."""


class RandomProposal(Player1ProposalStrategy):
    name = "random-proposal"

    def choose(
        self,
        *,
        maze: Maze,
        current: Node,
        candidates: Sequence[Node],
        exits: frozenset[Node],
        rng: random.Random,
    ) -> Node:
        return rng.choice(list(candidates))


class FarthestFromExitsProposal(Player1ProposalStrategy):
    """Предложить соседний узел, самый дальний от ближайшего выхода.

    Основной критерий — расстояние до ближайшего выхода. При равенстве
    используется сумма расстояний до всех выходов, затем выбирается узел с
    меньшим номером для воспроизводимости.
    """

    name = "farthest-from-exits"

    def choose(
        self,
        *,
        maze: Maze,
        current: Node,
        candidates: Sequence[Node],
        exits: frozenset[Node],
        rng: random.Random,
    ) -> Node:
        profiles = {
            node: maze.distance_profile(node, exits)
            for node in candidates
        }
        return max(
            candidates,
            key=lambda node: (min(profiles[node]), sum(profiles[node]), -node),
        )


@dataclass(frozen=True)
class Move:
    round_number: int
    proposal_number: int
    from_node: Node
    proposed_node: Node
    accepted: bool
    position_changed: bool


@dataclass(frozen=True)
class GameResult:
    game_number: int
    winner: str
    rounds: int
    final_position: Node
    moves: tuple[Move, ...]

    @property
    def player_2_won(self) -> bool:
        return self.winner == "И2"


@dataclass
class SimulationStats:
    games: list[GameResult] = field(default_factory=list)

    @property
    def player_1_wins(self) -> int:
        return sum(result.winner == "И1" for result in self.games)

    @property
    def player_2_wins(self) -> int:
        return sum(result.player_2_won for result in self.games)

    @property
    def player_2_win_rate(self) -> float:
        return self.player_2_wins / len(self.games) if self.games else 0.0


class MazeGame:
    def __init__(
        self,
        maze: Maze,
        *,
        exits: Iterable[Node] = DEFAULT_EXITS,
        max_rounds: int = 25,
        max_proposals_per_round: int | None = None,
    ) -> None:
        start = DEFAULT_START
        if start not in maze.adjacency:
            raise ValueError(f"Стартовый узел {start} отсутствует в лабиринте")
        if max_rounds <= 0:
            raise ValueError("Число раундов N должно быть положительным")
        exits_set = frozenset(exits)
        if not exits_set or not exits_set.issubset(maze.adjacency):
            raise ValueError("Выходы должны быть непустыми и присутствовать в лабиринте")
        self.maze = maze
        self.start = start
        self.exits = exits_set
        self.max_rounds = max_rounds
        self.max_proposals_per_round = max_proposals_per_round

    def play(
        self,
        *,
        game_number: int,
        player_2: Player2Strategy,
        player_1: Player1ProposalStrategy,
        rng: random.Random,
    ) -> GameResult:
        position = self.start
        moves: list[Move] = []

        for round_number in range(1, self.max_rounds + 1):
            candidates = list(self.maze.neighbors(position))
            rng.shuffle(candidates)
            attempts_limit = self.max_proposals_per_round or len(candidates)
            attempts = 0

            while candidates and attempts < attempts_limit:
                proposed = player_1.choose(
                    maze=self.maze,
                    current=position,
                    candidates=candidates,
                    exits=self.exits,
                    rng=rng,
                )
                candidates.remove(proposed)
                attempts += 1
                accepted = player_2.accept(
                    game_number=game_number,
                    round_number=round_number,
                    current=position,
                    proposed=proposed,
                    exits=self.exits,
                    rng=rng,
                )
                moves.append(Move(round_number, attempts, position, proposed, accepted, accepted))
                if accepted:
                    position = proposed
                    if position in self.exits:
                        return GameResult(game_number, "И2", round_number, position, tuple(moves))
                    break

        return GameResult(game_number, "И1", self.max_rounds, position, tuple(moves))

    def simulate(
        self,
        *,
        games: int,
        player_2: Player2Strategy,
        player_1: Player1ProposalStrategy | None = None,
        seed: int | None = None,
    ) -> SimulationStats:
        if games <= 0:
            raise ValueError("Объём выборки K должен быть положительным")
        rng = random.Random(seed)
        player_1 = player_1 or FarthestFromExitsProposal()
        stats = SimulationStats()
        for game_number in range(1, games + 1):
            stats.games.append(self.play(game_number=game_number, player_2=player_2, player_1=player_1, rng=rng))
        return stats


def parse_exit_nodes(value: str) -> frozenset[Node]:
    """Разобрать строку выходов вида ``2, 5, 25, 22``."""

    tokens = value.replace(",", " ").split()
    if not tokens:
        raise ValueError("Укажите хотя бы один выходной узел")
    try:
        exits = frozenset(int(token) for token in tokens)
    except ValueError as error:
        raise ValueError("Номера выходов должны быть целыми числами") from error
    invalid = sorted(node for node in exits if node not in VALID_NODES)
    if invalid:
        raise ValueError(f"Узлы вне лабиринта: {', '.join(map(str, invalid))}")
    return exits
