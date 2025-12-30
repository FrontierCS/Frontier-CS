#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <map>

// The problem statement guarantees N=20 for all test cases.
const int N = 20;

struct Oni {
    int id;
    int r, c;
};

// Represents a high-level "remove-and-restore" operation.
struct Operation {
    char dir;
    int index;
    int k; // Depth of the operation.
    int cost;
    std::vector<int> onis_covered; // IDs of Oni removed by this operation.
};

// Represents a single elementary move.
struct Move {
    char dir;
    int index;
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n_dummy;
    std::cin >> n_dummy; // Read N from input, though it's fixed at 20.

    std::vector<std::string> initial_board(N);
    std::vector<Oni> onis;
    std::map<std::pair<int, int>, int> oni_map;

    for (int i = 0; i < N; ++i) {
        std::cin >> initial_board[i];
        for (int j = 0; j < N; ++j) {
            if (initial_board[i][j] == 'x') {
                int id = onis.size();
                onis.push_back({id, i, j});
                oni_map[{i, j}] = id;
            }
        }
    }

    int num_onis = onis.size();
    std::vector<Operation> ops;

    // Generate all valid 'Up' operations
    for (int j = 0; j < N; ++j) {
        std::vector<int> onis_in_path;
        for (int k = 0; k < N; ++k) {
            if (initial_board[k][j] == 'o') break;
            if (initial_board[k][j] == 'x') onis_in_path.push_back(oni_map.at({k, j}));
            if (!onis_in_path.empty()) ops.push_back({'U', j, k, 2 * (k + 1), onis_in_path});
        }
    }

    // Generate all valid 'Down' operations
    for (int j = 0; j < N; ++j) {
        std::vector<int> onis_in_path;
        for (int k = N - 1; k >= 0; --k) {
            if (initial_board[k][j] == 'o') break;
            if (initial_board[k][j] == 'x') onis_in_path.push_back(oni_map.at({k, j}));
            if (!onis_in_path.empty()) ops.push_back({'D', j, k, 2 * (N - k), onis_in_path});
        }
    }

    // Generate all valid 'Left' operations
    for (int i = 0; i < N; ++i) {
        std::vector<int> onis_in_path;
        for (int k = 0; k < N; ++k) {
            if (initial_board[i][k] == 'o') break;
            if (initial_board[i][k] == 'x') onis_in_path.push_back(oni_map.at({i, k}));
            if (!onis_in_path.empty()) ops.push_back({'L', i, k, 2 * (k + 1), onis_in_path});
        }
    }

    // Generate all valid 'Right' operations
    for (int i = 0; i < N; ++i) {
        std::vector<int> onis_in_path;
        for (int k = N - 1; k >= 0; --k) {
            if (initial_board[i][k] == 'o') break;
            if (initial_board[i][k] == 'x') onis_in_path.push_back(oni_map.at({i, k}));
            if (!onis_in_path.empty()) ops.push_back({'R', i, k, 2 * (N - k), onis_in_path});
        }
    }

    std::vector<bool> removed(num_onis, false);
    int num_removed = 0;
    std::vector<Move> solution_moves;

    while (num_removed < num_onis) {
        double max_score = -1.0;
        int best_op_idx = -1;

        for (int i = 0; i < ops.size(); ++i) {
            int benefit = 0;
            for (int oni_id : ops[i].onis_covered) {
                if (!removed[oni_id]) {
                    benefit++;
                }
            }
            if (benefit == 0) continue;

            double score = (double)benefit / sqrt(ops[i].cost);

            if (score > max_score) {
                max_score = score;
                best_op_idx = i;
            } else if (score == max_score) {
                if (best_op_idx == -1 || ops[i].cost < ops[best_op_idx].cost) {
                    best_op_idx = i;
                }
            }
        }

        if (best_op_idx == -1) break; // Should not be reached

        Operation& best_op = ops[best_op_idx];

        if (best_op.dir == 'U') {
            for (int i = 0; i < best_op.k + 1; ++i) solution_moves.push_back({'U', best_op.index});
            for (int i = 0; i < best_op.k + 1; ++i) solution_moves.push_back({'D', best_op.index});
        } else if (best_op.dir == 'D') {
            for (int i = 0; i < N - best_op.k; ++i) solution_moves.push_back({'D', best_op.index});
            for (int i = 0; i < N - best_op.k; ++i) solution_moves.push_back({'U', best_op.index});
        } else if (best_op.dir == 'L') {
            for (int i = 0; i < best_op.k + 1; ++i) solution_moves.push_back({'L', best_op.index});
            for (int i = 0; i < best_op.k + 1; ++i) solution_moves.push_back({'R', best_op.index});
        } else if (best_op.dir == 'R') {
            for (int i = 0; i < N - best_op.k; ++i) solution_moves.push_back({'R', best_op.index});
            for (int i = 0; i < N - best_op.k; ++i) solution_moves.push_back({'L', best_op.index});
        }

        for (int oni_id : best_op.onis_covered) {
            if (!removed[oni_id]) {
                removed[oni_id] = true;
                num_removed++;
            }
        }
    }

    for (const auto& move : solution_moves) {
        std::cout << move.dir << " " << move.index << "\n";
    }

    return 0;
}