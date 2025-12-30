#include <bits/stdc++.h>
using namespace std;

struct Optimizer {
    static const int R = 8;
    static const int C = 14;
    static const int N = R * C;

    vector<int> grid;
    vector<vector<int>> adj;

    mt19937 rng;

    Optimizer() : grid(N, 0), adj(N) {
        rng.seed(chrono::high_resolution_clock::now().time_since_epoch().count());
        buildAdj();
        initGrid();
        // small random perturbation
        for (int k = 0; k < 200; ++k) {
            int a = rng() % N;
            int b = rng() % N;
            swap(grid[a], grid[b]);
        }
    }

    inline int id(int r, int c) const { return r * C + c; }

    void buildAdj() {
        static const int dr[8] = {-1,-1,-1,0,0,1,1,1};
        static const int dc[8] = {-1,0,1,-1,1,-1,0,1};
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c < C; ++c) {
                int u = id(r, c);
                for (int k = 0; k < 8; ++k) {
                    int nr = r + dr[k], nc = c + dc[k];
                    if (0 <= nr && nr < R && 0 <= nc && nc < C) {
                        adj[u].push_back(id(nr, nc));
                    }
                }
            }
        }
    }

    void initGrid() {
        // Fill grid along a snake path with the concatenation of integers 1.. until 112 digits
        string s;
        for (int n = 1; (int)s.size() < N; ++n) {
            s += to_string(n);
        }
        // snake order indices
        vector<int> order;
        order.reserve(N);
        for (int r = 0; r < R; ++r) {
            if (r % 2 == 0) {
                for (int c = 0; c < C; ++c) order.push_back(id(r, c));
            } else {
                for (int c = C - 1; c >= 0; --c) order.push_back(id(r, c));
            }
        }
        for (int i = 0; i < N; ++i) {
            grid[order[i]] = s[i] - '0';
        }
    }

    bool canReadStr(const string &s) const {
        int L = (int)s.size();
        if (L <= 0) return false;
        static bool cur[N], nxt[N];
        for (int i = 0; i < N; ++i) cur[i] = false;
        int d0 = s[0] - '0';
        for (int i = 0; i < N; ++i) {
            if (grid[i] == d0) cur[i] = true;
        }
        for (int j = 1; j < L; ++j) {
            int dj = s[j] - '0';
            bool any = false;
            for (int i = 0; i < N; ++i) nxt[i] = false;
            for (int u = 0; u < N; ++u) if (cur[u]) {
                const auto &neighbors = adj[u];
                for (int v : neighbors) {
                    if (grid[v] == dj) {
                        if (!nxt[v]) {
                            nxt[v] = true;
                            any = true;
                        }
                    }
                }
            }
            if (!any) return false;
            for (int i = 0; i < N; ++i) cur[i] = nxt[i];
        }
        for (int i = 0; i < N; ++i) if (cur[i]) return true;
        return false;
    }

    bool canReadInt(int n) const {
        return canReadStr(to_string(n));
    }

    int firstUnread(int limit = 10000) const {
        for (int n = 1; n <= limit; ++n) {
            if (!canReadInt(n)) return n;
        }
        return limit + 1;
    }

    // Find minimal flips to realize string s as a path
    // Returns pair(cost, path_indices)
    pair<int, vector<int>> minFlipPath(const string &s) const {
        int L = (int)s.size();
        const int INF = 1e9;
        vector<vector<int>> prv(L, vector<int>(N, -1));
        vector<int> dp_prev(N, INF), dp_cur(N, INF);
        int d0 = s[0] - '0';
        for (int v = 0; v < N; ++v) dp_cur[v] = (grid[v] == d0 ? 0 : 1);
        for (int i = 1; i < L; ++i) {
            dp_prev.swap(dp_cur);
            for (int v = 0; v < N; ++v) dp_cur[v] = INF;
            int di = s[i] - '0';
            for (int v = 0; v < N; ++v) {
                int best = INF, bestu = -1;
                for (int u : adj[v]) {
                    if (dp_prev[u] < best) {
                        best = dp_prev[u];
                        bestu = u;
                    }
                }
                if (best == INF) {
                    dp_cur[v] = INF;
                    prv[i][v] = -1;
                } else {
                    dp_cur[v] = best + (grid[v] == di ? 0 : 1);
                    prv[i][v] = bestu;
                }
            }
        }
        int best = INF, endv = -1;
        for (int v = 0; v < N; ++v) {
            if (dp_cur[v] < best) {
                best = dp_cur[v];
                endv = v;
            }
        }
        vector<int> path(L, -1);
        if (best >= INF || endv < 0) {
            return {INF, path};
        }
        int v = endv;
        for (int i = L - 1; i >= 0; --i) {
            path[i] = v;
            if (i > 0) v = prv[i][v];
        }
        return {best, path};
    }

    // Attempt to fix next missing using up to maxFlips changes.
    // Return: pair<bool improved, int newFirstUnread>
    pair<bool, int> tryFix(int curFirstUnread, int maxFlips) {
        string s = to_string(curFirstUnread);
        auto res = minFlipPath(s);
        int cost = res.first;
        if (cost > maxFlips || cost >= (int)res.second.size() + 100) {
            return {false, curFirstUnread};
        }
        // Apply changes
        vector<int> changed_idx;
        vector<int> old_vals;
        changed_idx.reserve(cost);
        old_vals.reserve(cost);
        for (int i = 0; i < (int)res.second.size(); ++i) {
            int v = res.second[i];
            int di = s[i] - '0';
            if (grid[v] != di) {
                changed_idx.push_back(v);
                old_vals.push_back(grid[v]);
                grid[v] = di;
            }
        }
        int newFirst = firstUnread(10000);
        if (newFirst >= curFirstUnread) {
            return {newFirst > curFirstUnread, newFirst};
        } else {
            // revert
            for (size_t k = 0; k < changed_idx.size(); ++k) {
                grid[changed_idx[k]] = old_vals[k];
            }
            return {false, curFirstUnread};
        }
    }

    void improve(double timeLimitSec) {
        auto start = chrono::high_resolution_clock::now();
        int first = firstUnread(10000);
        int bestFirst = first;
        vector<int> bestGrid = grid;

        int maxFlips = 1;
        int stagnant = 0;

        while (true) {
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - start).count();
            if (elapsed > timeLimitSec) break;

            // Gradually allow more flips over time
            if (stagnant > 80) {
                maxFlips = min(6, maxFlips + 1);
                stagnant = 0;
            }
            // Try to fix using bounded flips
            auto res = tryFix(first, maxFlips);
            if (res.first) {
                first = res.second;
                stagnant = 0;
                if (first > bestFirst) {
                    bestFirst = first;
                    bestGrid = grid;
                }
            } else {
                ++stagnant;
                // small random tweak: swap two cells to escape local minima, but keep if not worse
                int a = rng() % N;
                int b = rng() % N;
                if (a != b) {
                    int va = grid[a], vb = grid[b];
                    swap(grid[a], grid[b]);
                    int nf = firstUnread(10000);
                    if (nf >= first) {
                        if (nf > bestFirst) {
                            bestFirst = nf;
                            bestGrid = grid;
                        }
                        first = nf;
                        stagnant = 0;
                    } else {
                        swap(grid[a], grid[b]); // revert
                    }
                }
            }
        }
        grid = bestGrid; // ensure best found grid is output
    }

    void print() const {
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c < C; ++c) {
                cout << grid[id(r, c)];
            }
            cout << '\n';
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Optimizer opt;
    // Use a modest time budget to ensure we finish well within 1 minute.
    // Adjust as needed; here ~0.7 seconds.
    opt.improve(0.7);
    opt.print();
    return 0;
}