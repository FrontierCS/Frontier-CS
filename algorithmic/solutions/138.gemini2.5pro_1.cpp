#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <map>
#include <algorithm>

using namespace std;

int n, m, k;
vector<string> initial_grid, target_grid;
struct Preset {
    int np, mp;
    vector<string> mat;
};
vector<Preset> presets;

struct Operation {
    int op, r, c;
};
vector<Operation> operations;

vector<string> current_grid;

map<char, int> get_counts(const vector<string>& grid) {
    map<char, int> counts;
    for (const auto& row : grid) {
        for (char c : row) {
            counts[c]++;
        }
    }
    return counts;
}

void apply_op(int op, int r, int c) {
    operations.push_back({op, r, c});
    if (op >= 1) { // Preset
        int p_idx = op - 1;
        for (int i = 0; i < presets[p_idx].np; ++i) {
            for (int j = 0; j < presets[p_idx].mp; ++j) {
                current_grid[r - 1 + i][c - 1 + j] = presets[p_idx].mat[i][j];
            }
        }
    } else { // Swap
        int r1 = r - 1, c1 = c - 1;
        int r2, c2;
        if (op == -1) { r2 = r1; c2 = c1 + 1; }
        else if (op == -2) { r2 = r1; c2 = c1 - 1; }
        else if (op == -3) { r2 = r1 - 1; c2 = c1; }
        else { r2 = r1 + 1; c2 = c1; }
        swap(current_grid[r1][c1], current_grid[r2][c2]);
    }
}

void move_jelly(int r_from, int c_from, int r_to, int c_to) {
    // Path: (r_from, c_from) -> (r_from, c_to) -> (r_to, c_to)
    int r_curr = r_from, c_curr = c_from;
    
    if (c_curr > c_to) {
        for (int c = c_curr; c > c_to; --c) {
            apply_op(-2, r_curr, c);
        }
    } else {
        for (int c = c_curr; c < c_to; ++c) {
            apply_op(-1, r_curr, c);
        }
    }
    c_curr = c_to;

    if (r_curr > r_to) {
        for (int r = r_curr; r > r_to; --r) {
            apply_op(-3, r, c_curr);
        }
    } else {
        for (int r = r_curr; r < r_to; ++r) {
            apply_op(-4, r, c_curr);
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m >> k;
    initial_grid.resize(n);
    target_grid.resize(n);
    for (int i = 0; i < n; ++i) cin >> initial_grid[i];
    for (int i = 0; i < n; ++i) cin >> target_grid[i];

    presets.resize(k);
    for (int i = 0; i < k; ++i) {
        cin >> presets[i].np >> presets[i].mp;
        presets[i].mat.resize(presets[i].np);
        for (int j = 0; j < presets[i].np; ++j) {
            cin >> presets[i].mat[j];
        }
    }

    current_grid = initial_grid;

    map<char, int> target_counts = get_counts(target_grid);

    for (int iter = 0; iter < 400; ++iter) {
        map<char, int> current_counts = get_counts(current_grid);
        if (current_counts == target_counts) {
            break;
        }

        map<char, int> delta;
        for (auto const& [key, val] : current_counts) delta[key] += val;
        for (auto const& [key, val] : target_counts) delta[key] -= val;

        long long best_score = -2e18; 
        int best_p = -1, best_r = -1, best_c = -1;

        for (int p = 0; p < k; ++p) {
            map<char, int> preset_counts = get_counts(presets[p].mat);

            long long preset_goodness = 0;
            for(auto const& [key, val] : preset_counts) {
                if (delta[key] > 0) preset_goodness -= val; 
                else if (delta[key] < 0) preset_goodness += val;
            }

            vector<vector<int>> W(n, vector<int>(m));
            for(int i = 0; i < n; ++i) {
                for (int j = 0; j < m; ++j) {
                    char ch = current_grid[i][j];
                    if (delta[ch] > 0) W[i][j] = 1;
                    else if (delta[ch] < 0) W[i][j] = -1;
                    else W[i][j] = 0;
                }
            }

            vector<vector<long long>> S(n + 1, vector<long long>(m + 1, 0));
            for (int i = 0; i < n; ++i) {
                for (int j = 0; j < m; ++j) {
                    S[i+1][j+1] = W[i][j] + S[i][j+1] + S[i+1][j] - S[i][j];
                }
            }

            for (int r = 1; r <= n - presets[p].np + 1; ++r) {
                for (int c = 1; c <= m - presets[p].mp + 1; ++c) {
                    int r2 = r + presets[p].np - 1;
                    int c2 = c + presets[p].mp - 1;
                    long long removed_goodness = S[r2][c2] - S[r-1][c2] - S[r2][c-1] + S[r-1][c-1];
                    long long current_score = removed_goodness + preset_goodness;
                    if (current_score > best_score) {
                        best_score = current_score;
                        best_p = p + 1;
                        best_r = r;
                        best_c = c;
                    }
                }
            }
        }
        
        if (best_score <= 0) {
            break;
        }

        apply_op(best_p, best_r, best_c);
    }

    map<char, int> final_counts = get_counts(current_grid);
    if (final_counts != target_counts) {
        cout << -1 << endl;
        return 0;
    }

    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= m; ++j) {
            if (current_grid[i-1][j-1] == target_grid[i-1][j-1]) {
                continue;
            }
            
            pair<int, int> found_pos = {-1, -1};
            for (int r = i; r <= n; ++r) {
                for (int c = (r == i ? j + 1 : 1); c <= m; ++c) {
                    if (current_grid[r-1][c-1] == target_grid[i-1][j-1]) {
                        found_pos = {r, c};
                        goto found;
                    }
                }
            }
            found:;
            
            move_jelly(found_pos.first, found_pos.second, i, j);
        }
    }
    
    cout << operations.size() << endl;
    for (const auto& op : operations) {
        cout << op.op << " " << op.r << " " << op.c << endl;
    }

    return 0;
}