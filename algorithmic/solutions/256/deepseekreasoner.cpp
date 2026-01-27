#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

using namespace std;

// Disjoint Set Union with parity tracking
struct DSU {
    vector<int> parent;
    vector<int> val; // 0 or 1, relative to parent

    DSU(int n) {
        parent.resize(n);
        iota(parent.begin(), parent.end(), 0);
        val.assign(n, 0);
    }

    // Returns {root, parity relative to root}
    pair<int, int> find(int i) {
        if (parent[i] == i)
            return {i, 0};
        pair<int, int> root = find(parent[i]);
        parent[i] = root.first;
        val[i] = val[i] ^ root.second;
        return {parent[i], val[i]};
    }

    // Unite i and j with relation rel = val[i] ^ val[j]
    void unite(int i, int j, int rel) {
        pair<int, int> root_i = find(i);
        pair<int, int> root_j = find(j);
        if (root_i.first != root_j.first) {
            parent[root_i.first] = root_j.first;
            // val[root_i] ^ new_edge ^ val[root_j] = rel
            // new_edge = val[root_i] ^ val[root_j] ^ rel
            val[root_i.first] = root_i.second ^ root_j.second ^ rel;
        }
    }
};

int n;
int grid[55][55]; // stores final values
int id[55][55]; // continuous index mapping

int query(int r1, int c1, int r2, int c2) {
    cout << "? " << r1 << " " << c1 << " " << r2 << " " << c2 << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

vector<pair<int, int>> get_layer(int k) {
    vector<pair<int, int>> cells;
    for (int r = 1; r <= n; ++r) {
        int c = k + 2 - r;
        if (c >= 1 && c <= n) {
            cells.push_back({r, c});
        }
    }
    return cells;
}

bool isValid(int r, int c) {
    return r >= 1 && r <= n && c >= 1 && c <= n;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    int idx_counter = 0;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            id[i][j] = idx_counter++;
            grid[i][j] = -1;
        }
    }

    DSU dsu(n * n);

    // Process symmetric layers from center (layer n-2) outwards to 0
    for (int k = n - 2; k >= 0; --k) {
        vector<pair<int, int>> Sk = get_layer(k);
        vector<pair<int, int>> Sk_conj = get_layer(2 * n - 2 - k);

        // Try to connect component of u with component of v
        for (auto u : Sk) {
            for (auto v : Sk_conj) {
                // If already connected, no need to query
                if (dsu.find(id[u.first][u.second]).first == dsu.find(id[v.first][v.second]).first) continue;

                bool can_query = false;
                if (k == n - 2) {
                    // At center boundary, we check if u and v share a neighbor in S_{n-1}.
                    // Path: u -> m -> v.
                    vector<pair<int, int>> children_u;
                    if (isValid(u.first + 1, u.second)) children_u.push_back({u.first + 1, u.second});
                    if (isValid(u.first, u.second + 1)) children_u.push_back({u.first, u.second + 1});

                    for (auto m : children_u) {
                        // Check if m is neighbor of v (m is parent of v)
                        if (abs(m.first - v.first) + abs(m.second - v.second) == 1) {
                            can_query = true;
                            break;
                        }
                    }
                } else {
                    // For outer layers, check if there's an inner palindrome path.
                    // u -> u' ... v' -> v. u' in S_{k+1}, v' in S_{conj+1} (i.e. parent of v)
                    // We need known relation A[u'] == A[v'].
                    
                    vector<pair<int, int>> children_u;
                    if (isValid(u.first + 1, u.second)) children_u.push_back({u.first + 1, u.second});
                    if (isValid(u.first, u.second + 1)) children_u.push_back({u.first, u.second + 1});
                    
                    vector<pair<int, int>> parents_v;
                    if (isValid(v.first - 1, v.second)) parents_v.push_back({v.first - 1, v.second});
                    if (isValid(v.first, v.second - 1)) parents_v.push_back({v.first, v.second - 1});

                    for (auto u_inner : children_u) {
                        for (auto v_inner : parents_v) {
                            int uid = id[u_inner.first][u_inner.second];
                            int vid = id[v_inner.first][v_inner.second];
                            pair<int, int> root_u = dsu.find(uid);
                            pair<int, int> root_v = dsu.find(vid);
                            // Must be in same component since we solved inner layers
                            if (root_u.first == root_v.first) {
                                if (root_u.second == root_v.second) { // Values equal
                                    can_query = true;
                                    goto found_path;
                                }
                            }
                        }
                    }
                    found_path:;
                }

                if (can_query) {
                    int result = query(u.first, u.second, v.first, v.second);
                    // result 1 => palindrome => A[u] == A[v]
                    // result 0 => not palindrome. inner part was palindrome => A[u] != A[v]
                    dsu.unite(id[u.first][u.second], id[v.first][v.second], 1 - result);
                }
            }
        }
    }

    // Fill grid for determines cells.
    // Fix (1,1) to 1.
    pair<int, int> root1 = dsu.find(id[1][1]);
    int global_flip = 1 ^ root1.second; 

    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (i + j == n + 1) continue; // Skip center S_{n-1}
            pair<int, int> info = dsu.find(id[i][j]);
            if (info.first == root1.first) {
                grid[i][j] = info.second ^ global_flip;
            } else {
                pair<int, int> rootN = dsu.find(id[n][n]);
                if (info.first == rootN.first) {
                     // If (1,1) and (n,n) are disjoint (unlikely), base on (n,n)=0
                     int flipN = 0 ^ rootN.second;
                     grid[i][j] = info.second ^ flipN;
                }
            }
        }
    }

    // Solve Center Layer S_{n-1}
    vector<pair<int, int>> center = get_layer(n - 1);
    for (auto m : center) {
        bool determined = false;
        
        // Strategy 1: check relation with neighbor w in S_n
        // path u -> m -> w -> v, match A[u] == A[v]
        vector<pair<int, int>> neighbors_n; 
        if (isValid(m.first + 1, m.second)) neighbors_n.push_back({m.first + 1, m.second});
        if (isValid(m.first, m.second + 1)) neighbors_n.push_back({m.first, m.second + 1});

        for (auto w : neighbors_n) {
            if (determined) break;
            vector<pair<int, int>> children_w;
            if (isValid(w.first + 1, w.second)) children_w.push_back({w.first + 1, w.second});
            if (isValid(w.first, w.second + 1)) children_w.push_back({w.first, w.second + 1});
            vector<pair<int, int>> parents_m;
            if (isValid(m.first - 1, m.second)) parents_m.push_back({m.first - 1, m.second});
            if (isValid(m.first, m.second - 1)) parents_m.push_back({m.first, m.second - 1});

            for (auto u : parents_m) {
                for (auto v : children_w) {
                    if (grid[u.first][u.second] != -1 && grid[v.first][v.second] != -1 && 
                        grid[u.first][u.second] == grid[v.first][v.second]) {
                        int res = query(u.first, u.second, v.first, v.second);
                        if (res == 1) grid[m.first][m.second] = grid[w.first][w.second];
                        else grid[m.first][m.second] = 1 - grid[w.first][w.second];
                        determined = true;
                        goto done_m;
                    }
                }
            }
        }
        
        // Strategy 2: check relation with neighbor a in S_{n-2}
        if (!determined) {
            vector<pair<int, int>> neighbors_nm2;
            if (isValid(m.first - 1, m.second)) neighbors_nm2.push_back({m.first - 1, m.second});
            if (isValid(m.first, m.second - 1)) neighbors_nm2.push_back({m.first, m.second - 1});
            
            for (auto a : neighbors_nm2) {
                if (determined) break;
                vector<pair<int, int>> parents_a;
                if (isValid(a.first - 1, a.second)) parents_a.push_back({a.first - 1, a.second});
                if (isValid(a.first, a.second - 1)) parents_a.push_back({a.first, a.second - 1});
                vector<pair<int, int>> children_m;
                if (isValid(m.first + 1, m.second)) children_m.push_back({m.first + 1, m.second});
                if (isValid(m.first, m.second + 1)) children_m.push_back({m.first, m.second + 1});
                
                for (auto u : parents_a) {
                    for (auto v : children_m) {
                        if (grid[u.first][u.second] != -1 && grid[v.first][v.second] != -1 && 
                            grid[u.first][u.second] == grid[v.first][v.second]) {
                            int res = query(u.first, u.second, v.first, v.second);
                            // palindrome iff A[a] == A[m] (since u, v match)
                            if (res == 1) grid[m.first][m.second] = grid[a.first][a.second];
                            else grid[m.first][m.second] = 1 - grid[a.first][a.second];
                            determined = true;
                            goto done_m;
                        }
                    }
                }
            }
        }
        done_m:;
    }

    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j];
        }
        cout << endl;
    }

    return 0;
}