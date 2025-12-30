#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <map>
#include <tuple>
#include <algorithm>
#include <array>

using namespace std;

int n, m, k;
vector<string> initial_grid;
vector<string> target_grid;
vector<pair<pair<int, int>, vector<string>>> presets;
vector<string> current_grid;

vector<tuple<int, int, int>> moves;

const int NUM_CHARS = 62;
int char_to_int(char c) {
    if (c >= 'a' && c <= 'z') return c - 'a';
    if (c >= 'A' && c <= 'Z') return c - 'A' + 26;
    return c - '0' + 52;
}

map<char, int> get_counts_map(const vector<string>& grid) {
    map<char, int> counts;
    for (const auto& row : grid) {
        for (char c : row) {
            counts[c]++;
        }
    }
    return counts;
}

array<int, NUM_CHARS> get_counts_array(const vector<string>& grid) {
    array<int, NUM_CHARS> arr{};
    map<char, int> counts = get_counts_map(grid);
    for (auto const& [key, val] : counts) {
        arr[char_to_int(key)] = val;
    }
    return arr;
}

// PSA and related functions
array<vector<vector<int>>, NUM_CHARS> psa;

void build_psa() {
    for (int t = 0; t < NUM_CHARS; ++t) {
        psa[t].assign(n + 1, vector<int>(m + 1, 0));
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= m; ++j) {
                psa[t][i][j] = psa[t][i - 1][j] + psa[t][i][j - 1] - psa[t][i - 1][j - 1] + (char_to_int(current_grid[i - 1][j - 1]) == t);
            }
        }
    }
}

array<int, NUM_CHARS> get_subgrid_counts_psa(int r, int c, int h, int w) {
    array<int, NUM_CHARS> counts{};
    for (int t = 0; t < NUM_CHARS; ++t) {
        counts[t] = psa[t][r + h - 1][c + w - 1] - psa[t][r - 1][c + w - 1] - psa[t][r + h - 1][c - 1] + psa[t][r - 1][c - 1];
    }
    return counts;
}

void apply_preset(int p_idx, int r, int c) {
    int np = presets[p_idx - 1].first.first;
    int mp = presets[p_idx - 1].first.second;
    for (int i = 0; i < np; ++i) {
        for (int j = 0; j < mp; ++j) {
            current_grid[r - 1 + i][c - 1 + j] = presets[p_idx - 1].second[i][j];
        }
    }
    moves.emplace_back(p_idx, r, c);
}

void apply_recorded_swap(int r1, int c1, int r2, int c2) {
    swap(current_grid[r1 - 1][c1 - 1], current_grid[r2 - 1][c2 - 1]);
    if (r1 == r2) { // horizontal
        if (c2 == c1 + 1) moves.emplace_back(-1, r1, c1);
        else moves.emplace_back(-2, r1, c1);
    } else { // vertical
        if (r2 == r1 + 1) moves.emplace_back(-4, r1, c1);
        else moves.emplace_back(-3, r1, c1);
    }
}

void solve_phase2() {
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= m; ++j) {
            if (current_grid[i - 1][j - 1] != target_grid[i - 1][j - 1]) {
                int tr = -1, tc = -1;
                for (int r_search = i; r_search <= n; ++r_search) {
                    for (int c_search = (r_search == i ? j + 1 : 1); c_search <= m; ++c_search) {
                         if (current_grid[r_search - 1][c_search - 1] == target_grid[i - 1][j - 1]) {
                             tr = r_search;
                             tc = c_search;
                             goto found;
                         }
                    }
                }
            found:
                // Move from (tr, tc) to (tr, j)
                if (tc > j) {
                    for (int k = tc; k > j; --k) {
                        apply_recorded_swap(tr, k, tr, k - 1);
                    }
                } else {
                    for (int k = tc; k < j; ++k) {
                        apply_recorded_swap(tr, k, tr, k + 1);
                    }
                }
                // Move from (tr, j) to (i, j)
                for (int k = tr; k > i; --k) {
                    apply_recorded_swap(k, j, k - 1, j);
                }
            }
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
    
    // Skip empty line
    string dummy;
    getline(cin, dummy); 

    for (int i = 0; i < n; ++i) cin >> target_grid[i];
    
    for (int i = 0; i < k; ++i) {
        int np, mp;
        // Skip empty line
        getline(cin, dummy); 
        if(dummy.length() > 0 && dummy[0] != '\r') {
            // This happens if the last line of grid had no newline.
            // The empty line is consumed by `cin >> target_grid[n-1]`.
            // So dummy is now `np mp`.
            sscanf(dummy.c_str(), "%d %d", &np, &mp);
        } else {
            cin >> np >> mp;
        }

        vector<string> p_grid(np);
        for (int j = 0; j < np; ++j) cin >> p_grid[j];
        presets.push_back({{np, mp}, p_grid});
    }

    current_grid = initial_grid;
    array<int, NUM_CHARS> target_counts = get_counts_array(target_grid);
    vector<array<int, NUM_CHARS>> preset_counts;
    for(const auto& p : presets) {
        preset_counts.push_back(get_counts_array(p.second));
    }

    int preset_ops_count = 0;
    for (int iter = 0; iter < 400 && preset_ops_count < 400; ++iter) {
        array<int, NUM_CHARS> current_counts = get_counts_array(current_grid);
        
        bool done = true;
        for(int t=0; t<NUM_CHARS; ++t) {
            if (current_counts[t] != target_counts[t]) {
                done = false;
                break;
            }
        }
        if (done) break;

        long long current_l1_dist = 0;
        for (int t = 0; t < NUM_CHARS; ++t) {
            current_l1_dist += abs(target_counts[t] - current_counts[t]);
        }
        
        build_psa();

        long long best_reduction = 0;
        tuple<int, int, int> best_move = {-1, -1, -1};

        for (int p_idx = 1; p_idx <= k; ++p_idx) {
            int np = presets[p_idx - 1].first.first;
            int mp = presets[p_idx - 1].first.second;
            for (int r = 1; r <= n - np + 1; ++r) {
                for (int c = 1; c <= m - mp + 1; ++c) {
                    array<int, NUM_CHARS> sub_counts = get_subgrid_counts_psa(r, c, np, mp);
                    array<int, NUM_CHARS> next_counts = current_counts;
                    
                    for(int t=0; t<NUM_CHARS; ++t){
                        next_counts[t] -= sub_counts[t];
                        next_counts[t] += preset_counts[p_idx-1][t];
                    }

                    long long next_l1_dist = 0;
                    for (int t = 0; t < NUM_CHARS; ++t) {
                        next_l1_dist += abs(target_counts[t] - next_counts[t]);
                    }

                    if (current_l1_dist - next_l1_dist > best_reduction) {
                        best_reduction = current_l1_dist - next_l1_dist;
                        best_move = {p_idx, r, c};
                    }
                }
            }
        }

        if (get<0>(best_move) == -1) {
            break; 
        }

        apply_preset(get<0>(best_move), get<1>(best_move), get<2>(best_move));
        preset_ops_count++;
    }

    array<int, NUM_CHARS> final_counts = get_counts_array(current_grid);
    bool ok = true;
    for(int t=0; t<NUM_CHARS; ++t) if(final_counts[t] != target_counts[t]) ok = false;

    if (!ok) {
        cout << -1 << endl;
        return 0;
    }

    solve_phase2();

    cout << moves.size() << endl;
    for (const auto& move : moves) {
        cout << get<0>(move) << " " << get<1>(move) << " " << get<2>(move) << endl;
    }

    return 0;
}