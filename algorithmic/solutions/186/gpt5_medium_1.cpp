#include <bits/stdc++.h>
using namespace std;

using ULL = unsigned long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    
    const int MAXC = 512; // must be >= N (N <= 500)
    const int Wc = (MAXC + 63) / 64;
    
    // Adjacency list and dedup bitset
    vector<vector<int>> g(N);
    int Wa = (N + 63) / 64;
    vector<vector<ULL>> adjBits(N, vector<ULL>(Wa, 0));
    
    auto hasEdge = [&](int u, int v) -> bool {
        int idx = v >> 6, bit = v & 63;
        return (adjBits[u][idx] >> bit) & 1ULL;
    };
    auto setEdge = [&](int u, int v) {
        int idx = v >> 6, bit = v & 63;
        adjBits[u][idx] |= (1ULL << bit);
    };
    
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!hasEdge(u, v)) {
            setEdge(u, v);
            setEdge(v, u);
            g[u].push_back(v);
            g[v].push_back(u);
        }
    }
    
    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)g[i].size();
    
    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    
    auto dsatur_run = [&](bool randomize) -> vector<int> {
        vector<int> color(N, 0);
        vector<int> satDeg(N, 0);
        vector<vector<ULL>> used(N, vector<ULL>(Wc, 0));
        vector<uint64_t> randKey;
        if (randomize) {
            randKey.resize(N);
            for (int i = 0; i < N; ++i) randKey[i] = rng();
        }
        
        auto firstZero = [&](const vector<ULL>& bits) -> int {
            for (int w = 0; w < Wc; ++w) {
                ULL inv = ~bits[w];
                if (inv) {
                    int b = __builtin_ctzll(inv);
                    int c = w * 64 + b + 1;
                    if (c <= MAXC) return c;
                }
            }
            return MAXC; // fallback, should not happen with MAXC >= N
        };
        
        int colored = 0;
        while (colored < N) {
            int best = -1;
            int bestSat = -1;
            int bestDeg = -1;
            for (int i = 0; i < N; ++i) {
                if (color[i] != 0) continue;
                int s = satDeg[i];
                int d = deg[i];
                if (best == -1 || s > bestSat || (s == bestSat && d > bestDeg) ||
                    (s == bestSat && d == bestDeg && (randomize ? (randKey[i] > randKey[best]) : (i < best)))) {
                    best = i;
                    bestSat = s;
                    bestDeg = d;
                }
            }
            
            int v = best;
            int c = firstZero(used[v]);
            color[v] = c;
            ++colored;
            
            int idx = (c - 1) >> 6;
            ULL mask = 1ULL << ((c - 1) & 63);
            for (int u : g[v]) {
                if (color[u] == 0) {
                    if ((used[u][idx] & mask) == 0) {
                        used[u][idx] |= mask;
                        satDeg[u]++;
                    }
                }
            }
        }
        return color;
    };
    
    auto max_color = [&](const vector<int>& col) -> int {
        int mx = 0;
        for (int c : col) if (c > mx) mx = c;
        return mx;
    };
    
    auto lower_colors = [&](vector<int>& color) {
        // Try a few passes to greedily lower colors
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        bool changed = true;
        for (int pass = 0; pass < 3 && changed; ++pass) {
            // order by (-color, -deg), random tiebreak
            vector<uint64_t> rk(N);
            for (int i = 0; i < N; ++i) rk[i] = rng();
            sort(order.begin(), order.end(), [&](int a, int b){
                if (color[a] != color[b]) return color[a] > color[b];
                if (deg[a] != deg[b]) return deg[a] > deg[b];
                return rk[a] < rk[b];
            });
            changed = false;
            for (int u : order) {
                int cur = color[u];
                if (cur <= 1) continue;
                // mark colors used by neighbors less than cur
                vector<char> forbid(cur, 0);
                for (int v : g[u]) {
                    int c = color[v];
                    if (c > 0 && c < cur) forbid[c] = 1;
                }
                for (int c = 1; c < cur; ++c) {
                    if (!forbid[c]) {
                        color[u] = c;
                        changed = true;
                        break;
                    }
                }
            }
        }
    };
    
    auto t_start = chrono::steady_clock::now();
    double time_limit = 1.85; // seconds
    vector<int> best_col = dsatur_run(false);
    lower_colors(best_col);
    int bestC = max_color(best_col);
    
    int iterations = 0;
    while (true) {
        auto t_now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(t_now - t_start).count();
        if (elapsed > time_limit) break;
        vector<int> col = dsatur_run(true);
        lower_colors(col);
        int C = max_color(col);
        if (C < bestC) {
            bestC = C;
            best_col = move(col);
        }
        iterations++;
    }
    
    // Output the best coloring
    for (int i = 0; i < N; ++i) {
        cout << best_col[i] << '\n';
    }
    return 0;
}