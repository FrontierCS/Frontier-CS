#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>

using namespace std;

const int N = 20;

struct Oni {
    int id;
    int r, c;
};

struct Fukunokami {
    int r, c;
};

struct CompoundOp {
    char dir;
    int index;
    int amount;
    int cost;
    vector<int> oni_indices;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_dummy;
    cin >> n_dummy;
    vector<string> C(N);
    vector<Oni> oni_list;
    vector<Fukunokami> fuku_list;
    int oni_id_counter = 0;
    for (int i = 0; i < N; ++i) {
        cin >> C[i];
        for (int j = 0; j < N; ++j) {
            if (C[i][j] == 'x') {
                oni_list.push_back({oni_id_counter++, i, j});
            } else if (C[i][j] == 'o') {
                fuku_list.push_back({i, j});
            }
        }
    }

    vector<int> row_fuku_min_c(N, N);
    vector<int> row_fuku_max_c(N, -1);
    vector<int> col_fuku_min_r(N, N);
    vector<int> col_fuku_max_r(N, -1);

    for (const auto& f : fuku_list) {
        row_fuku_min_c[f.r] = min(row_fuku_min_c[f.r], f.c);
        row_fuku_max_c[f.r] = max(row_fuku_max_c[f.r], f.c);
        col_fuku_min_r[f.c] = min(col_fuku_min_r[f.c], f.r);
        col_fuku_max_r[f.c] = max(col_fuku_max_r[f.c], f.r);
    }

    vector<CompoundOp> ops;

    // Generate row operations
    for (int i = 0; i < N; ++i) {
        int max_c_left = -1;
        for (const auto& oni : oni_list) {
            if (oni.r == i && oni.c < row_fuku_min_c[i]) {
                max_c_left = max(max_c_left, oni.c);
            }
        }
        if (max_c_left != -1) {
            vector<int> left_oni_indices;
            for (const auto& oni : oni_list) {
                if (oni.r == i && oni.c <= max_c_left) {
                    left_oni_indices.push_back(oni.id);
                }
            }
            ops.push_back({'L', i, max_c_left + 1, 2 * (max_c_left + 1), left_oni_indices});
        }

        int min_c_right = N;
        for (const auto& oni : oni_list) {
            if (oni.r == i && oni.c > row_fuku_max_c[i]) {
                min_c_right = min(min_c_right, oni.c);
            }
        }
        if (min_c_right != N) {
            vector<int> right_oni_indices;
            for (const auto& oni : oni_list) {
                if (oni.r == i && oni.c >= min_c_right) {
                    right_oni_indices.push_back(oni.id);
                }
            }
            ops.push_back({'R', i, N - min_c_right, 2 * (N - min_c_right), right_oni_indices});
        }
    }

    // Generate column operations
    for (int j = 0; j < N; ++j) {
        int max_r_up = -1;
        for (const auto& oni : oni_list) {
            if (oni.c == j && oni.r < col_fuku_min_r[j]) {
                max_r_up = max(max_r_up, oni.r);
            }
        }
        if (max_r_up != -1) {
            vector<int> up_oni_indices;
            for (const auto& oni : oni_list) {
                if (oni.c == j && oni.r <= max_r_up) {
                    up_oni_indices.push_back(oni.id);
                }
            }
            ops.push_back({'U', j, max_r_up + 1, 2 * (max_r_up + 1), up_oni_indices});
        }

        int min_r_down = N;
        for (const auto& oni : oni_list) {
            if (oni.c == j && oni.r > col_fuku_max_r[j]) {
                min_r_down = min(min_r_down, oni.r);
            }
        }
        if (min_r_down != N) {
            vector<int> down_oni_indices;
            for (const auto& oni : oni_list) {
                if (oni.c == j && oni.r >= min_r_down) {
                    down_oni_indices.push_back(oni.id);
                }
            }
            ops.push_back({'D', j, N - min_r_down, 2 * (N - min_r_down), down_oni_indices});
        }
    }

    vector<bool> oni_removed(oni_list.size(), false);
    int num_oni_removed = 0;
    vector<pair<char, int>> moves;

    while (num_oni_removed < oni_list.size()) {
        int best_op_idx = -1;
        double min_efficiency = 1e18;

        for (int i = 0; i < ops.size(); ++i) {
            const auto& op = ops[i];
            int newly_covered_count = 0;
            for (int oni_idx : op.oni_indices) {
                if (!oni_removed[oni_idx]) {
                    newly_covered_count++;
                }
            }

            if (newly_covered_count > 0) {
                double efficiency = (double)op.cost / newly_covered_count;
                if (efficiency < min_efficiency) {
                    min_efficiency = efficiency;
                    best_op_idx = i;
                } else if (abs(efficiency - min_efficiency) < 1e-9) {
                    if (best_op_idx == -1 || op.cost < ops[best_op_idx].cost) {
                        best_op_idx = i;
                    }
                }
            }
        }

        if (best_op_idx == -1) {
            int unremoved_oni_idx = -1;
            for(size_t i = 0; i < oni_list.size(); ++i) {
                if(!oni_removed[i]) {
                    unremoved_oni_idx = i;
                    break;
                }
            }
            if (unremoved_oni_idx == -1) break;

            const auto& oni = oni_list[unremoved_oni_idx];
            int r = oni.r, c = oni.c;
            int best_cost = 1e9;
            char best_dir = ' ';
            int best_amount = 0;
            
            if (c < row_fuku_min_c[r]) {
                if (2 * (c + 1) < best_cost) {
                    best_cost = 2 * (c + 1); best_dir = 'L'; best_amount = c + 1;
                }
            }
            if (c > row_fuku_max_c[r]) {
                if (2 * (N - c) < best_cost) {
                    best_cost = 2 * (N - c); best_dir = 'R'; best_amount = N - c;
                }
            }
            if (r < col_fuku_min_r[c]) {
                if (2 * (r + 1) < best_cost) {
                    best_cost = 2 * (r + 1); best_dir = 'U'; best_amount = r + 1;
                }
            }
            if (r > col_fuku_max_r[c]) {
                if (2 * (N - r) < best_cost) {
                    best_cost = 2 * (N - r); best_dir = 'D'; best_amount = N - r;
                }
            }
            
            CompoundOp fallback_op;
            fallback_op.dir = best_dir;
            fallback_op.index = (best_dir == 'L' || best_dir == 'R') ? r : c;
            fallback_op.amount = best_amount;
            fallback_op.cost = best_cost;
            fallback_op.oni_indices.push_back(oni.id);
            ops.push_back(fallback_op);
            best_op_idx = ops.size()-1;
        }

        const auto& best_op = ops[best_op_idx];
        for (int i = 0; i < best_op.amount; ++i) {
            moves.push_back({best_op.dir, best_op.index});
        }
        
        char reverse_dir;
        if (best_op.dir == 'L') reverse_dir = 'R';
        else if (best_op.dir == 'R') reverse_dir = 'L';
        else if (best_op.dir == 'U') reverse_dir = 'D';
        else reverse_dir = 'U';
        
        for (int i = 0; i < best_op.amount; ++i) {
            moves.push_back({reverse_dir, best_op.index});
        }
        
        for (int oni_idx : best_op.oni_indices) {
            if (!oni_removed[oni_idx]) {
                oni_removed[oni_idx] = true;
                num_oni_removed++;
            }
        }
    }

    for (const auto& move : moves) {
        cout << move.first << " " << move.second << "\n";
    }

    return 0;
}