#include <bits/stdc++.h>
using namespace std;

using Clock = std::chrono::steady_clock;

pair<vector<int>, int> dsatur_color(const vector<vector<int>>& g, const vector<int>& deg, mt19937_64& rng, bool randomize) {
    int N = (int)g.size();
    vector<int> color(N, 0);
    vector<int> sat(N, 0);
    int stride = N + 1;
    vector<unsigned char> forbid((size_t)N * stride, 0);
    vector<uint64_t> rkey(N, 0);
    if (randomize) {
        for (int i = 0; i < N; ++i) rkey[i] = rng();
    }
    int maxColor = 0;
    for (int step = 0; step < N; ++step) {
        int u = -1;
        int bestSat = -1;
        int bestDeg = -1;
        uint64_t bestRnd = 0;
        for (int i = 0; i < N; ++i) if (color[i] == 0) {
            int s = sat[i];
            if (s > bestSat) {
                bestSat = s; bestDeg = deg[i]; u = i; bestRnd = rkey[i];
            } else if (s == bestSat) {
                if (deg[i] > bestDeg) {
                    bestDeg = deg[i]; u = i; bestRnd = rkey[i];
                } else if (deg[i] == bestDeg) {
                    if (!randomize) {
                        if (u == -1 || i < u) { u = i; }
                    } else if (rkey[i] > bestRnd) {
                        u = i; bestRnd = rkey[i];
                    }
                }
            }
        }
        int c = 1;
        for (; c <= maxColor; ++c) {
            if (!forbid[u * stride + c]) break;
        }
        if (c > maxColor) c = maxColor + 1;
        color[u] = c;
        if (c > maxColor) maxColor = c;
        for (int v : g[u]) if (color[v] == 0) {
            unsigned char &F = forbid[v * stride + c];
            if (!F) { F = 1; sat[v]++; }
        }
    }
    return {color, maxColor};
}

bool attempt_reduce_max_color(vector<int>& color, int K, const vector<vector<int>>& g, const vector<int>& deg, mt19937_64& rng, int tries, const Clock::time_point& deadline) {
    int N = (int)g.size();
    vector<int> S;
    S.reserve(N);
    for (int i = 0; i < N; ++i) if (color[i] == K) S.push_back(i);
    if (S.empty()) return true;

    vector<unsigned char> inS(N, 0);
    for (int u : S) inS[u] = 1;

    for (int attempt = 0; attempt < tries; ++attempt) {
        if (Clock::now() > deadline) return false;
        // Uncolor S
        for (int u : S) color[u] = 0;

        int stride = K; // colors 1..K-1 map to indices 0..K-2
        vector<unsigned char> forbid((size_t)N * stride, 0);
        vector<int> sat(N, 0);
        vector<uint64_t> rkey(N, 0);
        for (int i = 0; i < N; ++i) if (inS[i]) rkey[i] = rng();

        // Initialize forbid and sat for vertices in S from already colored neighbors (colors 1..K-1)
        for (int u : S) {
            for (int v : g[u]) {
                int cv = color[v];
                if (cv >= 1 && cv <= K - 1) {
                    unsigned char &F = forbid[u * stride + (cv - 1)];
                    if (!F) { F = 1; sat[u]++; }
                }
            }
        }

        int remaining = (int)S.size();
        bool fail = false;
        while (remaining > 0) {
            if (Clock::now() > deadline) { fail = true; break; }
            int u = -1;
            int bestSat = -1, bestDeg = -1;
            uint64_t bestRnd = 0;
            for (int i = 0; i < N; ++i) if (inS[i] && color[i] == 0) {
                int s = sat[i];
                if (s > bestSat) {
                    bestSat = s; bestDeg = deg[i]; bestRnd = rkey[i]; u = i;
                } else if (s == bestSat) {
                    if (deg[i] > bestDeg) {
                        bestDeg = deg[i]; bestRnd = rkey[i]; u = i;
                    } else if (deg[i] == bestDeg) {
                        if (rkey[i] > bestRnd) { bestRnd = rkey[i]; u = i; }
                    }
                }
            }
            if (u == -1) { fail = true; break; }

            int chosen = -1;
            for (int c = 1; c <= K - 1; ++c) {
                if (!forbid[u * stride + (c - 1)]) { chosen = c; break; }
            }
            if (chosen == -1) { fail = true; break; }

            color[u] = chosen;
            remaining--;
            for (int v : g[u]) if (inS[v] && color[v] == 0) {
                unsigned char &F = forbid[v * stride + (chosen - 1)];
                if (!F) { F = 1; sat[v]++; }
            }
        }
        if (!fail) return true;

        // Revert S to K before next attempt
        for (int u : S) color[u] = K;
    }
    return false;
}

int max_color_value(const vector<int>& color) {
    int mc = 0;
    for (int c : color) if (c > mc) mc = c;
    return mc;
}

bool is_valid_coloring(const vector<vector<int>>& g, const vector<int>& color) {
    int N = (int)g.size();
    for (int u = 0; u < N; ++u) {
        if (color[u] <= 0) return false;
        for (int v : g[u]) {
            if (v > u && color[u] == color[v]) return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<vector<int>> g(N);
    vector<unsigned char> present((size_t)N * N, 0);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!present[u * N + v]) {
            present[u * N + v] = present[v * N + u] = 1;
            g[u].push_back(v);
            g[v].push_back(u);
        }
    }
    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)g[i].size();

    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)&rng);

    auto start = Clock::now();
    auto deadline = start + chrono::milliseconds(1900);

    auto run_attempt = [&](bool randomize, int reduceTries) -> pair<vector<int>, int> {
        auto res = dsatur_color(g, deg, rng, randomize);
        vector<int> col = move(res.first);
        int C = res.second;
        // Try to reduce colors greedily
        while (C > 1 && Clock::now() < deadline) {
            bool ok = attempt_reduce_max_color(col, C, g, deg, rng, reduceTries, deadline);
            if (!ok) break;
            C--;
        }
        return {col, C};
    };

    auto best = run_attempt(false, 6);
    vector<int> bestColor = best.first;
    int bestC = best.second;

    // Additional randomized attempts while time permits
    while (Clock::now() < deadline) {
        auto cand = run_attempt(true, 6);
        if (cand.second < bestC) {
            bestC = cand.second;
            bestColor = move(cand.first);
        }
        if (Clock::now() >= deadline) break;
    }

    if (!is_valid_coloring(g, bestColor)) {
        // Fallback: simple greedy coloring by vertex order
        vector<int> color(N, 0);
        for (int u = 0; u < N; ++u) {
            vector<char> used(N + 2, 0);
            for (int v : g[u]) if (color[v]) used[color[v]] = 1;
            int c = 1; while (c <= N && used[c]) ++c;
            color[u] = c;
        }
        bestColor = move(color);
    }

    for (int i = 0; i < N; ++i) {
        cout << bestColor[i] << '\n';
    }
    return 0;
}