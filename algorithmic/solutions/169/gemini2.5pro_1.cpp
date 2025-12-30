#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

// Constants
const int N_fixed = 20;

// Struct to represent a single move
struct Move {
    char dir;
    int index;
};

// Struct to represent a potential group operation
struct Operation {
    char dir;
    int index;
    int count; // num shifts
    int oni_removed;
    long long cost;
};

// Applies a shift operation to the grid
void apply_shift(std::vector<std::string>& grid, char dir, int index, int count) {
    if (count <= 0) return;
    if (dir == 'U') {
        for (int i = 0; i < N_fixed; ++i) {
            grid[i][index] = (i + count < N_fixed) ? grid[i + count][index] : '.';
        }
    } else if (dir == 'D') {
        for (int i = N_fixed - 1; i >= 0; --i) {
            grid[i][index] = (i - count >= 0) ? grid[i - count][index] : '.';
        }
    } else if (dir == 'L') {
        for (int j = 0; j < N_fixed; ++j) {
            grid[index][j] = (j + count < N_fixed) ? grid[index][j + count] : '.';
        }
    } else if (dir == 'R') {
        for (int j = N_fixed - 1; j >= 0; --j) {
            grid[index][j] = (j - count >= 0) ? grid[index][j - count] : '.';
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N_in;
    std::cin >> N_in;

    std::vector<std::string> grid(N_fixed);
    for (int i = 0; i < N_fixed; ++i) {
        std::cin >> grid[i];
    }

    std::vector<Move> solution;

    while (true) {
        int total_oni = 0;
        for (int i = 0; i < N_fixed; ++i) {
            for (int j = 0; j < N_fixed; ++j) {
                if (grid[i][j] == 'x') {
                    total_oni++;
                }
            }
        }

        if (total_oni == 0) {
            break;
        }

        Operation best_op = {' ', -1, 0, 0, -1};
        long long best_op_num = -1, best_op_den = 1;

        // Find best UP operation
        for (int j = 0; j < N_fixed; ++j) {
            int min_f = N_fixed;
            for (int i = 0; i < N_fixed; ++i) {
                if (grid[i][j] == 'o') {
                    min_f = i;
                    break;
                }
            }

            int oni_to_remove = 0;
            int max_r = -1;
            for (int i = 0; i < min_f; ++i) {
                if (grid[i][j] == 'x') {
                    oni_to_remove++;
                    max_r = i;
                }
            }

            if (oni_to_remove > 0) {
                long long cost = max_r + 1;
                if (best_op_num == -1 || (long long)oni_to_remove * best_op_den > best_op_num * cost) {
                    best_op_num = oni_to_remove;
                    best_op_den = cost;
                    best_op = {'U', j, max_r + 1, oni_to_remove, cost};
                } else if ((long long)oni_to_remove * best_op_den == best_op_num * cost) {
                    if (best_op.cost == -1 || cost < best_op.cost) {
                         best_op = {'U', j, max_r + 1, oni_to_remove, cost};
                    }
                }
            }
        }

        // Find best DOWN operation
        for (int j = 0; j < N_fixed; ++j) {
            int max_f = -1;
            for (int i = N_fixed - 1; i >= 0; --i) {
                if (grid[i][j] == 'o') {
                    max_f = i;
                    break;
                }
            }

            int oni_to_remove = 0;
            int min_r = N_fixed;
            for (int i = N_fixed - 1; i > max_f; --i) {
                if (grid[i][j] == 'x') {
                    oni_to_remove++;
                    min_r = i;
                }
            }
            if (oni_to_remove > 0) {
                long long cost = N_fixed - min_r;
                if (best_op_num == -1 || (long long)oni_to_remove * best_op_den > best_op_num * cost) {
                    best_op_num = oni_to_remove;
                    best_op_den = cost;
                    best_op = {'D', j, N_fixed - min_r, oni_to_remove, cost};
                } else if ((long long)oni_to_remove * best_op_den == best_op_num * cost) {
                    if (best_op.cost == -1 || cost < best_op.cost) {
                         best_op = {'D', j, N_fixed - min_r, oni_to_remove, cost};
                    }
                }
            }
        }
        
        // Find best LEFT operation
        for (int i = 0; i < N_fixed; ++i) {
            int min_f = N_fixed;
            for (int j = 0; j < N_fixed; ++j) {
                if (grid[i][j] == 'o') {
                    min_f = j;
                    break;
                }
            }

            int oni_to_remove = 0;
            int max_c = -1;
            for (int j = 0; j < min_f; ++j) {
                if (grid[i][j] == 'x') {
                    oni_to_remove++;
                    max_c = j;
                }
            }

            if (oni_to_remove > 0) {
                long long cost = max_c + 1;
                if (best_op_num == -1 || (long long)oni_to_remove * best_op_den > best_op_num * cost) {
                    best_op_num = oni_to_remove;
                    best_op_den = cost;
                    best_op = {'L', i, max_c + 1, oni_to_remove, cost};
                } else if ((long long)oni_to_remove * best_op_den == best_op_num * cost) {
                    if (best_op.cost == -1 || cost < best_op.cost) {
                         best_op = {'L', i, max_c + 1, oni_to_remove, cost};
                    }
                }
            }
        }
        
        // Find best RIGHT operation
        for (int i = 0; i < N_fixed; ++i) {
            int max_f = -1;
            for (int j = N_fixed - 1; j >= 0; --j) {
                if (grid[i][j] == 'o') {
                    max_f = j;
                    break;
                }
            }

            int oni_to_remove = 0;
            int min_c = N_fixed;
            for (int j = N_fixed - 1; j > max_f; --j) {
                if (grid[i][j] == 'x') {
                    oni_to_remove++;
                    min_c = j;
                }
            }
            if (oni_to_remove > 0) {
                long long cost = N_fixed - min_c;
                if (best_op_num == -1 || (long long)oni_to_remove * best_op_den > best_op_num * cost) {
                    best_op_num = oni_to_remove;
                    best_op_den = cost;
                    best_op = {'R', i, N_fixed - min_c, oni_to_remove, cost};
                } else if ((long long)oni_to_remove * best_op_den == best_op_num * cost) {
                    if (best_op.cost == -1 || cost < best_op.cost) {
                        best_op = {'R', i, N_fixed - min_c, oni_to_remove, cost};
                    }
                }
            }
        }
        
        if (best_op.index == -1) {
            // Should not happen given the problem constraints
            break;
        }

        // Apply best operation
        for (int i = 0; i < best_op.count; ++i) {
            solution.push_back({best_op.dir, best_op.index});
        }
        apply_shift(grid, best_op.dir, best_op.index, best_op.count);
    }

    for (const auto& move : solution) {
        std::cout << move.dir << " " << move.index << "\n";
    }

    return 0;
}