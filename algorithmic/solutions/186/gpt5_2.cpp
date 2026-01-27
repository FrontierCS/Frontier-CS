#include <bits/stdc++.h>
using namespace std;

static const int MAXB = 512;

struct Graph {
    int N;
    vector< bitset<MAXB> > adj;    // adjacency over vertices (size up to N <= 500)
    vector<vector<int>> nb;        // adjacency list
    vector<int> deg;
    Graph(int n=0): N(n), adj(n), nb(n), deg(n,0) {}
};

static inline double now_sec() {
    static auto t0 = chrono::steady_clock::now();
    auto t = chrono::steady_clock::now();
    return chrono::duration<double>(t - t0).count();
}

struct DSResult {
    bool success;
    int maxColorUsed;
    vector<int> color;
};

static int approxCliqueLB(const Graph& G, mt19937_64& rng, double timeLimitSec) {
    int N = G.N;
    if (N == 0) return 0;
    int best = 1;
    int tries = min(6, N); // keep light
    for (int t = 0; t < tries; ++t) {
        if (now_sec() > timeLimitSec) break;
        bitset<MAXB> cand;
        for (int i = 0; i < N; ++i) cand.set(i);
        int sz = 0;
        while (cand.any()) {
            int bestV = -1, bestD = -1;
            // choose vertex with maximum degree within candidate
            for (int i = 0; i < N; ++i) if (cand.test(i)) {
                int d = (G.adj[i] & cand).count();
                if (d > bestD) { bestD = d; bestV = i; }
                else if (d == bestD) {
                    if (((rng() >> 1) & 1ULL) && bestV != -1) {
                        bestV = i;
                    }
                }
            }
            if (bestV == -1) break;
            sz++;
            cand &= G.adj[bestV];
        }
        best = max(best, sz);
    }
    // trivial bound from degree + 1
    int degp1 = 0;
    for (int i = 0; i < G.N; ++i) degp1 = max(degp1, G.deg[i] + 1);
    best = max(best, degp1);
    return best;
}

static int chooseColor(const bitset<MAXB>& forb, int colorLimit, int currentMaxColor, mt19937_64* prng, double noiseProb) {
    int upper = (colorLimit > 0 ? colorLimit : currentMaxColor + 1);
    vector<int> avail;
    avail.reserve(16);
    for (int c = 1; c <= upper; ++c) {
        if (!forb.test(c)) {
            avail.push_back(c);
        }
    }
    if (!avail.empty()) {
        int chosen = avail[0];
        if (prng && noiseProb > 0) {
            uniform_real_distribution<double> U(0.0, 1.0);
            if (U(*prng) < noiseProb) {
                // choose randomly among first few available small colors
                int k = min((int)avail.size(), 3);
                uniform_int_distribution<int> Ui(0, k - 1);
                chosen = avail[Ui(*prng)];
            }
        }
        return chosen;
    } else {
        if (colorLimit > 0) {
            return 0; // fail
        } else {
            // open a new color beyond currentMaxColor+1 if needed
            return upper + 1;
        }
    }
}

static DSResult dsaturGeneral(const Graph& G, int colorLimit, mt19937_64* prng, double noiseProb) {
    int N = G.N;
    DSResult res;
    res.success = true;
    res.maxColorUsed = 0;
    res.color.assign(N, 0);
    vector< bitset<MAXB> > forb(N); // forbidden colors mask per vertex from neighbors
    vector<unsigned short> satDeg(N, 0);
    vector<char> colored(N, 0);
    vector<double> prio(N, 0.0); // for tie-breaking
    if (prng) {
        uniform_real_distribution<double> U(0.0, 1.0);
        for (int i = 0; i < N; ++i) prio[i] = U(*prng);
    }
    int remaining = N;
    while (remaining > 0) {
        int bestV = -1;
        int bestSat = -1;
        int bestDeg = -1;
        for (int i = 0; i < N; ++i) if (!colored[i]) {
            int sd = satDeg[i];
            if (sd > bestSat) {
                bestSat = sd; bestDeg = G.deg[i]; bestV = i;
            } else if (sd == bestSat) {
                if (G.deg[i] > bestDeg) {
                    bestDeg = G.deg[i]; bestV = i;
                } else if (G.deg[i] == bestDeg) {
                    if (prng) {
                        if (prio[i] > (bestV >= 0 ? prio[bestV] : -1.0)) {
                            bestV = i;
                        }
                    } else {
                        if (bestV == -1 || i < bestV) bestV = i;
                    }
                }
            }
        }
        if (bestV == -1) { res.success = false; break; }
        int c = chooseColor(forb[bestV], colorLimit, res.maxColorUsed, prng, noiseProb);
        if (c == 0) { res.success = false; break; }
        res.color[bestV] = c;
        if (c > res.maxColorUsed) res.maxColorUsed = c;
        colored[bestV] = 1;
        --remaining;
        // update neighbors
        for (int u : G.nb[bestV]) if (!colored[u]) {
            if (!forb[u].test(c)) {
                forb[u].set(c);
                ++satDeg[u];
            }
        }
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    Graph G(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!G.adj[u].test(v)) {
            G.adj[u].set(v);
            G.adj[v].set(u);
        }
    }
    for (int i = 0; i < N; ++i) {
        for (int j = G.adj[i]._Find_first(); j < N; j = G.adj[i]._Find_next(j)) {
            G.nb[i].push_back(j);
        }
        G.deg[i] = (int)G.nb[i].size();
    }

    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    double timeBudget = 1.90; // seconds
    double deadline = now_sec() + timeBudget;

    int cliqueLB = approxCliqueLB(G, rng, deadline);

    // Initial DSATUR run
    DSResult best = dsaturGeneral(G, -1, &rng, 0.01);
    if (!best.success) {
        // Fallback greedy if something goes wrong
        best = dsaturGeneral(G, -1, nullptr, 0.0);
    }
    int bestK = best.maxColorUsed;
    vector<int> bestColor = best.color;

    // Try to reduce colors using DSATUR with a color limit
    int target = max(cliqueLB, 1);
    while (bestK > target && now_sec() < deadline) {
        int L = bestK - 1;
        bool improved = false;
        int attempts = 0;
        while (!improved && now_sec() < deadline) {
            double remainingFrac = max(0.0, (deadline - now_sec()) / timeBudget);
            double noise = 0.02 + 0.08 * (1.0 - remainingFrac); // slightly increase noise as time goes
            DSResult trial = dsaturGeneral(G, L, &rng, noise);
            attempts++;
            if (trial.success) {
                bestK = trial.maxColorUsed;
                bestColor = trial.color;
                improved = true;
            } else {
                // limit attempts
                if (attempts > 200) break;
            }
        }
        if (!improved) break; // couldn't reduce further
    }

    // Output final solution
    for (int i = 0; i < N; ++i) {
        int c = bestColor[i];
        if (c <= 0) c = 1;
        cout << c << '\n';
    }
    return 0;
}