#include <bits/stdc++.h>
using namespace std;

static inline uint64_t nowMicros() {
    using namespace std::chrono;
    return duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count();
}

struct DSaturSolver {
    int N;
    const vector<vector<int>>& adj;
    vector<int> color, deg, sat;
    vector<vector<uint64_t>> forb;
    int W;

    DSaturSolver(const vector<vector<int>>& g) : N((int)g.size()), adj(g) {
        color.assign(N, -1);
        deg.resize(N);
        sat.assign(N, 0);
        W = (N + 63) >> 6;
        forb.assign(N, vector<uint64_t>(W, 0));
        for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();
    }

    int pick_next() {
        int best = -1;
        for (int i = 0; i < N; ++i) if (color[i] == -1) {
            if (best == -1 || sat[i] > sat[best] || (sat[i] == sat[best] && deg[i] > deg[best]) || (sat[i] == sat[best] && deg[i] == deg[best] && i < best)) {
                best = i;
            }
        }
        return best;
    }

    vector<int> solve() {
        vector<int> usedTime(N, -1);
        int timeStamp = 0;
        int colored = 0;
        while (colored < N) {
            int u = pick_next();
            if (u == -1) break;

            // find smallest available color by scanning neighbors
            ++timeStamp;
            for (int v : adj[u]) {
                if (color[v] != -1) usedTime[color[v]] = timeStamp;
            }
            int c = 0;
            while (c < N && usedTime[c] == timeStamp) ++c;
            if (c >= N) c = N - 1; // fallback (shouldn't happen)

            color[u] = c;
            ++colored;

            // update saturation of neighbors
            int idx = c >> 6;
            uint64_t mask = 1ULL << (c & 63);
            for (int v : adj[u]) if (color[v] == -1) {
                if ((forb[v][idx] & mask) == 0) {
                    forb[v][idx] |= mask;
                    sat[v]++;
                }
            }
        }
        return color;
    }
};

static inline int maxColor(const vector<int>& col) {
    int mx = -1;
    for (int c : col) mx = max(mx, c);
    return mx + 1;
}

bool tryReduceOneColor(vector<int>& col, int& K, const vector<vector<int>>& adj, uint64_t deadlineMicros) {
    int N = (int)col.size();
    vector<int> vertices;
    vertices.reserve(N);
    for (int i = 0; i < N; ++i) if (col[i] == K - 1) vertices.push_back(i);
    if (vertices.empty()) { K--; return true; }

    auto timeUp = [&]() -> bool {
        return nowMicros() > deadlineMicros;
    };

    bool progress_any = true;
    while (progress_any && !vertices.empty()) {
        if (timeUp()) break;
        progress_any = false;

        // Pass 1: direct recolor if possible
        for (int v : vertices) {
            if (timeUp()) break;
            if (col[v] != K - 1) continue;
            vector<char> used(K - 1, 0);
            for (int u : adj[v]) {
                int cu = col[u];
                if (cu >= 0 && cu < K - 1) used[cu] = 1;
            }
            for (int a = 0; a < K - 1; ++a) {
                if (!used[a]) {
                    col[v] = a;
                    progress_any = true;
                    break;
                }
            }
        }
        if (progress_any) continue;

        // Pass 2: unique neighbor Kempe-chain swap
        bool swapped = false;
        for (int v : vertices) {
            if (timeUp()) break;
            if (col[v] != K - 1) continue;

            vector<int> cnt(K - 1, 0);
            vector<int> uniq(K - 1, -1);
            for (int u : adj[v]) {
                int cu = col[u];
                if (cu >= 0 && cu < K - 1) {
                    cnt[cu]++;
                    if (cnt[cu] == 1) uniq[cu] = u;
                    else uniq[cu] = -2; // multiple
                }
            }

            // try colors a with unique neighbor
            for (int a = 0; a < K - 1 && !swapped; ++a) {
                if (cnt[a] == 1) {
                    int u = uniq[a];
                    // Precompute neighbors of v with color c
                    vector<int> neigh_per_color_indices;
                    neigh_per_color_indices.reserve(adj[v].size());
                    // We'll test each c
                    for (int c = 0; c < K - 1 && !swapped; ++c) if (c != a) {
                        if (timeUp()) break;

                        // mark neighbors of v with color c
                        bool hasC = false;
                        vector<char> mark(N, 0);
                        for (int w : adj[v]) {
                            if (col[w] == c) {
                                mark[w] = 1;
                                hasC = true;
                            }
                        }

                        // BFS on {a, c} from u; ensure no marked node is reached
                        vector<char> vis(N, 0);
                        deque<int> dq;
                        dq.push_back(u);
                        vis[u] = 1;
                        bool bad = false;
                        vector<int> comp;
                        comp.reserve(32);
                        while (!dq.empty()) {
                            int x = dq.front(); dq.pop_front();
                            if (mark[x]) { bad = true; break; }
                            comp.push_back(x);
                            for (int y : adj[x]) {
                                int cy = col[y];
                                if ((cy == a || cy == c) && !vis[y]) {
                                    vis[y] = 1;
                                    dq.push_back(y);
                                }
                            }
                        }
                        if (bad) continue;

                        // Perform swap a <-> c on comp
                        for (int x : comp) {
                            int cx = col[x];
                            if (cx == a) col[x] = c;
                            else if (cx == c) col[x] = a;
                        }
                        // Now color v with a
                        col[v] = a;
                        swapped = true;
                        progress_any = true;
                        break;
                    }
                }
            }
        }
        if (!progress_any) break;
    }

    // Check if all K-1 are eliminated
    bool anyKminus1 = false;
    for (int i = 0; i < (int)col.size(); ++i) if (col[i] == K - 1) { anyKminus1 = true; break; }
    if (!anyKminus1) { K--; return true; }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> adj(N);
    vector<vector<char>> mat(N, vector<char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!mat[u][v]) {
            mat[u][v] = mat[v][u] = 1;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }

    // Initial coloring with DSATUR
    DSaturSolver solver(adj);
    vector<int> col = solver.solve();
    int K = maxColor(col);

    // Improvement phase with a time budget
    uint64_t startMicros = nowMicros();
    // Use up to 1.85 seconds (1,850,000 microseconds) for improvements
    uint64_t deadlineMicros = startMicros + 1850000ULL;

    // Try to reduce number of colors step by step
    while (K > 1 && nowMicros() < deadlineMicros) {
        bool improved = tryReduceOneColor(col, K, adj, deadlineMicros);
        if (!improved) break;
    }

    // Output 1-based colors
    for (int i = 0; i < N; ++i) {
        cout << (col[i] + 1) << '\n';
    }
    return 0;
}