#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <map>
#include <algorithm>
#include <vector>

using namespace std;

struct Preset {
    int id;
    int np, mp;
    vector<string> formula;
};

struct Operation {
    int op, x, y;
};

int n, m, k;
vector<string> initial_grid, target_grid, current_grid;
vector<Preset> presets;
vector<Operation> operations;

vector<vector<vector<int>>> preset_target_matches;
vector<vector<int>> prefix_sum;

void calculate_prefix_sum() {
    prefix_sum.assign(n + 1, vector<int>(m + 1, 0));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            prefix_sum[i + 1][j + 1] = prefix_sum[i][j + 1] + prefix_sum[i + 1][j] - prefix_sum[i][j] +
                                       (current_grid[i][j] == target_grid[i][j]);
        }
    }
}

int query_prefix_sum(int r1, int c1, int r2, int c2) {
    return prefix_sum[r2 + 1][c2 + 1] - prefix_sum[r1][c2 + 1] - prefix_sum[r2 + 1][c1] + prefix_sum[r1][c1];
}

void apply_preset(int p_idx, int r, int c) {
    operations.push_back({presets[p_idx].id, r + 1, c + 1});
    for (int i = 0; i < presets[p_idx].np; ++i) {
        for (int j = 0; j < presets[p_idx].mp; ++j) {
            current_grid[r + i][c + j] = presets[p_idx].formula[i][j];
        }
    }
}

void move_jelly(int r1, int c1, int r2, int c2) {
    // Path: (r1, c1) -> (r2, c1) -> (r2, c2)
    int curr_r = r1;
    while (curr_r > r2) {
        swap(current_grid[curr_r][c1], current_grid[curr_r - 1][c1]);
        operations.push_back({-3, curr_r + 1, c1 + 1});
        curr_r--;
    }
    
    int curr_c = c1;
    while (curr_c > c2) {
        swap(current_grid[r2][curr_c], current_grid[r2][curr_c - 1]);
        operations.push_back({-2, r2 + 1, curr_c + 1});
        curr_c--;
    }
    while (curr_c < c2) {
        swap(current_grid[r2][curr_c], current_grid[r2][curr_c + 1]);
        operations.push_back({-1, r2 + 1, curr_c + 1});
        curr_c++;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m >> k;

    initial_grid.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> initial_grid[i];
    }

    target_grid.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> target_grid[i];
    }

    presets.resize(k);
    for (int i = 0; i < k; ++i) {
        presets[i].id = i + 1;
        cin >> presets[i].np >> presets[i].mp;
        presets[i].formula.resize(presets[i].np);
        for (int j = 0; j < presets[i].np; ++j) {
            cin >> presets[i].formula[j];
        }
    }
    
    current_grid = initial_grid;

    preset_target_matches.resize(k);
    for(int p_idx = 0; p_idx < k; ++p_idx) {
        int np = presets[p_idx].np;
        int mp = presets[p_idx].mp;
        preset_target_matches[p_idx].assign(n - np + 1, vector<int>(m - mp + 1, 0));
        for (int r = 0; r <= n - np; ++r) {
            for (int c = 0; c <= m - mp; ++c) {
                int matches = 0;
                for (int i = 0; i < np; ++i) {
                    for (int j = 0; j < mp; ++j) {
                        if (presets[p_idx].formula[i][j] == target_grid[r + i][c + j]) {
                            matches++;
                        }
                    }
                }
                preset_target_matches[p_idx][r][c] = matches;
            }
        }
    }

    for (int iter = 0; iter < 400; ++iter) {
        calculate_prefix_sum();
        
        int best_score = 0;
        int best_p_idx = -1, best_r = -1, best_c = -1;

        for (int p_idx = 0; p_idx < k; ++p_idx) {
            int np = presets[p_idx].np;
            int mp = presets[p_idx].mp;
            for (int r = 0; r <= n - np; ++r) {
                for (int c = 0; c <= m - mp; ++c) {
                    int correct_before = query_prefix_sum(r, c, r + np - 1, c + mp - 1);
                    int correct_after = preset_target_matches[p_idx][r][c];
                    int score = correct_after - correct_before;
                    if (score > best_score) {
                        best_score = score;
                        best_p_idx = p_idx;
                        best_r = r;
                        best_c = c;
                    }
                }
            }
        }

        if (best_score > 0) {
            apply_preset(best_p_idx, best_r, best_c);
        } else {
            break;
        }
    }

    map<char, int> current_counts, target_counts;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            current_counts[current_grid[i][j]]++;
            target_counts[target_grid[i][j]]++;
        }
    }

    if (current_counts != target_counts) {
        cout << -1 << endl;
        return 0;
    }

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (current_grid[i][j] != target_grid[i][j]) {
                int find_r = -1, find_c = -1;
                for (int r = i; r < n; ++r) {
                    for (int c = (r == i ? j + 1 : 0); c < m; ++c) {
                        if (current_grid[r][c] == target_grid[i][j]) {
                            find_r = r;
                            find_c = c;
                            goto found;
                        }
                    }
                }
            found:
                move_jelly(find_r, find_c, i, j);
            }
        }
    }
    
    cout << operations.size() << endl;
    for (const auto& op : operations) {
        cout << op.op << " " << op.x << " " << op.y << endl;
    }

    return 0;
}