#include <bits/stdc++.h>
using namespace std;

static inline uint64_t now_ms() {
    using namespace std::chrono;
    return duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}

vector<int> dsatur_coloring(const vector<vector<int>>& adj, const vector<int>& degree, mt19937_64& rng) {
    int N = (int)adj.size();
    vector<int> color(N, 0);
    vector<char> colored(N, 0);
    vector<int> sat(N, 0);
    vector<vector<char>> used(N, vector<char>(N + 1, 0));

    // Choose initial vertex: max degree, tie-break random among equals
    int best = -1, bestdeg = -1;
    vector<int> candidates;
    for (int i = 0; i < N; ++i) {
        if (degree[i] > bestdeg) {
            bestdeg = degree[i];
            candidates.clear();
            candidates.push_back(i);
        } else if (degree[i] == bestdeg) {
            candidates.push_back(i);
        }
    }
    if (!candidates.empty()) {
        uniform_int_distribution<int> dist(0, (int)candidates.size() - 1);
        best = candidates[dist(rng)];
    } else {
        best = 0;
    }

    for (int it = 0; it < N; ++it) {
        int u;
        if (it == 0) {
            u = best;
        } else {
            int maxSat = -1, maxDeg = -1;
            candidates.clear();
            for (int v = 0; v < N; ++v) if (!colored[v]) {
                if (sat[v] > maxSat) {
                    maxSat = sat[v];
                    maxDeg = degree[v];
                    candidates.clear();
                    candidates.push_back(v);
                } else if (sat[v] == maxSat) {
                    if (degree[v] > maxDeg) {
                        maxDeg = degree[v];
                        candidates.clear();
                        candidates.push_back(v);
                    } else if (degree[v] == maxDeg) {
                        candidates.push_back(v);
                    }
                }
            }
            if (candidates.empty()) {
                // all colored
                break;
            }
            uniform_int_distribution<int> dist(0, (int)candidates.size() - 1);
            u = candidates[dist(rng)];
        }

        // Find smallest available color for u
        vector<char> forbid(N + 1, 0);
        for (int w : adj[u]) {
            int c = color[w];
            if (c > 0) forbid[c] = 1;
        }
        int c = 1;
        while (c <= N && forbid[c]) ++c;
        if (c > N) c = 1; // fallback, should not happen
        color[u] = c;
        colored[u] = 1;

        // Update saturation of neighbors
        for (int v : adj[u]) if (!colored[v]) {
            if (!used[v][c]) {
                used[v][c] = 1;
                sat[v]++;
            }
        }
    }
    return color;
}

void greedy_reduce(vector<int>& color, const vector<vector<int>>& adj, mt19937_64& rng) {
    int N = (int)color.size();
    int maxC = 0;
    for (int c : color) if (c > maxC) maxC = c;
    if (maxC <= 1) return;

    vector<int> order;
    order.reserve(N);
    vector<char> used;
    for (int col = maxC; col >= 2; --col) {
        order.clear();
        for (int i = 0; i < N; ++i) if (color[i] == col) order.push_back(i);
        if (order.empty()) continue;
        shuffle(order.begin(), order.end(), rng);

        for (int u : order) {
            used.assign(col, 0); // only need colors < col
            for (int v : adj[u]) {
                int c = color[v];
                if (c > 0 && c < col) used[c] = 1;
            }
            for (int c = 1; c < col; ++c) {
                if (!used[c]) {
                    color[u] = c;
                    break;
                }
            }
        }
    }
    // Compact colors if there are gaps
    // Build mapping to [1..K] preserving order of appearance
    vector<int> present(N + 1, 0);
    for (int c : color) if (c > 0 && c <= N) present[c] = 1;
    vector<int> mapc(N + 1, 0);
    int nxt = 1;
    for (int c = 1; c <= N; ++c) if (present[c]) mapc[c] = nxt++;
    for (int i = 0; i < N; ++i) color[i] = mapc[color[i]];
}

bool valid_coloring(const vector<int>& color, const vector<vector<int>>& adj) {
    int N = (int)color.size();
    for (int u = 0; u < N; ++u) {
        if (color[u] < 1) return false;
        for (int v : adj[u]) {
            if (color[u] == color[v]) return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<char>> mat(N, vector<char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        mat[u][v] = 1;
        mat[v][u] = 1;
    }
    vector<vector<int>> adj(N);
    vector<int> degree(N, 0);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) if (mat[i][j]) adj[i].push_back(j);
        degree[i] = (int)adj[i].size();
    }

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    uint64_t start = now_ms();
    uint64_t time_limit_ms = 1800; // a bit under 2s to be safe
    vector<int> best_color(N, 1);
    int bestC = N + 1;

    int attempts = 0;
    while (now_ms() - start < time_limit_ms) {
        vector<int> col = dsatur_coloring(adj, degree, rng);
        greedy_reduce(col, adj, rng);
        if (!valid_coloring(col, adj)) {
            // fallback: simple greedy
            vector<int> simple(N, 0);
            vector<int> order(N);
            iota(order.begin(), order.end(), 0);
            sort(order.begin(), order.end(), [&](int a, int b){
                if (degree[a] != degree[b]) return degree[a] > degree[b];
                return a < b;
            });
            for (int u : order) {
                vector<char> used(N + 1, 0);
                for (int v : adj[u]) {
                    if (simple[v] > 0) used[simple[v]] = 1;
                }
                int c = 1;
                while (c <= N && used[c]) ++c;
                if (c > N) c = 1;
                simple[u] = c;
            }
            col.swap(simple);
            greedy_reduce(col, adj, rng);
        }
        int maxC = 0;
        for (int c : col) if (c > maxC) maxC = c;
        if (valid_coloring(col, adj) && maxC < bestC) {
            bestC = maxC;
            best_color = col;
        }
        attempts++;
        if (attempts >= 50) break; // avoid too many iterations on small graphs
    }

    for (int i = 0; i < N; ++i) {
        cout << best_color[i] << "\n";
    }
    return 0;
}