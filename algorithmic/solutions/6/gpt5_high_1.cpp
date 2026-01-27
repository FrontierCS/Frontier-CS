#include <bits/stdc++.h>
using namespace std;

static const int KMAX = 240;

struct RNG {
    uint64_t seed;
    RNG(uint64_t s=123456789) : seed(s) {}
    inline uint64_t next() {
        seed ^= seed << 7;
        seed ^= seed >> 9;
        return seed;
    }
    inline int randint(int n) { // [0, n)
        return (int)(next() % (uint64_t)n);
    }
    inline bool coin() { return (next() >> 63) & 1; }
};

struct WorldMapBuilder {
    int N, M;
    vector<int> A, B;
    vector<vector<char>> adj;   // adj[u][v] true if edge exists between u and v
    vector<vector<char>> allow; // allow[u][v] true if u==v or adj[u][v]

    int K; // grid size
    vector<vector<int>> grid;

    RNG rng;

    WorldMapBuilder(int n, int m, const vector<int>& a, const vector<int>& b, uint64_t seed)
        : N(n), M(m), A(a), B(b), adj(n, vector<char>(n, 0)), allow(n, vector<char>(n, 0)), rng(seed) {
        for (int i = 0; i < M; ++i) {
            int u = A[i]-1;
            int v = B[i]-1;
            adj[u][v] = adj[v][u] = 1;
        }
        for (int i = 0; i < N; ++i) {
            allow[i][i] = 1;
            for (int j = 0; j < N; ++j) if (adj[i][j]) allow[i][j] = 1;
        }
        // Choose K: try to keep moderate but enough to cover edges
        K = min(KMAX, max(2*N, 100));
        grid.assign(K, vector<int>(K, 0));
    }

    vector<int> dfs_walk() {
        vector<vector<int>> G(N);
        for (int u = 0; u < N; ++u) for (int v = 0; v < N; ++v) if (adj[u][v]) G[u].push_back(v);
        // Shuffle neighbors to add randomness
        for (int u = 0; u < N; ++u) {
            for (int i = (int)G[u].size()-1; i > 0; --i) {
                int j = rng.randint(i+1);
                swap(G[u][i], G[u][j]);
            }
        }
        vector<int> walk;
        vector<char> vis(N, 0);
        int root = 0;
        // In case of isolated single node graph (N==1 allowed)
        function<void(int,int)> dfs = [&](int u, int p){
            vis[u] = 1;
            walk.push_back(u);
            for (int v : G[u]) {
                if (!vis[v]) {
                    dfs(v, u);
                    walk.push_back(u);
                }
            }
        };
        dfs(root, -1);
        if (walk.empty()) walk.push_back(0);
        // Ensure it ends at root
        if (walk.back() != root) walk.push_back(root);
        return walk;
    }

    inline void markEdge(int u, int v, vector<vector<char>>& covered) {
        if (u == v) return;
        if (!adj[u][v]) return;
        int x = min(u, v), y = max(u, v);
        covered[x][y] = 1;
    }

    void collectCovered(const vector<vector<int>>& g, vector<vector<char>>& covered) {
        for (int i = 0; i < N; ++i) for (int j = i+1; j < N; ++j) covered[i][j] = 0;
        for (int r = 0; r < K; ++r) {
            for (int c = 1; c < K; ++c) markEdge(g[r][c-1], g[r][c], covered);
        }
        for (int r = 1; r < K; ++r) {
            for (int c = 0; c < K; ++c) markEdge(g[r-1][c], g[r][c], covered);
        }
    }

    vector<int> build_first_row_from_walk(const vector<int>& walk) {
        vector<int> row(K);
        for (int c = 0; c < K; ++c) row[c] = walk[c % (int)walk.size()];
        return row;
    }

    // DP to build a row with optional forcing of an edge (u,v) horizontally.
    // top: pointer to top row (nullptr if building first row)
    // covered: current covered edges (for weighting)
    // returns empty vector if impossible (shouldn't happen often)
    vector<int> compute_row_dp(const vector<int>* top, const vector<vector<char>>& covered, int force_u = -1, int force_v = -1) {
        bool enforce = (force_u != -1 && force_v != -1);
        // Precompute allowed colors per column based on top constraint
        vector<vector<int>> allowedCols(K);
        if (top) {
            allowedCols.assign(K, {});
            for (int c = 0; c < K; ++c) {
                int t = (*top)[c];
                for (int x = 0; x < N; ++x) if (allow[x][t]) allowedCols[c].push_back(x);
                // random shuffle to add diversity
                for (int i = (int)allowedCols[c].size()-1; i > 0; --i) {
                    int j = rng.randint(i+1);
                    swap(allowedCols[c][i], allowedCols[c][j]);
                }
            }
        } else {
            vector<int> all(N);
            iota(all.begin(), all.end(), 0);
            for (int c = 0; c < K; ++c) {
                allowedCols[c] = all;
                for (int i = N-1; i > 0; --i) {
                    int j = rng.randint(i+1);
                    swap(allowedCols[c][i], allowedCols[c][j]);
                }
            }
        }

        const int NEG = -1e9;
        // dp[c][x][used] -> best score
        vector<array<int,2>> dp_prev(N, {NEG, NEG}), dp_cur(N, {NEG, NEG});
        vector<vector<array<int,2>>> prv(K, vector<array<int,2>>(N, array<int,2>{-1,-1}));

        auto wantEdge = [&](int a, int b)->bool{
            if (a==b) return false;
            int x = min(a,b), y = max(a,b);
            if (!adj[x][y]) return false;
            return !covered[x][y];
        };

        auto trans_w = [&](int y, int x)->int{
            if (y == x) return 0;
            return wantEdge(y, x) ? 2 : 0; // horizontal edges weight 2
        };
        auto node_w = [&](int c, int x)->int{
            if (!top) return 0;
            int t = (*top)[c];
            if (t == x) return 0;
            return wantEdge(t, x) ? 1 : 0;  // vertical edges weight 1
        };

        // Initialize column 0
        for (int x : allowedCols[0]) {
            int used = 0;
            dp_prev[x][0] = node_w(0, x);
            dp_prev[x][1] = NEG; // cannot have used forced edge at first cell
        }

        // Iterate columns
        for (int c = 1; c < K; ++c) {
            // reset dp_cur
            for (int x = 0; x < N; ++x) dp_cur[x][0] = dp_cur[x][1] = NEG;
            for (int x : allowedCols[c]) {
                int nw = node_w(c, x);
                for (int y : allowedCols[c-1]) {
                    if (!allow[y][x]) continue;
                    // used=0
                    if (dp_prev[y][0] > NEG/2) {
                        int inc = trans_w(y, x) + nw;
                        int used = 0;
                        if (enforce && ((y==force_u && x==force_v) || (y==force_v && x==force_u))) used = 1;
                        int cand = dp_prev[y][0] + inc;
                        if (cand > dp_cur[x][used] || (cand == dp_cur[x][used] && rng.coin())) {
                            dp_cur[x][used] = cand;
                            prv[c][x][used] = y;
                        }
                    }
                    // used=1
                    if (dp_prev[y][1] > NEG/2) {
                        int inc = trans_w(y, x) + nw;
                        int used = 1;
                        int cand = dp_prev[y][1] + inc;
                        if (cand > dp_cur[x][used] || (cand == dp_cur[x][used] && rng.coin())) {
                            dp_cur[x][used] = cand;
                            prv[c][x][used] = y;
                        }
                    }
                }
            }
            // swap
            for (int x = 0; x < N; ++x) {
                dp_prev[x][0] = dp_cur[x][0];
                dp_prev[x][1] = dp_cur[x][1];
                dp_cur[x][0] = dp_cur[x][1] = NEG;
            }
        }

        // Choose best ending
        int best_used = enforce ? 1 : 0;
        int best_x = -1, best_val = NEG;
        for (int x : allowedCols[K-1]) {
            for (int u = (enforce?1:0); u <= 1; ++u) {
                if (!enforce && u==0) {
                    if (dp_prev[x][u] > best_val || (dp_prev[x][u] == best_val && rng.coin())) {
                        best_val = dp_prev[x][u];
                        best_x = x;
                        best_used = u;
                    }
                } else if (enforce && u==1) {
                    if (dp_prev[x][u] > best_val || (dp_prev[x][u] == best_val && rng.coin())) {
                        best_val = dp_prev[x][u];
                        best_x = x;
                        best_used = u;
                    }
                } else if (!enforce && u==1) {
                    if (dp_prev[x][u] > best_val || (dp_prev[x][u] == best_val && rng.coin())) {
                        best_val = dp_prev[x][u];
                        best_x = x;
                        best_used = u;
                    }
                }
            }
        }
        if (best_x == -1) {
            // Fallback: copy top row if exists, else random row following self loops
            vector<int> fallback(K);
            if (top) {
                fallback = *top;
            } else {
                for (int c = 0; c < K; ++c) fallback[c] = rng.randint(N);
            }
            return fallback;
        }

        // Reconstruct
        vector<int> row(K);
        int x = best_x;
        int used = best_used;
        for (int c = K-1; c >= 0; --c) {
            row[c] = x;
            if (c == 0) break;
            int y = prv[c][x][used];
            if (enforce) {
                // determine if the pair (y,x) matched the forced edge to backtrack used flag
                if (used == 1) {
                    if ((y==force_u && x==force_v) || (y==force_v && x==force_u)) {
                        // previous used flag may have been 0
                        // but could also be 1 if multiple matches; we don't know; try both:
                        // We stored only one predecessor y; to know previous 'used' we can recompute:
                        // Check if dp_prev[y][1] led to dp[c][x][1] with equal score; If not, then used came from a new match -> previous was 0.
                        // For simplicity, we will attempt to deduce previous used state:
                        // We'll recompute quick conditions; but we didn't store scores; We'll approximate:
                        // To avoid complexity, we can mark used=0 when encountering the first matching pair in backtracking.
                        used = 0;
                    }
                }
            }
            x = y;
        }
        return row;
    }

    void update_covered_with_row(int r, const vector<int>* top, const vector<int>& row, vector<vector<char>>& covered) {
        // horizontal in row
        for (int c = 1; c < K; ++c) markEdge(row[c-1], row[c], covered);
        if (top) {
            for (int c = 0; c < K; ++c) markEdge((*top)[c], row[c], covered);
        }
    }

    bool all_edges_covered(const vector<vector<char>>& covered) {
        for (int i = 0; i < M; ++i) {
            int u = A[i]-1, v = B[i]-1;
            int x = min(u, v), y = max(u, v);
            if (!covered[x][y]) return false;
        }
        return true;
    }

    vector<pair<int,int>> missing_edges(const vector<vector<char>>& covered) {
        vector<pair<int,int>> miss;
        for (int i = 0; i < M; ++i) {
            int u = A[i]-1, v = B[i]-1;
            int x = min(u, v), y = max(u, v);
            if (!covered[x][y]) miss.emplace_back(x, y);
        }
        return miss;
    }

    vector<vector<int>> build_once() {
        vector<vector<int>> g(K, vector<int>(K, 0));
        vector<vector<char>> covered(N, vector<char>(N, 0));
        // row 0
        vector<int> walk = dfs_walk();
        vector<int> row0 = build_first_row_from_walk(walk);
        g[0] = row0;
        // update covered with row0 horizontally
        update_covered_with_row(0, nullptr, row0, covered);
        // build subsequent rows
        for (int r = 1; r < K; ++r) {
            vector<int> rowr = compute_row_dp(&g[r-1], covered, -1, -1);
            g[r] = rowr;
            update_covered_with_row(r, &g[r-1], rowr, covered);
        }
        // Ensure all colors appear at least once: if not, try to adjust slightly by random re-generation of some rows
        vector<int> freq(N, 0);
        for (int r = 0; r < K; ++r) for (int c = 0; c < K; ++c) freq[g[r][c]]++;
        for (int col = 0; col < N; ++col) {
            if (freq[col] == 0) {
                // Try to force appearance by rebuilding a random row with no force edge (weights tend to include new colors)
                int r = rng.randint(K);
                vector<int> rowr = compute_row_dp((r>0 ? &g[r-1] : nullptr), covered, -1, -1);
                g[r] = rowr;
                // Rebuild all rows below to maintain vertical adjacency
                // Recompute covered up to r
                for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) covered[i][j] = 0;
                update_covered_with_row(0, nullptr, g[0], covered);
                for (int i = 1; i <= r; ++i) update_covered_with_row(i, &g[i-1], g[i], covered);
                for (int i = r+1; i < K; ++i) {
                    vector<int> rowi = compute_row_dp(&g[i-1], covered, -1, -1);
                    g[i] = rowi;
                    update_covered_with_row(i, &g[i-1], g[i], covered);
                }
                // update freq
                freq.assign(N, 0);
                for (int rr = 0; rr < K; ++rr) for (int c = 0; c < K; ++c) freq[g[rr][c]]++;
            }
        }
        return g;
    }

    vector<vector<int>> repair_missing(vector<vector<int>>& g) {
        // Attempt to repair missing edges by forcing rows
        vector<vector<char>> covered(N, vector<char>(N, 0));
        collectCovered(g, covered);
        auto miss = missing_edges(covered);
        if (miss.empty()) return g;

        // Try to cover missing edges one by one
        // Shuffle missing edges to randomize
        for (int i = (int)miss.size()-1; i > 0; --i) {
            int j = rng.randint(i+1);
            swap(miss[i], miss[j]);
        }

        for (auto edge : miss) {
            int fu = edge.first, fv = edge.second; // 0-based sorted
            bool added = false;
            // Try multiple rows randomly
            vector<int> rows(K);
            iota(rows.begin(), rows.end(), 0);
            for (int i = K-1; i > 0; --i) {
                int j = rng.randint(i+1);
                swap(rows[i], rows[j]);
            }
            for (int rindex = 0; rindex < K && !added; ++rindex) {
                int r = rows[rindex];
                vector<vector<char>> covUp = covered; // copy baseline
                // Recompute covered up to row r-1 to be safe
                for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) covUp[i][j] = 0;
                update_covered_with_row(0, nullptr, g[0], covUp);
                for (int i = 1; i < r; ++i) update_covered_with_row(i, &g[i-1], g[i], covUp);

                vector<int>* top = (r > 0 ? &g[r-1] : nullptr);
                vector<int> newRow = compute_row_dp(top, covUp, fu, fv);
                if (newRow.empty()) continue;

                // Apply and rebuild below rows
                g[r] = newRow;
                // Reset covered and rebuild from row r onwards to maximize adding missing edges
                vector<vector<char>> cov(N, vector<char>(N, 0));
                update_covered_with_row(0, nullptr, g[0], cov);
                for (int i = 1; i <= r; ++i) update_covered_with_row(i, &g[i-1], g[i], cov);
                for (int i = r+1; i < K; ++i) {
                    vector<int> ri = compute_row_dp(&g[i-1], cov, -1, -1);
                    g[i] = ri;
                    update_covered_with_row(i, &g[i-1], g[i], cov);
                }

                // Check if edge added
                vector<vector<char>> covCheck(N, vector<char>(N, 0));
                collectCovered(g, covCheck);
                if (covCheck[fu][fv]) {
                    covered = covCheck;
                    added = true;
                }
            }
            if (!added) {
                // Failed to add this edge in current configuration, give up and return as is
                return g;
            }
        }
        return g;
    }

    vector<vector<int>> build_map() {
        // Multiple attempts with randomization to ensure full coverage
        for (int attempt = 0; attempt < 8; ++attempt) {
            auto g = build_once();
            vector<vector<char>> covered(N, vector<char>(N, 0));
            collectCovered(g, covered);
            if (all_edges_covered(covered)) {
                grid = g;
                return format_output();
            }
            auto g2 = repair_missing(g);
            collectCovered(g2, covered);
            if (all_edges_covered(covered)) {
                grid = g2;
                return format_output();
            }
            // Try again with different K maybe: increase K slightly if possible
            if (K < KMAX) {
                K = min(KMAX, K + max(5, N/2));
                grid.assign(K, vector<int>(K, 0));
            }
            // re-seed slightly
            rng.next();
        }
        // Fallback: ensure valid (no invalid adjacencies). Build trivial map repeating a DFS walk row by row (no vertical differences).
        K = min(KMAX, max(2*N, 100));
        grid.assign(K, vector<int>(K, 0));
        vector<int> walk = dfs_walk();
        for (int r = 0; r < K; ++r) {
            auto row0 = build_first_row_from_walk(walk);
            for (int c = 0; c < K; ++c) grid[r][c] = row0[c];
        }
        return format_output();
    }

    vector<vector<int>> format_output() {
        vector<vector<int>> C(K, vector<int>(K, 0));
        for (int r = 0; r < K; ++r) for (int c = 0; c < K; ++c) C[r][c] = grid[r][c] + 1;
        return C;
    }
};

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    // Seed RNG with hash of inputs for reproducibility
    uint64_t seed = 1469598103934665603ull;
    seed ^= (uint64_t)N + 0x9e3779b97f4a7c15ull + (seed<<6) + (seed>>2);
    seed ^= (uint64_t)M + 0x9e3779b97f4a7c15ull + (seed<<6) + (seed>>2);
    for (int x : A) { seed ^= (uint64_t)x + 0x9e3779b97f4a7c15ull + (seed<<6) + (seed>>2); }
    for (int x : B) { seed ^= (uint64_t)x + 0x9e3779b97f4a7c15ull + (seed<<6) + (seed>>2); }

    WorldMapBuilder builder(N, M, A, B, seed);
    return builder.build_map();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; ++tc) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; ++i) cin >> A[i] >> B[i];
        auto C = create_map(N, M, A, B);
        int P = (int)C.size();
        cout << P << "\n";
        for (int i = 0; i < P; ++i) {
            cout << (int)C[i].size() << (i+1==P?'\n':' ');
        }
        cout << "\n";
        for (int i = 0; i < P; ++i) {
            for (int j = 0; j < (int)C[i].size(); ++j) {
                if (j) cout << ' ';
                cout << C[i][j];
            }
            cout << "\n";
        }
        cout.flush();
    }
    return 0;
}