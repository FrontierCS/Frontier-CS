#include <bits/stdc++.h>
using namespace std;

struct ColorResult {
    vector<int> color;
    int K;
};

ColorResult runGreedy(const vector<vector<int>>& compAdj, const vector<int>& order) {
    int N = (int)compAdj.size();
    vector<int> color(N, 0);
    int K = 0;
    for (int u : order) {
        if (K == 0) {
            color[u] = ++K;
            continue;
        }
        vector<char> blocked(K + 1, 0);
        for (int v : compAdj[u]) {
            int c = color[v];
            if (c > 0 && c <= K) blocked[c] = 1;
        }
        int assign = 0;
        for (int c = 1; c <= K; ++c) {
            if (!blocked[c]) { assign = c; break; }
        }
        if (assign == 0) assign = ++K;
        color[u] = assign;
    }
    return {color, K};
}

ColorResult runDSATUR(const vector<vector<int>>& compAdj, const vector<int>& degC, mt19937& rng, bool randomTie) {
    int N = (int)compAdj.size();
    vector<int> color(N, 0);
    vector<int> sat(N, 0);
    vector<int> remDeg = degC;
    vector<vector<unsigned char>> used(N, vector<unsigned char>(N + 1, 0));
    int K = 0;
    int remain = N;

    while (remain > 0) {
        int maxSat = -1, maxDeg = -1;
        vector<int> cands;
        cands.reserve(N);
        for (int i = 0; i < N; ++i) {
            if (color[i] != 0) continue;
            if (sat[i] > maxSat) {
                maxSat = sat[i];
                maxDeg = remDeg[i];
                cands.clear();
                cands.push_back(i);
            } else if (sat[i] == maxSat) {
                if (remDeg[i] > maxDeg) {
                    maxDeg = remDeg[i];
                    cands.clear();
                    cands.push_back(i);
                } else if (remDeg[i] == maxDeg) {
                    cands.push_back(i);
                }
            }
        }
        int u;
        if (randomTie && cands.size() > 1) {
            uniform_int_distribution<int> dist(0, (int)cands.size() - 1);
            u = cands[dist(rng)];
        } else {
            u = cands[0];
        }

        int assign = 0;
        for (int c = 1; c <= K; ++c) {
            if (used[u][c] == 0) { assign = c; break; }
        }
        if (assign == 0) assign = ++K;
        color[u] = assign;
        remain--;

        for (int v : compAdj[u]) {
            if (color[v] == 0) {
                if (used[v][assign] == 0) {
                    used[v][assign] = 1;
                    sat[v]++;
                }
                remDeg[v]--;
            }
        }
    }
    return {color, K};
}

void reduceColors(vector<int>& color, int& K, const vector<vector<int>>& compAdj) {
    int N = (int)color.size();
    if (K <= 1) return;

    vector<vector<int>> buckets(K + 1);
    vector<int> pos(N, -1);
    for (int i = 0; i < N; ++i) {
        int c = color[i];
        if (c <= 0) continue;
        pos[i] = (int)buckets[c].size();
        buckets[c].push_back(i);
    }

    int c = K;
    while (c >= 2) {
        vector<int> vertices = buckets[c]; // snapshot since we will modify buckets[c]
        for (int u : vertices) {
            if (color[u] != c) continue; // may have been moved already
            vector<char> blocked(c, 0); // only need 1..c-1
            for (int v : compAdj[u]) {
                int cv = color[v];
                if (cv > 0 && cv < c) blocked[cv] = 1;
            }
            int target = 0;
            for (int t = 1; t < c; ++t) {
                if (!blocked[t]) { target = t; break; }
            }
            if (target != 0) {
                // remove u from buckets[c]
                int idx = pos[u];
                int last = buckets[c].back();
                buckets[c][idx] = last;
                pos[last] = idx;
                buckets[c].pop_back();

                // add u to buckets[target]
                pos[u] = (int)buckets[target].size();
                buckets[target].push_back(u);
                color[u] = target;
            }
        }
        if (buckets[c].empty()) {
            if (c != K) {
                // move color K to c
                for (int v : buckets[K]) {
                    color[v] = c;
                }
                for (int v : buckets[K]) {
                    pos[v] = (int)buckets[c].size();
                    buckets[c].push_back(v);
                }
                buckets[K].clear();
            }
            --K;
            // process the newly moved color now at index c
            continue;
        }
        --c;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<vector<char>> g(N, vector<char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        g[u][v] = 1;
        g[v][u] = 1;
    }

    vector<vector<int>> compAdj(N);
    vector<int> degC(N, 0);
    for (int u = 0; u < N; ++u) {
        for (int v = u + 1; v < N; ++v) {
            if (!g[u][v]) {
                compAdj[u].push_back(v);
                compAdj[v].push_back(u);
                degC[u]++;
                degC[v]++;
            }
        }
    }

    mt19937 rng((unsigned)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Initial attempts
    ColorResult best;
    best.color.assign(N, 0);
    best.K = N + 1; // worse than possible

    // DSATUR attempt
    {
        ColorResult r = runDSATUR(compAdj, degC, rng, true);
        if (r.K < best.K) best = r;
    }

    // Welsh-Powell descending degree
    {
        vector<int> ord(N);
        iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int a, int b){
            if (degC[a] != degC[b]) return degC[a] > degC[b];
            return a < b;
        });
        ColorResult r = runGreedy(compAdj, ord);
        if (r.K < best.K) best = r;
    }

    // Random greedy runs within time budget
    auto start = chrono::steady_clock::now();
    const double timeBudget = 1.7; // seconds for search; leave some for improvement/output
    vector<int> ord(N);
    iota(ord.begin(), ord.end(), 0);
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > timeBudget) break;
        shuffle(ord.begin(), ord.end(), rng);
        ColorResult r = runGreedy(compAdj, ord);
        if (r.K < best.K) best = r;
    }

    // Optional extra DSATUR if some time remains
    {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed < 1.4) {
            ColorResult r = runDSATUR(compAdj, degC, rng, true);
            if (r.K < best.K) best = r;
        }
    }

    // Improvement pass to try to reduce color count
    reduceColors(best.color, best.K, compAdj);

    for (int i = 0; i < N; ++i) {
        int id = best.color[i];
        if (id <= 0) id = 1;
        cout << id << '\n';
    }
    return 0;
}