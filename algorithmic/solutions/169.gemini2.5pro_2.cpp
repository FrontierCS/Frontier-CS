#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <tuple>

using namespace std;

const int N = 20;

struct Oni {
    int id;
    int r, c;
};

struct Operation {
    double score = -1.0;
    int benefit = 0;
    long long cost = 0;
    char dir = ' ';
    int index = -1;
    vector<int> oni_indices;
    int shifts = 0;
};

// Tie-breaking: higher benefit, then lower cost.
bool is_better(const Operation& op1, const Operation& op2) {
    if (op1.score > op2.score) return true;
    if (op1.score < op2.score) return false;
    if (op1.benefit > op2.benefit) return true;
    if (op1.benefit < op2.benefit) return false;
    if (op1.cost < op2.cost) return true;
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_dummy;
    cin >> n_dummy;

    vector<string> board(N);
    vector<Oni> oni_list;
    int oni_counter = 0;

    for (int i = 0; i < N; ++i) {
        cin >> board[i];
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 'x') {
                oni_list.push_back({oni_counter++, i, j});
            }
        }
    }

    vector<bool> oni_removed(oni_list.size(), false);
    int num_oni_total = oni_list.size();
    int num_oni_removed = 0;

    vector<int> fuku_row_min(N, N), fuku_row_max(N, -1);
    vector<int> fuku_col_min(N, N), fuku_col_max(N, -1);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 'o') {
                fuku_row_min[i] = min(fuku_row_min[i], j);
                fuku_row_max[i] = max(fuku_row_max[i], j);
                fuku_col_min[j] = min(fuku_col_min[j], i);
                fuku_col_max[j] = max(fuku_col_max[j], i);
            }
        }
    }

    vector<pair<char, int>> solution_moves;

    while (num_oni_removed < num_oni_total) {
        Operation best_op;

        // Evaluate removing Oni from rows
        for (int i = 0; i < N; ++i) {
            vector<pair<int, int>> left_removable, right_removable;
            for (const auto& oni : oni_list) {
                if (!oni_removed[oni.id] && oni.r == i) {
                    if (oni.c < fuku_row_min[i]) {
                        left_removable.push_back({oni.c, oni.id});
                    }
                    if (oni.c > fuku_row_max[i]) {
                        right_removable.push_back({oni.c, oni.id});
                    }
                }
            }
            sort(left_removable.begin(), left_removable.end());
            sort(right_removable.rbegin(), right_removable.rend());

            vector<int> current_oni_ids;
            for (size_t j = 0; j < left_removable.size(); ++j) {
                current_oni_ids.push_back(left_removable[j].second);
                Operation current_op;
                current_op.benefit = j + 1;
                current_op.cost = 2LL * (left_removable[j].first + 1);
                current_op.score = (double)current_op.benefit / current_op.cost;
                current_op.dir = 'L';
                current_op.index = i;
                current_op.oni_indices = current_oni_ids;
                current_op.shifts = left_removable[j].first + 1;
                if (is_better(current_op, best_op)) {
                    best_op = current_op;
                }
            }
            
            current_oni_ids.clear();
            for (size_t j = 0; j < right_removable.size(); ++j) {
                current_oni_ids.push_back(right_removable[j].second);
                Operation current_op;
                current_op.benefit = j + 1;
                current_op.cost = 2LL * (N - right_removable[j].first);
                current_op.score = (double)current_op.benefit / current_op.cost;
                current_op.dir = 'R';
                current_op.index = i;
                current_op.oni_indices = current_oni_ids;
                current_op.shifts = N - right_removable[j].first;
                if (is_better(current_op, best_op)) {
                    best_op = current_op;
                }
            }
        }
        
        // Evaluate removing Oni from columns
        for (int j = 0; j < N; ++j) {
            vector<pair<int, int>> up_removable, down_removable;
            for (const auto& oni : oni_list) {
                if (!oni_removed[oni.id] && oni.c == j) {
                    if (oni.r < fuku_col_min[j]) {
                        up_removable.push_back({oni.r, oni.id});
                    }
                    if (oni.r > fuku_col_max[j]) {
                        down_removable.push_back({oni.r, oni.id});
                    }
                }
            }
            sort(up_removable.begin(), up_removable.end());
            sort(down_removable.rbegin(), down_removable.rend());

            vector<int> current_oni_ids;
            for (size_t k = 0; k < up_removable.size(); ++k) {
                current_oni_ids.push_back(up_removable[k].second);
                Operation current_op;
                current_op.benefit = k + 1;
                current_op.cost = 2LL * (up_removable[k].first + 1);
                current_op.score = (double)current_op.benefit / current_op.cost;
                current_op.dir = 'U';
                current_op.index = j;
                current_op.oni_indices = current_oni_ids;
                current_op.shifts = up_removable[k].first + 1;
                if (is_better(current_op, best_op)) {
                    best_op = current_op;
                }
            }

            current_oni_ids.clear();
            for (size_t k = 0; k < down_removable.size(); ++k) {
                current_oni_ids.push_back(down_removable[k].second);
                Operation current_op;
                current_op.benefit = k + 1;
                current_op.cost = 2LL * (N - down_removable[k].first);
                current_op.score = (double)current_op.benefit / current_op.cost;
                current_op.dir = 'D';
                current_op.index = j;
                current_op.oni_indices = current_oni_ids;
                current_op.shifts = N - down_removable[k].first;
                if (is_better(current_op, best_op)) {
                    best_op = current_op;
                }
            }
        }
        
        if (best_op.benefit == 0) {
            break; // No more groups can be removed, switch to fallback
        }

        // Apply the best operation found
        for (int oni_id : best_op.oni_indices) {
            if (!oni_removed[oni_id]) {
                oni_removed[oni_id] = true;
                num_oni_removed++;
            }
        }

        char restore_dir = ' ';
        if (best_op.dir == 'L') restore_dir = 'R';
        if (best_op.dir == 'R') restore_dir = 'L';
        if (best_op.dir == 'U') restore_dir = 'D';
        if (best_op.dir == 'D') restore_dir = 'U';
        
        for (int k = 0; k < best_op.shifts; ++k) {
            solution_moves.push_back({best_op.dir, best_op.index});
        }
        for (int k = 0; k < best_op.shifts; ++k) {
            solution_moves.push_back({restore_dir, best_op.index});
        }
    }

    // Fallback: Remove remaining Oni individually
    for (const auto& oni : oni_list) {
        if (oni_removed[oni.id]) continue;
        
        int r = oni.r;
        int c = oni.c;
        long long min_cost = -1;
        char best_dir = ' ';
        int best_idx = -1;
        int best_shifts = 0;

        if (r < fuku_col_min[c]) {
            long long cost = 2LL * (r + 1);
            if (min_cost == -1 || cost < min_cost) {
                min_cost = cost; best_dir = 'U'; best_idx = c; best_shifts = r + 1;
            }
        }
        if (r > fuku_col_max[c]) {
            long long cost = 2LL * (N - r);
            if (min_cost == -1 || cost < min_cost) {
                min_cost = cost; best_dir = 'D'; best_idx = c; best_shifts = N - r;
            }
        }
        if (c < fuku_row_min[r]) {
            long long cost = 2LL * (c + 1);
            if (min_cost == -1 || cost < min_cost) {
                min_cost = cost; best_dir = 'L'; best_idx = r; best_shifts = c + 1;
            }
        }
        if (c > fuku_row_max[r]) {
            long long cost = 2LL * (N - c);
            if (min_cost == -1 || cost < min_cost) {
                min_cost = cost; best_dir = 'R'; best_idx = r; best_shifts = N - c;
            }
        }

        char restore_dir = ' ';
        if (best_dir == 'L') restore_dir = 'R';
        if (best_dir == 'R') restore_dir = 'L';
        if (best_dir == 'U') restore_dir = 'D';
        if (best_dir == 'D') restore_dir = 'U';

        for (int k = 0; k < best_shifts; ++k) {
            solution_moves.push_back({best_dir, best_idx});
        }
        for (int k = 0; k < best_shifts; ++k) {
            solution_moves.push_back({restore_dir, best_idx});
        }
    }

    for (const auto& move : solution_moves) {
        cout << move.first << " " << move.second << "\n";
    }

    return 0;
}