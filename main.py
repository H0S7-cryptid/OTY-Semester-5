"""Точка запуска UI и консольного режима модели лабиринта."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from game_logic import (
    AlwaysAccept,
    AlwaysReject,
    CustomPattern,
    ExitSeeking,
    FarthestFromExitsProposal,
    Maze,
    MazeGame,
    Player1ProposalStrategy,
    Player2Strategy,
    RandomDecision,
    RandomProposal,
    SimulationStats,
    StandardStrategy,
    parse_exit_nodes,
)


def build_strategy(args: argparse.Namespace) -> Player2Strategy:
    if args.strategy2 == "standard":
        return StandardStrategy()
    if args.strategy2 == "always-accept":
        return AlwaysAccept()
    if args.strategy2 == "always-reject":
        return AlwaysReject()
    if args.strategy2 == "random":
        return RandomDecision(args.accept_probability)
    if args.strategy2 == "exit-seeking":
        return ExitSeeking()
    if args.strategy2 == "custom":
        if not args.pattern:
            raise SystemExit("Для --strategy2 custom укажите --pattern, например ++--+-")
        return CustomPattern(args.pattern)
    return StandardStrategy()


def build_player1_strategy(args: argparse.Namespace) -> Player1ProposalStrategy:
    if args.strategy1 == "random":
        return RandomProposal()
    return FarthestFromExitsProposal()


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Имитационная модель рефлексивного управления в лабиринте")
    parser.add_argument("--ui", action="store_true", help="запустить графический интерфейс")
    parser.add_argument("--cli", action="store_true", help="запустить консольный режим")
    parser.add_argument("--games", type=int, default=1, help="число игр в консольном режиме")
    parser.add_argument("--rounds", type=int, default=25, help="число раундов N в игре")
    parser.add_argument("--exits", default="2,5,25,22", help="выходы через запятую, например 2,5,25,22")
    parser.add_argument("--seed", type=int, default=None, help="начальное значение генератора случайных чисел")
    parser.add_argument(
        "--strategy2",
        choices=("standard", "random", "always-accept", "always-reject", "exit-seeking", "custom"),
        default="standard",
        help="алгоритм игрока 2",
    )
    parser.add_argument("--pattern", help="пользовательский шаблон реакции, например ++--+-")
    parser.add_argument("--accept-probability", type=float, default=0.5, help="вероятность '+' для random")
    parser.add_argument(
        "--strategy1",
        choices=("farthest", "random"),
        default="farthest",
        help="алгоритм предложений игрока 1",
    )
    parser.add_argument("--list-strategies", action="store_true", help="показать доступные стратегии")
    parser.add_argument("--verbose", action="store_true", help="вывести историю ходов")
    return parser


def print_strategies() -> None:
    print("Стратегии игрока 1:")
    print("  farthest       — предлагать узел, самый дальний от всех выходов")
    print("  random         — предлагать случайный доступный узел")
    print()
    print("Стратегии игрока 2:")
    print("  standard       — 5 '+', 6 '-', 2 '+', 4 '-', 4 '+', 1 '-', 1 '+', 2 '-'")
    print("  random         — принимать с заданной вероятностью")
    print("  always-accept  — всегда принимать")
    print("  always-reject  — всегда отклонять")
    print("  exit-seeking   — принимать только переход в выход")
    print("  custom         — пользовательский шаблон '+'/'-'")


def print_result(
    stats: SimulationStats,
    strategy: Player2Strategy,
    player_1: Player1ProposalStrategy,
) -> None:
    print(f"Стратегия И1: {player_1.name}")
    print(f"Стратегия И2: {strategy.name}")
    print(f"Игр: {len(stats.games)}, побед И1: {stats.player_1_wins}, побед И2: {stats.player_2_wins}")
    print(f"Доля побед И2: {stats.player_2_win_rate:.1%}")
    for result in stats.games:
        print(
            f"  Игра {result.game_number}: победитель {result.winner}, "
            f"раундов {result.rounds}, конечный узел {result.final_position}"
        )


def run_cli(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    strategy = build_strategy(args)
    player_1 = build_player1_strategy(args)
    try:
        exits = parse_exit_nodes(args.exits)
    except ValueError as error:
        parser.error(str(error))

    game = MazeGame(Maze.default(), exits=exits, max_rounds=args.rounds)
    stats = game.simulate(
        games=args.games,
        player_2=strategy,
        player_1=player_1,
        seed=args.seed,
    )
    print_result(stats, strategy, player_1)

    if args.verbose:
        for result in stats.games:
            print(f"\nИстория игры {result.game_number}:")
            for move in result.moves:
                if move.actor == "И2":
                    print(
                        f"  раунд {move.round_number}, случайный ход И2: "
                        f"{move.from_node}->{move.proposed_node}"
                    )
                    continue
                sign = "+" if move.accepted else "-"
                print(
                    f"  раунд {move.round_number}, предложение {move.proposal_number}: "
                    f"{move.from_node}->{move.proposed_node} {sign}"
                )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    if args.ui or (argv is None and len(sys.argv) == 1):
        from ui import run_ui

        run_ui()
        return 0
    if args.list_strategies:
        print_strategies()
        return 0
    return run_cli(args, parser)


if __name__ == "__main__":
    raise SystemExit(main())
