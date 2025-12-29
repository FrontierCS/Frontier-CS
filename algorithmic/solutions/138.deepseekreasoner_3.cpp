#include <bits/stdc++.h>
using namespace std;

int n, m, k;
vector<string> initial_grid, target_grid;

struct Preset {
    int h, w;
    vector<string> pattern;
    array<int,62> cnt;
};
vector<Preset> presets;

using Counts = array<int,62>;

Counts initial_counts, target_counts;

int char_to_idx(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'Z') return 10 + (c - 'A');
    if (c >= 'a' && c <= 'z') return 36 + (c - 'a');
    return -1;
}
char idx_to_char(int i) {
    if (i < 10) return '0' + i;
    if (i < 36) return 'A' + (i - 10);
    return 'a' + (i - 36);
}

Counts count_grid(const vector<string>& g) {
    Counts cnt = {0};
    for (const string& s : g) {
        for (char c : s) {
            cnt[char_to_idx(c)]++;
        }
    }
    return cnt;
}

struct Operation {
    int op, x, y;
};
vector<Operation> ops;

void swap_up(vector<string>& grid, int x, int y) {
    swap(grid[x][y], grid[x-1][y]);
    ops.push_back({-3, x+1, y+1});
}
void swap_down(vector<string>& grid, int x, int y) {
    swap(grid[x][y], grid[x+1][y]);
    ops.push_back({-4, x+1, y+1});
}
void swap_left(vector<string>& grid, int x, int y) {
    swap(grid[x][y], grid[x][y-1]);
    ops.push_back({-2, x+1, y+1});
}
void swap_right(vector<string>& grid, int x, int y) {
    swap(grid[x][y], grid[x][y+1]);
    ops.push_back({-1, x+1, y+1});
}

void move_cell_to(vector<string>& grid, int src_x, int src_y, int dst_x, int dst_y) {
    while (src_x > dst_x) {
        swap_up(grid, src_x, src_y);
        src_x--;
    }
    while (src_x < dst_x) {
        swap_down(grid, src_x, src_y);
        src_x++;
    }
    while (src_y > dst_y) {
        swap_left(grid, src_x, src_y);
        src_y--;
    }
    while (src_y < dst_y) {
        swap_right(grid, src_x, src_y);
        src_y++;
    }
}

void rearrange_rectangle(vector<string>& grid, int x, int y, int h, int w, const Counts& desired) {
    Counts cur = {0};
    for (int i = x; i < x+h; ++i)
        for (int j = y; j < y+w; ++j)
            cur[char_to_idx(grid[i][j])]++;
    array<int,62> deficit;
    for (int t = 0; t < 62; ++t)
        deficit[t] = desired[t] - cur[t];
    for (int i = x; i < x+h; ++i) {
        for (int j = y; j < y+w; ++j) {
            int t = char_to_idx(grid[i][j]);
            if (deficit[t] <= 0) {
                int s = -1;
                for (int tt = 0; tt < 62; ++tt)
                    if (deficit[tt] > 0) { s = tt; break; }
                if (s == -1) return;
                int ox = -1, oy = -1;
                for (int ii = 0; ii < n; ++ii) {
                    for (int jj = 0; jj < m; ++jj) {
                        if (ii >= x && ii < x+h && jj >= y && jj < y+w) continue;
                        if (char_to_idx(grid[ii][jj]) == s) {
                            ox = ii; oy = jj;
                            break;
                        }
                    }
                    if (ox != -1) break;
                }
                if (ox == -1) continue;
                move_cell_to(grid, ox, oy, i, j);
                deficit[t]++;
                deficit[s]--;
            } else {
                deficit[t]--;
            }
        }
    }
}

void permute_to_target(vector<string>& grid, const vector<string>& target) {
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (grid[i][j] == target[i][j]) continue;
            int i2 = -1, j2 = -1;
            for (int ii = i; ii < n; ++ii) {
                int start_j = (ii == i) ? j : 0;
                for (int jj = start_j; jj < m; ++jj) {
                    if (grid[ii][jj] == target[i][j]) {
                        i2 = ii; j2 = jj;
                        break;
                    }
                }
                if (i2 != -1) break;
            }
            if (i2 == -1) continue;
            move_cell_to(grid, i2, j2, i, j);
        }
    }
}

Counts compute_removal(const Counts& c, int pid) {
    const Preset& pre = presets[pid];
    int S = pre.h * pre.w;
    Counts r = {0};
    array<int,62> excess;
    int total_excess = 0;
    for (int t = 0; t < 62; ++t) {
        excess[t] = max(0, c[t] - target_counts[t]);
        total_excess += excess[t];
    }
    if (total_excess >= S) {
        int sum_assigned = 0;
        for (int t = 0; t < 62; ++t) {
            if (excess[t] > 0) {
                r[t] = (S * excess[t]) / total_excess;
                sum_assigned += r[t];
            }
        }
        if (sum_assigned < S) {
            vector<pair<int,int>> rem;
            for (int t = 0; t < 62; ++t)
                if (excess[t] > r[t])
                    rem.push_back({excess[t] - r[t], t});
            sort(rem.begin(), rem.end(), greater<pair<int,int>>());
            for (auto& p : rem) {
                int add = min(p.first, S - sum_assigned);
                r[p.second] += add;
                sum_assigned += add;
                if (sum_assigned == S) break;
            }
        }
    } else {
        for (int t = 0; t < 62; ++t) {
            r[t] = excess[t];
        }
        int remaining = S - total_excess;
        vector<pair<int,int>> cand;
        for (int t = 0; t < 62; ++t) {
            if (c[t] > r[t]) cand.push_back({c[t], t});
        }
        sort(cand.begin(), cand.end(), greater<pair<int,int>>());
        for (auto& p : cand) {
            int t = p.second;
            int can_remove = min(c[t] - r[t], remaining);
            r[t] += can_remove;
            remaining -= can_remove;
            if (remaining == 0) break;
        }
        if (remaining > 0) return Counts();
    }
    int sum_r = 0;
    for (int t = 0; t < 62; ++t) {
        if (r[t] > c[t]) r[t] = c[t];
        sum_r += r[t];
    }
    if (sum_r < S) {
        int need = S - sum_r;
        for (int t = 0; t < 62 && need > 0; ++t) {
            int add = min(c[t] - r[t], need);
            r[t] += add;
            need -= add;
        }
    } else if (sum_r > S) {
        int need = sum_r - S;
        for (int t = 0; t < 62 && need > 0; ++t) {
            int sub = min(r[t], need);
            r[t] -= sub;
            need -= sub;
        }
    }
    return r;
}

struct CountsHash {
    size_t operator()(const Counts& c) const {
        size_t h = 0;
        for (int x : c) h = h * 123456789 + x;
        return h;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n >> m >> k;
    initial_grid.resize(n);
    for (int i = 0; i < n; ++i) cin >> initial_grid[i];
    string empty_line;
    getline(cin, empty_line);
    getline(cin, empty_line);
    target_grid.resize(n);
    for (int i = 0; i < n; ++i) cin >> target_grid[i];
    presets.resize(k);
    for (int i = 0; i < k; ++i) {
        getline(cin, empty_line);
        int np, mp;
        cin >> np >> mp;
        presets[i].h = np; presets[i].w = mp;
        presets[i].pattern.resize(np);
        for (int j = 0; j < np; ++j) cin >> presets[i].pattern[j];
        presets[i].cnt = count_grid(presets[i].pattern);
    }
    initial_counts = count_grid(initial_grid);
    target_counts = count_grid(target_grid);
    if (initial_counts == target_counts) {
        vector<string> grid = initial_grid;
        permute_to_target(grid, target_grid);
        cout << ops.size() << "\n";
        for (auto& op : ops) cout << op.op << " " << op.x << " " << op.y << "\n";
        return 0;
    }
    vector<Counts> state_cnt;
    vector<int> state_parent, state_preset;
    vector<Counts> state_removal;
    unordered_set<Counts, CountsHash> visited;
    queue<int> q;
    state_cnt.push_back(initial_counts);
    state_parent.push_back(-1);
    state_preset.push_back(-1);
    state_removal.push_back(Counts());
    q.push(0);
    visited.insert(initial_counts);
    int target_idx = -1;
    while (!q.empty() && state_cnt.size() < 20000) {
        int u = q.front(); q.pop();
        Counts c = state_cnt[u];
        for (int i = 0; i < k; ++i) {
            Counts r = compute_removal(c, i);
            int S = presets[i].h * presets[i].w;
            int sum_r = 0;
            bool valid = true;
            for (int t = 0; t < 62; ++t) {
                if (r[t] < 0 || r[t] > c[t]) { valid = false; break; }
                sum_r += r[t];
            }
            if (!valid || sum_r != S) continue;
            Counts nc = c;
            for (int t = 0; t < 62; ++t) {
                nc[t] = nc[t] - r[t] + presets[i].cnt[t];
                if (nc[t] < 0) { valid = false; break; }
            }
            if (!valid) continue;
            if (visited.find(nc) != visited.end()) continue;
            visited.insert(nc);
            state_cnt.push_back