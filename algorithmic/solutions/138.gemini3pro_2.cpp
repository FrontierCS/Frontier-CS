#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <queue>
#include <set>

using namespace std;

// Globals
int N, M, K;
vector<string> initial_grid;
vector<string> target_grid;
struct Preset {
    int h, w;
    vector<string> grid;
    map<char, int> counts;
    int id;
};
vector<Preset> presets;

// Operations
struct Op {
    int type; // -4 to 0 for moves/rotates, 1..k for presets
    int x, y; // 1-based
};
vector<Op> history;

// Current state
vector<string> current_grid;

// Helper to check coordinates
bool valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < M;
}

// Add operation
void add_op(int type, int x, int y) {
    history.push_back({type, x, y});
}

// Apply primitive operations to current_grid for tracking
void apply_swap(int r1, int c1, int r2, int c2) {
    swap(current_grid[r1][c1], current_grid[r2][c2]);
}

void do_swap(int r, int c, int dir) {
    // dir: 0=down, 1=up, 2=left, 3=right
    // Op codes:
    // -4 x y: swaps (x,y) and (x+1,y)  (down)
    // -3 x y: swaps (x,y) and (x-1,y)  (up)
    // -2 x y: swaps (x,y) and (x,y-1)  (left)
    // -1 x y: swaps (x,y) and (x,y+1)  (right)
    int nr = r, nc = c;
    int op_code = 0;
    if (dir == 0) { nr++; op_code = -4; }
    else if (dir == 1) { nr--; op_code = -3; }
    else if (dir == 2) { nc--; op_code = -2; }
    else if (dir == 3) { nc++; op_code = -1; }
    
    add_op(op_code, r + 1, c + 1);
    apply_swap(r, c, nr, nc);
}

// BFS to move src to dst without touching locked
// locked cells are those lexicographically < (limit_r, limit_c)
bool move_char(int src_r, int src_c, int dst_r, int dst_c, int limit_r, int limit_c) {
    if (src_r == dst_r && src_c == dst_c) return true;
    
    // BFS to find path
    queue<pair<int, int>> q;
    q.push({src_r, src_c});
    vector<vector<pair<int, int>>> parent(N, vector<pair<int, int>>(M, {-1, -1}));
    vector<vector<bool>> visited(N, vector<bool>(M, false));
    visited[src_r][src_c] = true;
    
    bool found = false;
    int dr[] = {1, -1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    
    while (!q.empty()) {
        auto [r, c] = q.front();
        q.pop();
        
        if (r == dst_r && c == dst_c) {
            found = true;
            break;
        }
        
        for (int i = 0; i < 4; i++) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            
            if (valid(nr, nc) && !visited[nr][nc]) {
                bool is_locked = (nr < limit_r) || (nr == limit_r && nc < limit_c);
                if (!is_locked) {
                    visited[nr][nc] = true;
                    parent[nr][nc] = {r, c};
                    q.push({nr, nc});
                }
            }
        }
    }
    
    if (!found) return false;
    
    // Reconstruct path
    vector<pair<int, int>> path;
    int cur_r = dst_r, cur_c = dst_c;
    while (cur_r != src_r || cur_c != src_c) {
        path.push_back({cur_r, cur_c});
        auto p = parent[cur_r][cur_c];
        cur_r = p.first;
        cur_c = p.second;
    }
    path.push_back({src_r, src_c});
    reverse(path.begin(), path.end());
    
    // Execute swaps along path
    for (size_t i = 0; i < path.size() - 1; i++) {
        int r1 = path[i].first;
        int c1 = path[i].second;
        int r2 = path[i+1].first;
        int c2 = path[i+1].second;
        
        if (r2 == r1 + 1) do_swap(r1, c1, 0);
        else if (r2 == r1 - 1) do_swap(r1, c1, 1);
        else if (c2 == c1 - 1) do_swap(r1, c1, 2);
        else if (c2 == c1 + 1) do_swap(r1, c1, 3);
    }
    return true;
}

// Counts map
map<char, int> get_counts(int start_r, int start_c) {
    map<char, int> cnts;
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < M; c++) {
            if (r > start_r || (r == start_r && c >= start_c)) {
                cnts[current_grid[r][c]]++;
            }
        }
    }
    return cnts;
}

map<char, int> get_needed(int start_r, int start_c) {
    map<char, int> cnts;
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < M; c++) {
            if (r > start_r || (r == start_r && c >= start_c)) {
                cnts[target_grid[r][c]]++;
            }
        }
    }
    return cnts;
}

bool can_spawn_later(char c, int next_r, int next_c) {
    for (const auto& p : presets) {
        if (p.counts.count(c) && p.counts.at(c) > 0) {
            for (int pr = 0; pr <= N - p.h; pr++) {
                for (int pc = 0; pc <= M - p.w; pc++) {
                    if (pr > next_r || (pr == next_r && pc >= next_c)) {
                        return true;
                    }
                }
            }
        }
    }
    return false;
}

void apply_preset(int p_idx, int pr, int pc, int limit_r, int limit_c) {
    const auto& p = presets[p_idx];
    
    auto needed = get_needed(limit_r, limit_c);
    auto have = get_counts(limit_r, limit_c);
    
    vector<pair<int, int>> valuable_pos;
    vector<pair<int, int>> safe_pos;
    
    // Identify valuable characters to evacuate
    for (int r = 0; r < N; r++) {
        for (int c = 0; c < M; c++) {
            if (r > limit_r || (r == limit_r && c >= limit_c)) {
                bool inside = (r >= pr && r < pr + p.h && c >= pc && c < pc + p.w);
                char ch = current_grid[r][c];
                bool is_valuable = (needed[ch] >= have[ch]);
                
                if (inside && is_valuable) {
                    valuable_pos.push_back({r, c});
                } else if (!inside) {
                    if (!is_valuable) {
                        safe_pos.push_back({r, c});
                    }
                }
            }
        }
    }
    
    int moves = min(valuable_pos.size(), safe_pos.size());
    for (int i = 0; i < moves; i++) {
        move_char(valuable_pos[i].first, valuable_pos[i].second, 
                  safe_pos[i].first, safe_pos[i].second, limit_r, limit_c);
    }
    
    // Apply preset
    add_op(p.id, pr + 1, pc + 1);
    for (int r = 0; r < p.h; r++) {
        for (int c = 0; c < p.w; c++) {
            current_grid[pr + r][pc + c] = p.grid[r][c];
        }
    }
}

bool spawn_char(char target, int limit_r, int limit_c) {
    for (int i = 0; i < K; i++) {
        if (presets[i].counts.count(target) && presets[i].counts.at(target) > 0) {
            const auto& p = presets[i];
            for (int pr = 0; pr <= N - p.h; pr++) {
                for (int pc = 0; pc <= M - p.w; pc++) {
                    if (pr > limit_r || (pr == limit_r && pc >= limit_c)) {
                        apply_preset(i, pr, pc, limit_r, limit_c);
                        return true;
                    }
                }
            }
        }
    }
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M >> K)) return 0;
    
    initial_grid.resize(N);
    for (int i = 0; i < N; i++) cin >> initial_grid[i];
    
    target_grid.resize(N);
    string dummy; getline(cin, dummy); // skip newline
    for (int i = 0; i < N; i++) cin >> target_grid[i];
    
    for (int i = 0; i < K; i++) {
        int np, mp;
        cin >> np >> mp;
        Preset p;
        p.h = np; p.w = mp;
        p.id = i + 1;
        p.grid.resize(np);
        for (int r = 0; r < np; r++) {
            cin >> p.grid[r];
            for (char c : p.grid[r]) p.counts[c]++;
        }
        presets.push_back(p);
    }
    
    current_grid = initial_grid;
    
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < M; j++) {
            // Phase 1: Pre-emptive spawning
            int next_r = i, next_c = j + 1;
            if (next_c == M) { next_r++; next_c = 0; }
            
            map<char, int> needed = get_needed(i, j);
            map<char, int> have = get_counts(i, j);
            
            for (auto const& [ch, count] : needed) {
                if (have[ch] < count) {
                    if (!can_spawn_later(ch, next_r, next_c)) {
                        while (have[ch] < count) {
                            if (!spawn_char(ch, i, j)) {
                                cout << -1 << endl;
                                return 0;
                            }
                            have = get_counts(i, j);
                        }
                    }
                }
            }
            
            // Phase 2: Current cell satisfaction
            char target = target_grid[i][j];
            have = get_counts(i, j);
            if (have[target] == 0) {
                if (!spawn_char(target, i, j)) {
                    cout << -1 << endl;
                    return 0;
                }
                have = get_counts(i, j);
            }
            
            // Phase 3: Move to position
            int tr = -1, tc = -1;
            int dist = 10000;
            
            for (int r = 0; r < N; r++) {
                for (int c = 0; c < M; c++) {
                    if (r > i || (r == i && c >= j)) {
                        if (current_grid[r][c] == target) {
                            int d = abs(r - i) + abs(c - j);
                            if (d < dist) {
                                dist = d;
                                tr = r;
                                tc = c;
                            }
                        }
                    }
                }
            }
            
            if (tr == -1) {
                cout << -1 << endl;
                return 0;
            }
            
            move_char(tr, tc, i, j, i, j);
        }
    }
    
    cout << history.size() << "\n";
    for (const auto& op : history) {
        cout << op.type << " " << op.x << " " << op.y << "\n";
    }

    return 0;
}