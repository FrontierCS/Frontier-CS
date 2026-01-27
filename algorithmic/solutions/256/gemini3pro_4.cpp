#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <map>

using namespace std;

struct DSU {
    vector<int> parent;
    vector<int> relation; // 0 for same, 1 for different
    int n;

    DSU(int n) : n(n) {
        parent.resize(n);
        iota(parent.begin(), parent.end(), 0);
        relation.assign(n, 0);
    }

    pair<int, int> find(int i) {
        if (parent[i] != i) {
            pair<int, int> root = find(parent[i]);
            parent[i] = root.first;
            relation[i] = (relation[i] ^ root.second);
        }
        return {parent[i], relation[i]};
    }

    // Unite i and j with rel (0: same, 1: diff)
    // Returns true if merged, false if already in same component (check consistency?)
    bool unite(int i, int j, int rel) {
        pair<int, int> root_i = find(i);
        pair<int, int> root_j = find(j);
        if (root_i.first != root_j.first) {
            // relation[i] ^ relation[j] ^ x = rel => x = rel ^ relation[i] ^ relation[j]
            int x = rel ^ root_i.second ^ root_j.second;
            parent[root_i.first] = root_j.first;
            relation[root_i.first] = x;
            return true;
        }
        return false;
    }
    
    // Check if i and j are related with specific relation
    // Returns -1 if not connected, 0/1 otherwise
    int check(int i, int j) {
        pair<int, int> root_i = find(i);
        pair<int, int> root_j = find(j);
        if (root_i.first != root_j.first) return -1;
        return root_i.second ^ root_j.second;
    }
};

int N;
int query_count = 0;

int ask(int r1, int c1, int r2, int c2) {
    cout << "? " << r1 + 1 << " " << c1 + 1 << " " << r2 + 1 << " " << c2 + 1 << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); 
    query_count++;
    return res;
}

int get_id(int r, int c) {
    return r * N + c;
}

bool is_palindrome_path(const vector<vector<int>>& grid, int r1, int c1, int r2, int c2) {
    if (grid[r1][c1] != grid[r2][c2]) return false;
    int dist = (r2 + c2) - (r1 + c1);
    if (dist <= 1) return true; // Adjacent or same -> handled by equality check

    // BFS state: (r_start, c_start, r_end, c_end)
    // We move start forward and end backward.
    // Since we need *exists*, we can just use set of reachable (start, end) pairs.
    // Optimization: step by step.
    vector<pair<int, int>> current_level;
    current_level.push_back({r1 * N + c1, r2 * N + c2});

    int steps = (dist - 1) / 2;
    // For odd total length path (even dist), middle is one cell.
    // For even total length path (odd dist), middle is two cells.
    // Wait, dist is manhattan distance. Path nodes = dist + 1.
    // If dist is even, nodes is odd. Single middle.
    // If dist is odd, nodes is even. Two middles.

    // Just standard BFS for Palindromic Paths logic?
    // We maintain a set of reachable pairs (u, v) at current step k and dist-k.
    // Check if grid[u] == grid[v].
    
    // To avoid huge state, note that we only care if they can meet.
    // We can run DP: can_reach[u][v]
    // But N=50 is small enough for simple layer-by-layer.
    
    vector<pair<int, int>> q;
    q.push_back({get_id(r1, c1), get_id(r2, c2)});
    
    // We need to advance 'steps' times.
    // In each step, u moves R/D, v moves L/U (reverse).
    // Check value equality.
    
    // Wait, simpler:
    // Just simple BFS on state (u, v).
    // State space size roughly (N/2)^2 * 2?
    // Layers are limited.
    
    // Actually simpler:
    // dp[u][v] = true if path u...v is palindrome.
    // Length based recursion.
    // Since we fix grid, we can just run this.
    
    // But wait, the interactive check "exists path"
    // is equivalent to finding a meeting point.
    // Let's implement layer-by-layer reachability.
    
    vector<int> fronts;
    fronts.push_back(get_id(r1, c1));
    vector<int> backs;
    backs.push_back(get_id(r2, c2));
    
    int len = dist + 1;
    int half = (len - 1) / 2;
    
    // Move front 'half' steps
    // Move back 'half' steps
    // Then check intersection or adjacency
    
    // For each step, we expand front to valid neighbors with correct value
    // But value depends on matching with back?
    // This requires coupled movement.
    
    vector<pair<int, int>> layer;
    layer.push_back({get_id(r1, c1), get_id(r2, c2)});
    
    for (int k = 0; k < half; ++k) {
        vector<pair<int, int>> next_layer;
        // sort and unique to keep size down
        sort(layer.begin(), layer.end());
        layer.erase(unique(layer.begin(), layer.end()), layer.end());
        
        if (layer.empty()) return false;
        
        for (auto p : layer) {
            int u = p.first;
            int v = p.second;
            int r_u = u / N, c_u = u % N;
            int r_v = v / N, c_v = v % N;
            
            // Try moves
            int dr[] = {0, 1};
            int dc[] = {1, 0};
            int dr_back[] = {0, -1};
            int dc_back[] = {-1, 0};
            
            for (int i = 0; i < 2; ++i) { // u move
                int nu_r = r_u + dr[i];
                int nu_c = c_u + dc[i];
                if (nu_r >= N || nu_c >= N) continue;
                
                for (int j = 0; j < 2; ++j) { // v move
                    int nv_r = r_v + dr_back[j];
                    int nv_c = c_v + dc_back[j];
                    if (nv_r < 0 || nv_c < 0) continue;
                    
                    if (grid[nu_r][nu_c] == grid[nv_r][nv_c]) {
                        next_layer.push_back({get_id(nu_r, nu_c), get_id(nv_r, nv_c)});
                    }
                }
            }
        }
        layer = next_layer;
    }
    
    if (layer.empty()) return false;
    
    // Check meeting
    // If len is odd, u and v should be same
    // If len is even, u and v should be adjacent
    for (auto p : layer) {
        int u = p.first;
        int v = p.second;
        if (len % 2 == 1) {
            if (u == v) return true;
        } else {
            int r_u = u / N, c_u = u % N;
            int r_v = v / N, c_v = v % N;
            if (abs(r_u - r_v) + abs(c_u - c_v) == 1) return true;
        }
    }
    
    return false;
}

int main() {
    cin >> N;
    
    vector<vector<pair<int, int>>> shells(2 * N);
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            shells[r + c].push_back({r, c});
        }
    }
    
    DSU dsu(N * N);
    
    // 1. Link shells with dist 2 (Same parity linking)
    for (int k = 0; k < 2 * N - 4; ++k) {
        for (auto p : shells[k]) {
            // Try to link to a valid node in shells[k+2]
            // Any node reachable via intermediate is fine
            // Since intermediate is single node, always palindrome.
            // Check reachability:
            // p (k) -> mid (k+1) -> q (k+2)
            // p=(r,c). mids: (r+1,c), (r,c+1).
            // q from mids: (r+2,c), (r+1,c+1), (r,c+2).
            // We just need to link p to ONE q.
            
            vector<pair<int, int>> candidates;
            if (p.first + 2 < N) candidates.push_back({p.first + 2, p.second});
            if (p.first + 1 < N && p.second + 1 < N) candidates.push_back({p.first + 1, p.second + 1});
            if (p.second + 2 < N) candidates.push_back({p.first, p.second + 2});
            
            for (auto q : candidates) {
                // Check if q is in shells[k+2] (it is by coord logic)
                // Query
                // To save queries, check if already connected
                int u = get_id(p.first, p.second);
                int v = get_id(q.first, q.second);
                if (dsu.check(u, v) == -1) {
                    int res = ask(p.first, p.second, q.first, q.second);
                    dsu.unite(u, v, res == 1 ? 0 : 1);
                }
            }
        }
    }
    
    // 2. Symmetric linking (Inside-Out)
    // k goes from n-2 down to 0
    for (int k = N - 2; k >= 0; --k) {
        vector<pair<int, int>>& L = shells[k];
        vector<pair<int, int>>& R = shells[2 * N - 2 - k];
        
        // Try to connect every u in L to some v in R
        for (auto u_coord : L) {
            int u = get_id(u_coord.first, u_coord.second);
            for (auto v_coord : R) {
                int v = get_id(v_coord.first, v_coord.second);
                
                if (dsu.check(u, v) != -1) continue; // Already linked
                
                // Check if valid bridge exists
                // Neighbors of u in k+1
                // Preds of v in 2N-2-k-1
                
                bool bridge_found = false;
                
                vector<pair<int, int>> u_next;
                if (u_coord.first + 1 < N) u_next.push_back({u_coord.first + 1, u_coord.second});
                if (u_coord.second + 1 < N) u_next.push_back({u_coord.first, u_coord.second + 1});
                
                vector<pair<int, int>> v_prev;
                if (v_coord.first > 0) v_prev.push_back({v_coord.first - 1, v_coord.second});
                if (v_coord.second > 0) v_prev.push_back({v_coord.first, v_coord.second - 1});
                
                for (auto un : u_next) {
                    for (auto vp : v_prev) {
                        int un_id = get_id(un.first, un.second);
                        int vp_id = get_id(vp.first, vp.second);
                        
                        // Check if un and vp have SAME value
                        int rel = dsu.check(un_id, vp_id);
                        if (rel == 0) {
                            bridge_found = true;
                            break;
                        }
                    }
                    if (bridge_found) break;
                }
                
                if (bridge_found) {
                    int res = ask(u_coord.first, u_coord.second, v_coord.first, v_coord.second);
                    dsu.unite(u, v, res == 1 ? 0 : 1);
                    break; // Connected u to component
                }
            }
        }
        
        // Connect every v in R to some u in L
        for (auto v_coord : R) {
            int v = get_id(v_coord.first, v_coord.second);
            if (dsu.check(v, get_id(L[0].first, L[0].second)) != -1) continue; // Connected to L-shell component? Approx check
            
            for (auto u_coord : L) {
                int u = get_id(u_coord.first, u_coord.second);
                if (dsu.check(u, v) != -1) continue;
                
                 bool bridge_found = false;
                vector<pair<int, int>> u_next;
                if (u_coord.first + 1 < N) u_next.push_back({u_coord.first + 1, u_coord.second});
                if (u_coord.second + 1 < N) u_next.push_back({u_coord.first, u_coord.second + 1});
                vector<pair<int, int>> v_prev;
                if (v_coord.first > 0) v_prev.push_back({v_coord.first - 1, v_coord.second});
                if (v_coord.second > 0) v_prev.push_back({v_coord.first, v_coord.second - 1});
                
                for (auto un : u_next) {
                    for (auto vp : v_prev) {
                        int un_id = get_id(un.first, un.second);
                        int vp_id = get_id(vp.first, vp.second);
                        if (dsu.check(un_id, vp_id) == 0) {
                            bridge_found = true; break;
                        }
                    }
                    if (bridge_found) break;
                }
                
                if (bridge_found) {
                    int res = ask(u_coord.first, u_coord.second, v_coord.first, v_coord.second);
                    dsu.unite(u, v, res == 1 ? 0 : 1);
                    break;
                }
            }
        }
    }
    
    // 3. Link S_n-1 (Middle) to S_n-3
    if (N >= 3) {
        vector<pair<int, int>>& Mid = shells[N - 1];
        vector<pair<int, int>>& Prev = shells[N - 3];
        for (auto m : Mid) {
            int m_id = get_id(m.first, m.second);
            for (auto p : Prev) {
                // Check reachability p -> ? -> m
                // p=(r,c). m needs to be >= (r,c) + move
                if (m.first >= p.first && m.second >= p.second && (m.first + m.second) == (p.first + p.second) + 2) {
                     // Dist is 2, inner is S_n-2. Always valid.
                     // Just link.
                     int p_id = get_id(p.first, p.second);
                     if (dsu.check(m_id, p_id) == -1) {
                         int res = ask(p.first, p.second, m.first, m.second);
                         dsu.unite(m_id, p_id, res == 1 ? 0 : 1);
                         break; // Linked m
                     }
                }
            }
        }
    }
    
    // Construct solution
    vector<vector<int>> ans(N, vector<int>(N));
    int start = get_id(0, 0);
    int end_node = get_id(N - 1, N - 1);
    
    // Fixed component
    auto fix_comp = [&](int root, int val, vector<vector<int>>& grid) {
        // Iterate all nodes, if in same component, set value
        for (int r = 0; r < N; ++r) {
            for (int c = 0; c < N; ++c) {
                int u = get_id(r, c);
                if (dsu.check(root, u) != -1) {
                    grid[r][c] = val ^ dsu.check(root, u);
                }
            }
        }
    };
    
    // We know (0,0) is 1, (N-1,N-1) is 0
    // They are in Same Parity Component (Even shells).
    // They should be in same DSU component.
    // If not, our linking failed (should not happen with dist 2 queries).
    
    // Fill basic grid
    // There are 2 components: Even-shells and Odd-shells.
    // (0,0) fixes Even shells.
    // Odd shells are floating.
    
    // Fill Even shells
    fix_comp(start, 1, ans);
    
    // Determine Odd shells
    // Need a test query.
    // Try to find a valid query between Even and Odd sets.
    // E.g. (0,0) -> some node in S_3 (if N>=3)
    // Or (0,0) -> S_1 is not possible (dist 1).
    // Try S_n-2 (Odd) to S_n+1 (Even) if n-2 and n+1 dist >= 2.
    // Actually, any cross component query.
    
    // Let's identify the root of Odd component.
    int odd_root = -1;
    if (N > 1) odd_root = get_id(0, 1); // S_1
    
    // If N=1, logic trivial. (N >= 3)
    
    if (odd_root != -1) {
        // Create 2 candidate grids
        vector<vector<int>> grid1 = ans;
        vector<vector<int>> grid2 = ans;
        
        // Fill Odd component for grid1 (assume odd_root = 0)
        fix_comp(odd_root, 0, grid1);
        // Fill Odd component for grid2 (assume odd_root = 1)
        fix_comp(odd_root, 1, grid2);
        
        // Find distinguishing query
        int best_r1 = -1, best_c1 = -1, best_r2 = -1, best_c2 = -1;
        bool found = false;
        
        // Search pairs
        // We can just try a few random pairs or iterate small range
        for (int r1 = 0; r1 < N && !found; ++r1) {
            for (int c1 = 0; c1 < N && !found; ++c1) {
                for (int r2 = r1; r2 < N && !found; ++r2) {
                    for (int c2 = c1; c2 < N && !found; ++c2) {
                        if (r1 == r2 && c1 == c2) continue;
                        if (r1 + c1 + 2 > r2 + c2) continue;
                        if (is_palindrome_path(grid1, r1, c1, r2, c2) != is_palindrome_path(grid2, r1, c1, r2, c2)) {
                            best_r1 = r1; best_c1 = c1; best_r2 = r2; best_c2 = c2;
                            found = true;
                        }
                    }
                }
            }
        }
        
        if (found) {
            int res = ask(best_r1, best_c1, best_r2, best_c2);
            if (is_palindrome_path(grid1, best_r1, best_c1, best_r2, best_c2) == (res == 1)) {
                ans = grid1;
            } else {
                ans = grid2;
            }
        } else {
            // Cannot distinguish? Either is fine?
            ans = grid1;
        }
    }
    
    cout << "!" << endl;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            cout << ans[r][c];
        }
        cout << endl;
    }
    
    return 0;
}