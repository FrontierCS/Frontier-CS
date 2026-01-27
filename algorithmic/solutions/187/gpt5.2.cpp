#include <bits/stdc++.h>
using namespace std;

static constexpr int MAXN = 500;
static constexpr int MAXC = 512;

static inline double now_sec() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

static vector<int> dsatur_color(
    int N,
    const vector<bitset<MAXN>>& compAdj,
    const vector<int>& degComp,
    mt19937& rng,
    bool randomized_ties
) {
    vector<int> col(N, 0), satCount(N, 0);
    vector<bitset<MAXC>> sat(N);
    int maxColor = 0;

    for (int step = 0; step < N; step++) {
        int maxSat = -1, maxDeg = -1;
        vector<int> cand;
        cand.reserve(N);

        for (int i = 0; i < N; i++) {
            if (col[i] != 0) continue;
            int s = satCount[i];
            int d = degComp[i];
            if (s > maxSat || (s == maxSat && d > maxDeg)) {
                maxSat = s;
                maxDeg = d;
                cand.clear();
                cand.push_back(i);
            } else if (s == maxSat && d == maxDeg) {
                cand.push_back(i);
            }
        }

        int v = cand[0];
        if (randomized_ties && cand.size() > 1) {
            uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
            v = cand[dist(rng)];
        }

        int c = 1;
        while (c < MAXC && sat[v].test(c)) c++;
        if (c >= MAXC) c = MAXC - 1; // should never happen for N<=500

        col[v] = c;
        if (c > maxColor) maxColor = c;

        for (int u = 0; u < N; u++) {
            if (col[u] != 0) continue;
            if (!compAdj[v].test(u)) continue;
            if (!sat[u].test(c)) {
                sat[u].set(c);
                satCount[u]++;
            }
        }
    }

    return col;
}

static int compress_colors(int N, vector<int>& col, vector<bitset<MAXN>>& classBits) {
    int K = (int)classBits.size() - 1;
    vector<int> mp(K + 1, 0);
    int newK = 0;
    vector<bitset<MAXN>> newBits(K + 1);

    for (int c = 1; c <= K; c++) {
        if (classBits[c].any()) {
            mp[c] = ++newK;
            newBits[newK] = classBits[c];
        }
    }
    newBits.resize(newK + 1);
    classBits.swap(newBits);

    for (int v = 0; v < N; v++) col[v] = mp[col[v]];
    return newK;
}

static int max_color_of(const vector<int>& col) {
    int mx = 0;
    for (int x : col) mx = max(mx, x);
    return mx;
}

static void improve_coloring(
    int N,
    vector<int>& col,
    const vector<bitset<MAXN>>& compAdj,
    mt19937& rng,
    double end_time_sec
) {
    int K = max_color_of(col);
    vector<bitset<MAXN>> classBits(K + 1);
    for (int v = 0; v < N; v++) classBits[col[v]].set(v);

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);

    int stagnant = 0;
    while (now_sec() < end_time_sec) {
        bool anyChange = false;

        shuffle(order.begin(), order.end(), rng);
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            return col[a] > col[b];
        });

        for (int idx = 0; idx < N; idx++) {
            int v = order[idx];
            int old = col[v];
            if (old <= 1) continue;

            for (int c = 1; c < old; c++) {
                if ((compAdj[v] & classBits[c]).none()) {
                    classBits[old].reset(v);
                    classBits[c].set(v);
                    col[v] = c;
                    anyChange = true;
                    break;
                }
            }
        }

        if (anyChange) {
            K = compress_colors(N, col, classBits);
            stagnant = 0;
        } else {
            stagnant++;
            if (stagnant >= 5) break;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    int M;
    if (!(cin >> N >> M)) return 0;

    vector<bitset<MAXN>> adj(N);
    for (int i = 0; i < N; i++) adj[i].set(i);

    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }

    bitset<MAXN> all;
    for (int i = 0; i < N; i++) all.set(i);

    vector<bitset<MAXN>> compAdj(N);
    vector<int> degComp(N, 0);
    for (int i = 0; i < N; i++) {
        compAdj[i] = all & (~adj[i]);
        degComp[i] = (int)compAdj[i].count();
    }

    double start = now_sec();
    double end_time = start + 1.90; // keep margin for output

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)N * 0x9e3779b97f4a7c15ULL;
    seed ^= (uint64_t)M * 0xbf58476d1ce4e5b9ULL;
    mt19937 rng((uint32_t)(seed ^ (seed >> 32)));

    vector<int> bestCol;
    int bestK = N + 1;

    // Always do a deterministic DSATUR first
    {
        auto col = dsatur_color(N, compAdj, degComp, rng, false);
        improve_coloring(N, col, compAdj, rng, min(end_time, now_sec() + 0.35));
        int K = max_color_of(col);
        if (K < bestK) {
            bestK = K;
            bestCol = std::move(col);
        }
    }

    int attempts = 0;
    while (now_sec() < end_time && attempts < 200) {
        bool randomized = true;
        auto col = dsatur_color(N, compAdj, degComp, rng, randomized);

        double local_end = min(end_time, now_sec() + 0.12);
        improve_coloring(N, col, compAdj, rng, local_end);

        int K = max_color_of(col);
        if (K < bestK) {
            bestK = K;
            bestCol = std::move(col);
            if (bestK == 1) break;
        }
        attempts++;
    }

    if (bestCol.empty()) {
        bestCol.assign(N, 1);
    }

    for (int i = 0; i < N; i++) {
        cout << bestCol[i] << "\n";
    }

    return 0;
}