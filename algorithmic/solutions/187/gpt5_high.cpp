#include <bits/stdc++.h>
using namespace std;

static const int MAXB = 512;

struct DSRes {
    vector<int> color;
    int K;
};

DSRes dsatur_coloring(const vector<vector<unsigned char>>& g, const vector<int>& degH, mt19937& rng) {
    int N = (int)g.size();
    vector<int> color(N, 0);
    vector<int> satdeg(N, 0);
    vector<bitset<MAXB>> used(N); // colors used by complement neighbors
    vector<char> uncolored(N, 1);

    int Kcurr = 0;
    int colored = 0;

    while (colored < N) {
        int maxSat = -1, maxDeg = -1;
        vector<int> cands;
        cands.reserve(N);
        for (int u = 0; u < N; ++u) {
            if (!uncolored[u]) continue;
            if (satdeg[u] > maxSat) {
                maxSat = satdeg[u];
                maxDeg = degH[u];
                cands.clear();
                cands.push_back(u);
            } else if (satdeg[u] == maxSat) {
                if (degH[u] > maxDeg) {
                    maxDeg = degH[u];
                    cands.clear();
                    cands.push_back(u);
                } else if (degH[u] == maxDeg) {
                    cands.push_back(u);
                }
            }
        }

        int v;
        if ((int)cands.size() == 1) v = cands[0];
        else v = cands[rng() % cands.size()];

        int c;
        for (c = 1; c <= Kcurr; ++c) {
            if (!used[v].test(c)) break;
        }
        if (c == Kcurr + 1) Kcurr++;

        color[v] = c;
        uncolored[v] = 0;
        colored++;

        for (int u = 0; u < N; ++u) {
            if (!uncolored[u]) continue;
            if (!g[v][u]) { // edge in complement
                if (!used[u].test(c)) {
                    used[u].set(c);
                    satdeg[u]++;
                }
            }
        }
    }

    return {color, Kcurr};
}

int compress_colors(vector<int>& color) {
    int N = (int)color.size();
    int K = 0;
    for (int i = 0; i < N; ++i) K = max(K, color[i]);
    vector<int> mapc(K + 1, 0);
    int nxt = 0;
    for (int i = 0; i < N; ++i) {
        int c = color[i];
        if (!mapc[c]) mapc[c] = ++nxt;
        color[i] = mapc[c];
    }
    return nxt;
}

int reduce_colors_greedy(const vector<bitset<MAXB>>& gbits, vector<int>& color) {
    int N = (int)gbits.size();
    int K = 0;
    for (int i = 0; i < N; ++i) K = max(K, color[i]);
    if (K <= 1) return K;

    vector<vector<int>> classes(K + 1);
    vector<bitset<MAXB>> classBits(K + 1);
    for (int v = 0; v < N; ++v) {
        int c = color[v];
        classes[c].push_back(v);
        classBits[c].set(v);
    }

    for (int col = K; col >= 2; --col) {
        bool changed = true;
        while (changed) {
            changed = false;
            for (size_t idx = 0; idx < classes[col].size(); ++idx) {
                int v = classes[col][idx];
                for (int d = 1; d < col; ++d) {
                    if (classBits[d].none()) {
                        // Move v to empty class d
                        color[v] = d;
                        classBits[col].reset(v);
                        classBits[d].set(v);
                        classes[d].push_back(v);
                        classes[col][idx] = classes[col].back();
                        classes[col].pop_back();
                        --idx;
                        changed = true;
                        break;
                    } else {
                        // Check if all in class d are neighbors of v in G
                        if ((gbits[v] & classBits[d]) == classBits[d]) {
                            color[v] = d;
                            classBits[col].reset(v);
                            classBits[d].set(v);
                            classes[d].push_back(v);
                            classes[col][idx] = classes[col].back();
                            classes[col].pop_back();
                            --idx;
                            changed = true;
                            break;
                        }
                    }
                }
            }
        }
    }

    // Compress colors to 1..newK
    vector<int> mapc(K + 1, 0);
    int newK = 0;
    for (int c = 1; c <= K; ++c) {
        if (classBits[c].any()) mapc[c] = ++newK;
    }
    for (int v = 0; v < N; ++v) color[v] = mapc[color[v]];
    return newK;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<unsigned char>> g(N, vector<unsigned char>(N, 0));
    vector<int> degG(N, 0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!g[u][v]) {
            g[u][v] = g[v][u] = 1;
            degG[u]++; degG[v]++;
        }
    }

    vector<int> degH(N);
    for (int i = 0; i < N; ++i) degH[i] = (N - 1) - degG[i];

    // Precompute G adjacency bitsets for reduction phase
    vector<bitset<MAXB>> gbits(N);
    for (int i = 0; i < N; ++i) {
        bitset<MAXB> b;
        for (int j = 0; j < N; ++j) if (g[i][j]) b.set(j);
        gbits[i] = b;
    }

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937 rng((unsigned)seed);

    auto start = chrono::steady_clock::now();
    const double timeLimitMs = 1850.0;

    DSRes best;
    best.K = N + 1;

    int attempts = 0;
    while (true) {
        DSRes cur = dsatur_coloring(g, degH, rng);
        if (cur.K < best.K) {
            best = cur;
        }

        attempts++;
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double, milli>(now - start).count();
        if (elapsed > timeLimitMs) break;
        // Limit number of attempts based on N to stay safe
        if ((N > 400 && attempts >= 10) || (N > 250 && attempts >= 18) || (N > 150 && attempts >= 28) || (attempts >= 40)) break;
    }

    // Compress and attempt a simple reduction
    best.K = compress_colors(best.color);
    best.K = reduce_colors_greedy(gbits, best.color);

    // Final compression to ensure IDs are 1..K
    best.K = compress_colors(best.color);

    for (int i = 0; i < N; ++i) {
        cout << best.color[i] << '\n';
    }

    return 0;
}