#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <queue>
#include <tuple>
#include <algorithm>
#include <numeric>

using namespace std;

int n, m, k;
vector<string> initial_grid, target_grid;
vector<pair<int, int>> preset_sizes;
vector<vector<string>> preset_formulas;
vector<vector<int>> preset_counts;

int char_to_int[128];
char int_to_char[62];
int char_map_size = 0;

void build_char_map() {
    int idx = 0;
    for (char c = 'a'; c <= 'z'; ++c) char_to_int[c] = idx++;
    for (char c = 'A'; c <= 'Z'; ++c) char_to_int[c] = idx++;
    for (char c = '0'; c <= '9'; ++c) char_to_int[c] = idx++;
    char_map_size = idx;
    idx = 0;
    for (char c = 'a'; c <= 'z'; ++c) int_to_char[idx++] = c;
    for (char c = 'A'; c <= 'Z'; ++c) int_to_char[idx++] = c;
    for (char c = '0'; c <= '9'; ++c) int_to_char[idx++] = c;
}

vector<int> get_counts(const vector<string>& grid) {
    vector<int> counts(char_map_size, 0);
    for (const auto& row : grid) {
        for (char c : row) {
            counts[char_to_int[c]]++;
        }
    }
    return counts;
}

vector<tuple<int, int, int>> ops;
vector<string> current_grid;

void do_swap(int r1, int c1, int r2, int c2) {
    swap(current_grid[r1 - 1][c1 - 1], current_grid[r2 - 1][c2 - 1]);
    if (r1 == r2) { // horizontal
        if (c1 < c2) ops.emplace_back(-1, r1, c1);
        else ops.emplace_back(-2, r1, c1);
    } else { // vertical
        if (r1 < r2) ops.emplace_back(-4, r1, c1);
        else ops.emplace_back(-3, r1, c1);
    }
}

void bring(int r, int c, int tr, int tc) {
    int cr = r, cc = c;
    while (cc < tc) {
        do_swap(cr, cc, cr, cc + 1);
        cc++;
    }
    while (cc > tc) {
        do_swap(cr, cc, cr, cc - 1);
        cc--;
    }
    while (cr < tr) {
        do_swap(cr, cc, cr + 1, cc);
        cr++;
    }
    while (cr > tr) {
        do_swap(cr, cc, cr - 1, cc);
        cr--;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    build_char_map();

    cin >> n >> m >> k;

    initial_grid.resize(n);
    for (int i = 0; i < n; ++i) cin >> initial_grid[i];
    
    cin.ignore(numeric_limits<streamsize>::max(), '\n');

    target_grid.resize(n);
    for (int i = 0; i < n; ++i) cin >> target_grid[i];
    
    preset_sizes.resize(k);
    preset_formulas.resize(k);
    preset_counts.resize(k, vector<int>(char_map_size, 0));

    for (int i = 0; i < k; ++i) {
        cin.ignore(numeric_limits<streamsize>::max(), '\n');
        int np, mp;
        cin >> np >> mp;
        preset_sizes[i] = {np, mp};
        preset_formulas[i].resize(np);
        for (int j = 0; j < np; ++j) {
            cin >> preset_formulas[i][j];
            for (char c : preset_formulas[i][j]) {
                preset_counts[i][char_to_int[c]]++;
            }
        }
    }

    vector<int> initial_counts = get_counts(initial_grid);
    vector<int> target_counts = get_counts(target_grid);

    vector<int> initial_needed(char_map_size);
    bool all_zero = true;
    for (int i = 0; i < char_map_size; ++i) {
        initial_needed[i] = max(0, target_counts[i] - initial_counts[i]);
        if (initial_needed[i] > 0) all_zero = false;
    }

    vector<int> presets_used;
    if (!all_zero) {
        map<vector<int>, pair<vector<int>, int>> parent;
        map<vector<int>, int> dist;
        queue<vector<int>> q;

        dist[initial_needed] = 0;
        q.push(initial_needed);

        bool found = false;

        while (!q.empty()) {
            vector<int> u = q.front();
            q.pop();

            int d = dist[u];
            
            bool is_goal = true;
            for(int val : u) {
                if(val > 0) { is_goal = false; break; }
            }

            if (is_goal) {
                vector<int> curr = u;
                while (dist.count(curr) && dist[curr] > 0) {
                    auto p = parent[curr];
                    presets_used.push_back(p.second);
                    curr = p.first;
                }
                reverse(presets_used.begin(), presets_used.end());
                found = true;
                break;
            }
            
            if (d >= 400 || presets_used.size() + d >= 400) continue;

            for (int i = 0; i < k; ++i) {
                vector<int> v = u;
                for (int j = 0; j < char_map_size; ++j) {
                    v[j] = max(0, v[j] - preset_counts[i][j]);
                }
                if (dist.find(v) == dist.end()) {
                    dist[v] = d + 1;
                    parent[v] = {u, i};
                    q.push(v);
                }
            }
        }

        if (!found) {
            cout << -1 << endl;
            return 0;
        }
    }

    current_grid = initial_grid;
    
    vector<int> final_counts = initial_counts;
    for (int p_idx : presets_used) {
        for (int i = 0; i < char_map_size; ++i) {
            final_counts[i] += preset_counts[p_idx][i];
        }
    }

    vector<int> discard_counts(char_map_size);
    for (int i = 0; i < char_map_size; ++i) {
        if (final_counts[i] < target_counts[i]) {
            cout << -1 << endl;
            return 0;
        }
        discard_counts[i] = final_counts[i] - target_counts[i];
    }
    
    int preset_cell_r = 1, preset_cell_c = 1;

    for (int p_idx : presets_used) {
        int np = preset_sizes[p_idx].first;
        int mp = preset_sizes[p_idx].second;
        
        vector<pair<int, int>> discard_cells;
        int temp_r = preset_cell_r, temp_c = preset_cell_c;
        for (int i = 0; i < np; ++i) {
            for (int j = 0; j < mp; ++j) {
                discard_cells.push_back({temp_r, temp_c});
                temp_c++;
                if (temp_c > m) {
                    temp_c = 1;
                    temp_r++;
                }
            }
        }
        
        int cell_idx = 0;
        for (int i = 0; i < char_map_size; ++i) {
            char discard_char = int_to_char[i];
            while (discard_counts[i] > 0 && cell_idx < np * mp) {
                int dr = discard_cells[cell_idx].first;
                int dc = discard_cells[cell_idx].second;

                int found_r = -1, found_c = -1;
                for (int r = 1; r <= n; ++r) {
                    for (int c = 1; c <= m; ++c) {
                        if (current_grid[r-1][c-1] == discard_char) {
                             bool is_placed = false;
                             for(int placed_idx = 0; placed_idx < cell_idx; ++placed_idx) {
                                 if (r == discard_cells[placed_idx].first && c == discard_cells[placed_idx].second) {
                                     is_placed = true;
                                     break;
                                 }
                             }
                             if (!is_placed) {
                                 found_r = r;
                                 found_c = c;
                                 goto found_it;
                             }
                        }
                    }
                }
                found_it:;
                bring(found_r, found_c, dr, dc);
                discard_counts[i]--;
                cell_idx++;
            }
        }
        
        ops.emplace_back(p_idx + 1, preset_cell_r, preset_cell_c);
        for(int i=0; i<np; ++i) {
            for(int j=0; j<mp; ++j) {
                current_grid[preset_cell_r+i-1][preset_cell_c+j-1] = preset_formulas[p_idx][i][j];
            }
        }
        preset_cell_c += mp;
        if (preset_cell_c > m) {
            preset_cell_c = 1;
            preset_cell_r += np;
        }
    }

    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= m; ++j) {
            if (current_grid[i - 1][j - 1] != target_grid[i - 1][j - 1]) {
                char target_char = target_grid[i - 1][j - 1];
                int found_r = -1, found_c = -1;
                for (int r = i; r <= n; ++r) {
                    for (int c = 1; c <= m; ++c) {
                        if (r == i && c < j) continue;
                        if (current_grid[r - 1][c - 1] == target_char) {
                            found_r = r;
                            found_c = c;
                            break;
                        }
                    }
                    if (found_r != -1) break;
                }
                bring(found_r, found_c, i, j);
            }
        }
    }

    cout << ops.size() << endl;
    for (const auto& op : ops) {
        cout << get<0>(op) << " " << get<1>(op) << " " << get<2>(op) << "\n";
    }

    return 0;
}