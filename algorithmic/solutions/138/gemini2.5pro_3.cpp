#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <tuple>

using namespace std;

int n, m, k;
vector<string> initial_grid, target_grid;
vector<pair<int, int>> preset_dims;
vector<vector<string>> presets;

struct Operation {
    int op, r, c;
};

void apply_swap(vector<string>& grid, int r1, int c1, int r2, int c2) {
    swap(grid[r1 - 1][c1 - 1], grid[r2 - 1][c2 - 1]);
}

void apply_preset(vector<string>& grid, int p_idx, int r, int c) {
    int np = preset_dims[p_idx - 1].first;
    int mp = preset_dims[p_idx - 1].second;
    for (int i = 0; i < np; ++i) {
        for (int j = 0; j < mp; ++j) {
            grid[r + i - 1][c + j - 1] = presets[p_idx - 1][i][j];
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
    
    string dummy;
    while(cin.peek() == '\n' || cin.peek() == '\r' || cin.peek() == ' ') {
        if(cin.peek() == '\n' || cin.peek() == '\r') getline(cin, dummy);
        else cin.get();
    }
    
    for (int i = 0; i < n; ++i) cin >> target_grid[i];
    
    presets.resize(k);
    preset_dims.resize(k);
    for (int i = 0; i < k; ++i) {
        while(cin.peek() == '\n' || cin.peek() == '\r' || cin.peek() == ' ') {
            if(cin.peek() == '\n' || cin.peek() == '\r') getline(cin, dummy);
            else cin.get();
        }
        int np, mp;
        cin >> np >> mp;
        preset_dims[i] = {np, mp};
        presets[i].resize(np);
        for (int j = 0; j < np; ++j) cin >> presets[i][j];
    }

    vector<string> current_grid = initial_grid;
    vector<Operation> ops;

    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= m; ++j) {
            while (current_grid[i - 1][j - 1] != target_grid[i - 1][j - 1]) {
                pair<int, int> found_pos = {-1, -1};
                int min_dist = 1e9;

                for (int r = i; r <= n; ++r) {
                    for (int c = 1; c <= m; ++c) {
                        if (r == i && c < j) continue;
                        if (current_grid[r - 1][c - 1] == target_grid[i - 1][j - 1]) {
                            int dist = (r - i) + abs(c - j);
                            if (dist < min_dist) {
                                min_dist = dist;
                                found_pos = {r, c};
                            }
                        }
                    }
                }
                
                if (found_pos.first != -1) {
                    int cur_r = found_pos.first;
                    int cur_c = found_pos.second;

                    if (cur_c > j) {
                        for (int c = cur_c; c > j; --c) {
                            ops.push_back({-2, cur_r, c});
                            apply_swap(current_grid, cur_r, c, cur_r, c - 1);
                        }
                    } else {
                        for (int c = cur_c; c < j; ++c) {
                            ops.push_back({-1, cur_r, c});
                            apply_swap(current_grid, cur_r, c, cur_r, c + 1);
                        }
                    }
                    cur_c = j;
                    
                    for (int r = cur_r; r > i; --r) {
                        ops.push_back({-3, r, cur_c});
                        apply_swap(current_grid, r, cur_c, r - 1, cur_c);
                    }
                } else {
                    int best_p = -1, best_r = -1, best_c = -1;
                    int max_score = -1;

                    for (int p = 1; p <= k; ++p) {
                        int np = preset_dims[p - 1].first;
                        int mp = preset_dims[p - 1].second;
                        for (int r_start = 1; r_start <= n - np + 1; ++r_start) {
                            for (int c_start = 1; c_start <= m - mp + 1; ++c_start) {
                                bool generates_needed = false;
                                for(int dr = 0; dr < np; ++dr) {
                                    for(int dc = 0; dc < mp; ++dc) {
                                        int cur_r = r_start + dr;
                                        int cur_c = c_start + dc;
                                        if (cur_r > i || (cur_r == i && cur_c >= j)) {
                                            if (presets[p - 1][dr][dc] == target_grid[i - 1][j - 1]) {
                                                generates_needed = true;
                                                break;
                                            }
                                        }
                                    }
                                    if(generates_needed) break;
                                }

                                if(generates_needed) {
                                    int score = 0;
                                    for(int dr = 0; dr < np; ++dr) {
                                        for(int dc = 0; dc < mp; ++dc) {
                                            int cur_r = r_start + dr;
                                            int cur_c = c_start + dc;
                                            if (cur_r > i || (cur_r == i && cur_c >= j)) {
                                                if (presets[p-1][dr][dc] == target_grid[cur_r - 1][cur_c - 1] && current_grid[cur_r - 1][cur_c - 1] != target_grid[cur_r-1][cur_c-1]) {
                                                    score++;
                                                }
                                            }
                                        }
                                    }
                                    if (score > max_score) {
                                        max_score = score;
                                        best_p = p;
                                        best_r = r_start;
                                        best_c = c_start;
                                    }
                                }
                            }
                        }
                    }

                    if (best_p == -1) {
                        cout << -1 << endl;
                        return 0;
                    }
                    
                    ops.push_back({best_p, best_r, best_c});
                    apply_preset(current_grid, best_p, best_r, best_c);
                }
            }
        }
    }

    if (ops.size() > 400000) {
        cout << -1 << endl;
        return 0;
    }
    int preset_count = 0;
    for(const auto& op : ops) if (op.op >= 1) preset_count++;
    if (preset_count > 400) {
        cout << -1 << endl;
        return 0;
    }

    cout << ops.size() << endl;
    for (const auto& op : ops) {
        cout << op.op << " " << op.r << " " << op.c << endl;
    }

    return 0;
}