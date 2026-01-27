#include <bits/stdc++.h>
using namespace std;

static const int MAXC = 512;

pair<vector<int>, int> dsatur(const vector<vector<int>>& adj, const vector<int>& deg, mt19937_64& rng) {
    int N = (int)adj.size() - 1;
    vector<int> color(N + 1, 0);
    vector<int> sat(N + 1, 0);
    vector<bitset<MAXC>> nbrColors(N + 1);
    int maxColor = 0;

    for (int step = 0; step < N; ++step) {
        int best = -1;
        int bestSat = -1;
        int bestDeg = -1;
        int tieCount = 0;
        for (int v = 1; v <= N; ++v) {
            if (color[v] != 0) continue;
            int s = sat[v];
            int d = deg[v];
            if (s > bestSat || (s == bestSat && d > bestDeg)) {
                best = v;
                bestSat = s;
                bestDeg = d;
                tieCount = 1;
            } else if (s == bestSat && d == bestDeg) {
                ++tieCount;
                if ((uint64_t)(rng() % tieCount) == 0) {
                    best = v;
                }
            }
        }

        bitset<MAXC> used = nbrColors[best];
        int chosen = 0;
        for (int c = 1; c <= maxColor; ++c) {
            if (!used.test(c)) { chosen = c; break; }
        }
        if (chosen == 0) chosen = ++maxColor;
        color[best] = chosen;

        for (int u : adj[best]) {
            if (color[u] == 0) {
                if (!nbrColors[u].test(chosen)) {
                    nbrColors[u].set(chosen);
                    ++sat[u];
                }
            }
        }
    }
    return {color, maxColor};
}

void compressColors(vector<int>& color, int& C) {
    int N = (int)color.size() - 1;
    vector<int> mapC(C + 1, 0);
    int idx = 0;
    for (int c = 1; c <= C; ++c) {
        bool exists = false;
        for (int i = 1; i <= N; ++i) {
            if (color[i] == c) { exists = true; break; }
        }
        if (exists) mapC[c] = ++idx;
    }
    for (int i = 1; i <= N; ++i) color[i] = mapC[color[i]];
    C = idx;
}

bool passLoweringColors(vector<int>& color, int& C, const vector<vector<int>>& adj, mt19937_64& rng) {
    int N = (int)color.size() - 1;
    vector<vector<int>> buckets(C + 1);
    for (int i = 1; i <= N; ++i) buckets[color[i]].push_back(i);
    for (int c = C; c >= 1; --c) {
        auto& vlist = buckets[c];
        if (!vlist.empty()) shuffle(vlist.begin(), vlist.end(), rng);
    }
    bool changed = false;
    bitset<MAXC> used;
    for (int c = C; c >= 1; --c) {
        auto& vlist = buckets[c];
        for (int v : vlist) {
            used.reset();
            for (int u : adj[v]) {
                int cu = color[u];
                if (cu >= 1 && cu < MAXC) used.set(cu);
            }
            int newc = 0;
            for (int d = 1; d < color[v]; ++d) {
                if (!used.test(d)) { newc = d; break; }
            }
            if (newc > 0) {
                color[v] = newc;
                changed = true;
            }
        }
    }
    if (changed) {
        compressColors(color, C);
    }
    return changed;
}

bool attemptEliminateTopColor(vector<int>& color, int& C, const vector<vector<int>>& adj, mt19937_64& rng) {
    int N = (int)color.size() - 1;
    int top = C;
    vector<int> topVertices;
    topVertices.reserve(N);
    for (int i = 1; i <= N; ++i) if (color[i] == top) topVertices.push_back(i);
    if (topVertices.empty()) {
        compressColors(color, C);
        return false;
    }
    shuffle(topVertices.begin(), topVertices.end(), rng);
    vector<int> backup = color;
    bitset<MAXC> used;
    for (int v : topVertices) {
        used.reset();
        for (int u : adj[v]) {
            int cu = color[u];
            if (cu >= 1 && cu < MAXC) used.set(cu);
        }
        int newc = 0;
        for (int d = 1; d < top; ++d) {
            if (!used.test(d)) { newc = d; break; }
        }
        if (newc == 0) {
            color = backup;
            return false;
        }
        color[v] = newc;
    }
    compressColors(color, C);
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<char>> mat(N + 1, vector<char>(N + 1, 0));
    vector<vector<int>> adj(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v;
        if (u == v) continue;
        if (!mat[u][v]) {
            mat[u][v] = mat[v][u] = 1;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }

    vector<int> deg(N + 1);
    for (int i = 1; i <= N; ++i) deg[i] = (int)adj[i].size();

    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85;

    vector<int> bestColor(N + 1, 1);
    int bestC = N;

    int iter = 0;
    do {
        auto res = dsatur(adj, deg, rng);
        vector<int> color = res.first;
        int C = res.second;

        // Local refinement passes
        for (int pass = 0; pass < 3; ++pass) {
            bool changed = passLoweringColors(color, C, adj, rng);
            if (!changed) break;
        }
        // Try to eliminate top colors a few times
        for (int at = 0; at < 3; ++at) {
            if (!attemptEliminateTopColor(color, C, adj, rng)) break;
            for (int pass = 0; pass < 2; ++pass) {
                bool changed = passLoweringColors(color, C, adj, rng);
                if (!changed) break;
            }
        }

        if (C < bestC) {
            bestC = C;
            bestColor = color;
            if (bestC <= 1) break;
        }

        ++iter;
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT) break;
    } while (true);

    // Final compression and output
    compressColors(bestColor, bestC);
    for (int i = 1; i <= N; ++i) {
        cout << bestColor[i] << "\n";
    }
    return 0;
}