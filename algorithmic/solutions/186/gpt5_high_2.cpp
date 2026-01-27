#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 512;

struct DSaturSolver {
    int N;
    const vector<vector<int>>& adj;
    const vector<int>& deg;
    vector<int> color;
    vector<int> sat;
    vector< bitset<MAXN> > used;
    vector<uint32_t> tieRand;
    DSaturSolver(int n, const vector<vector<int>>& adj, const vector<int>& deg)
        : N(n), adj(adj), deg(deg) {
        color.assign(N + 1, 0);
        sat.assign(N + 1, 0);
        used.assign(N + 1, bitset<MAXN>());
        tieRand.assign(N + 1, 0);
    }
    pair<int, vector<int>> run(mt19937_64& rng, bool randomize) {
        fill(color.begin(), color.end(), 0);
        fill(sat.begin(), sat.end(), 0);
        for (int i = 1; i <= N; ++i) {
            used[i].reset();
            tieRand[i] = randomize ? uint32_t(rng()) : uint32_t(i);
        }
        int currentMax = 0;
        for (int colored = 0; colored < N; ++colored) {
            int u = -1;
            int bestSat = -1;
            int bestDeg = -1;
            uint32_t bestRnd = 0;
            for (int v = 1; v <= N; ++v) if (color[v] == 0) {
                int s = sat[v];
                if (s > bestSat) {
                    u = v; bestSat = s; bestDeg = deg[v]; bestRnd = tieRand[v];
                } else if (s == bestSat) {
                    if (deg[v] > bestDeg) {
                        u = v; bestDeg = deg[v]; bestRnd = tieRand[v];
                    } else if (deg[v] == bestDeg) {
                        if (tieRand[v] > bestRnd) {
                            u = v; bestRnd = tieRand[v];
                        }
                    }
                }
            }
            bitset<MAXN>& forb = used[u];
            int c = 1;
            while (c <= currentMax && forb.test(c)) ++c;
            if (c == currentMax + 1) ++currentMax;
            color[u] = c;
            for (int v : adj[u]) if (color[v] == 0) {
                if (!used[v].test(c)) {
                    used[v].set(c);
                    ++sat[v];
                }
            }
        }
        return {currentMax, color};
    }
};

pair<int, vector<int>> greedyColoring(int N, const vector<vector<int>>& adj, const vector<int>& order) {
    vector<int> color(N + 1, 0);
    int C = 0;
    bitset<MAXN> used;
    for (int u : order) {
        used.reset();
        for (int v : adj[u]) {
            int cv = color[v];
            if (cv) used.set(cv);
        }
        int c = 1;
        while (c <= C && used.test(c)) ++c;
        if (c == C + 1) ++C;
        color[u] = c;
    }
    return {C, color};
}

bool reduce_one_color(vector<int>& color, int& K, const vector<vector<int>>& adj) {
    int N = (int)adj.size() - 1;
    vector<int> bucketK;
    bucketK.reserve(N);
    for (int i = 1; i <= N; ++i) if (color[i] == K) bucketK.push_back(i);
    if (bucketK.empty()) { --K; return true; }

    bool changed = false;
    vector<int> neighborCount(K + 1, 0);
    vector<int> neighborRep(K + 1, -1);

    bool anyChange = true;
    while (anyChange) {
        anyChange = false;
        for (int u : bucketK) {
            if (color[u] != K) continue;
            fill(neighborCount.begin(), neighborCount.end(), 0);
            fill(neighborRep.begin(), neighborRep.end(), -1);
            for (int v : adj[u]) {
                int cv = color[v];
                if (cv >= 1 && cv <= K - 1) {
                    neighborCount[cv]++;
                    neighborRep[cv] = v;
                }
            }
            bool recoloredU = false;
            for (int c = 1; c <= K - 1; ++c) {
                if (neighborCount[c] == 0) {
                    color[u] = c;
                    anyChange = true;
                    changed = true;
                    recoloredU = true;
                    break;
                }
            }
            if (recoloredU) continue;
            for (int c = 1; c <= K - 1 && !recoloredU; ++c) if (neighborCount[c] == 1) {
                int v = neighborRep[c];
                bitset<MAXN> used;
                used.reset();
                for (int w : adj[v]) if (w != u) {
                    int cw = color[w];
                    if (cw >= 1 && cw <= K - 1) used.set(cw);
                }
                int d = 1;
                for (; d <= K - 1; ++d) {
                    if (d == c) continue;
                    if (!used.test(d)) break;
                }
                if (d <= K - 1) {
                    color[v] = d;
                    color[u] = c;
                    anyChange = true;
                    changed = true;
                    recoloredU = true;
                    break;
                }
            }
        }
    }
    for (int i = 1; i <= N; ++i) if (color[i] == K) return false;
    --K;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector< bitset<MAXN> > adjMat(N + 1);
    vector<vector<int>> adj(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v;
        if (u == v || u < 1 || v < 1 || u > N || v > N) continue;
        if (!adjMat[u].test(v)) {
            adjMat[u].set(v);
            adjMat[v].set(u);
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }
    vector<int> deg(N + 1, 0);
    for (int i = 1; i <= N; ++i) deg[i] = (int)adj[i].size();

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85;

    vector<int> bestColor(N + 1, 0);
    int bestK = N;

    DSaturSolver ds(N, adj, deg);
    {
        auto res = ds.run(rng, false);
        if (res.first < bestK) {
            bestK = res.first;
            bestColor = move(res.second);
        }
    }

    {
        vector<int> order(N);
        iota(order.begin(), order.end(), 1);
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            if (deg[a] != deg[b]) return deg[a] > deg[b];
            return a < b;
        });
        auto res = greedyColoring(N, adj, order);
        if (res.first < bestK) {
            bestK = res.first;
            bestColor = move(res.second);
        }
    }

    int iter = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT * 0.85) break;
        auto res = ds.run(rng, true);
        if (res.first < bestK) {
            bestK = res.first;
            bestColor = move(res.second);
        }
        ++iter;
        if (bestK <= 3) break; // Good enough, stop early
    }

    // Attempt post-improvement: try to reduce number of colors greedily
    while (bestK > 1) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT) break;
        bool ok = reduce_one_color(bestColor, bestK, adj);
        if (!ok) break;
    }

    for (int i = 1; i <= N; ++i) {
        cout << bestColor[i] << "\n";
    }
    return 0;
}