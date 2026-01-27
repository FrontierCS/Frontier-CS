#include <bits/stdc++.h>
using namespace std;

struct Timer {
    chrono::high_resolution_clock::time_point st;
    Timer() { reset(); }
    void reset() { st = chrono::high_resolution_clock::now(); }
    double elapsed() const {
        return chrono::duration<double>(chrono::high_resolution_clock::now() - st).count();
    }
};

static inline int firstSetBit(const vector<uint64_t>& bs) {
    for (int i = 0; i < (int)bs.size(); ++i) {
        uint64_t w = bs[i];
        if (w) return i * 64 + __builtin_ctzll(w);
    }
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    int B = (N + 63) / 64;
    vector<vector<uint64_t>> adjBits(N, vector<uint64_t>(B, 0ULL));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (u < 0 || u >= N || v < 0 || v >= N) continue;
        adjBits[u][v / 64] |= (1ULL << (v % 64));
        adjBits[v][u / 64] |= (1ULL << (u % 64));
    }
    // Build adjacency lists and degrees
    vector<vector<int>> G(N);
    vector<int> deg(N, 0);
    for (int i = 0; i < N; ++i) {
        vector<int> row;
        row.reserve(64);
        for (int j = 0; j < B; ++j) {
            uint64_t w = adjBits[i][j];
            while (w) {
                uint64_t t = w & -w;
                int b = __builtin_ctzll(w);
                int v = j * 64 + b;
                if (v < N && v != i) row.push_back(v);
                w ^= t;
            }
        }
        sort(row.begin(), row.end());
        row.erase(unique(row.begin(), row.end()), row.end());
        G[i] = move(row);
        deg[i] = (int)G[i].size();
    }

    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto buildMIS_GRASP = [&](double alpha)->vector<char> {
        vector<int> d = deg;
        vector<char> alive(N, 1);
        int aliveCount = N;
        vector<char> inS(N, 0);
        while (aliveCount > 0) {
            int dmin = INT_MAX, dmax = -1;
            for (int i = 0; i < N; ++i) if (alive[i]) {
                int di = d[i];
                if (di < dmin) dmin = di;
                if (di > dmax) dmax = di;
            }
            int thr = dmin + (int)floor(alpha * (double)(dmax - dmin));
            vector<int> cand;
            cand.reserve(N);
            for (int i = 0; i < N; ++i) if (alive[i] && d[i] <= thr) cand.push_back(i);
            if (cand.empty()) {
                // fallback: pick any alive with min degree
                for (int i = 0; i < N; ++i) if (alive[i] && d[i] == dmin) cand.push_back(i);
                if (cand.empty()) {
                    // pick any alive
                    for (int i = 0; i < N; ++i) if (alive[i]) { cand.push_back(i); break; }
                }
            }
            int u = cand[rng() % cand.size()];
            inS[u] = 1;
            auto remove_vertex = [&](int w) {
                if (!alive[w]) return;
                alive[w] = 0;
                --aliveCount;
                for (int x : G[w]) if (alive[x]) --d[x];
            };
            remove_vertex(u);
            for (int v : G[u]) remove_vertex(v);
        }
        return inS;
    };

    auto augment_to_maximal = [&](vector<char>& inS) {
        vector<int> cnt(N, 0);
        for (int i = 0; i < N; ++i) if (inS[i]) {
            for (int v : G[i]) ++cnt[v];
        }
        vector<int> q;
        q.reserve(N);
        for (int v = 0; v < N; ++v) if (!inS[v] && cnt[v] == 0) q.push_back(v);
        while (!q.empty()) {
            int z = q.back(); q.pop_back();
            if (inS[z] || cnt[z] != 0) continue;
            inS[z] = 1;
            for (int t : G[z]) ++cnt[t];
        }
    };

    auto improve_two_for_one = [&](vector<char>& inS, double timeLimit, Timer& tim) {
        // Build initial counts
        vector<int> cnt(N, 0);
        for (int i = 0; i < N; ++i) if (inS[i]) {
            for (int v : G[i]) ++cnt[v];
        }
        vector<int> sNodes;
        sNodes.reserve(N);
        for (int i = 0; i < N; ++i) if (inS[i]) sNodes.push_back(i);

        int Bsz = B;
        auto clearBit = [&](vector<uint64_t>& bs, int idx) {
            bs[idx / 64] &= ~(1ULL << (idx % 64));
        };
        auto andNot = [&](const vector<uint64_t>& A, const vector<uint64_t>& Bmask, vector<uint64_t>& out) {
            int L = (int)A.size();
            out.resize(L);
            for (int i = 0; i < L; ++i) out[i] = A[i] & ~Bmask[i];
        };
        bool improved_any = false;

        while (tim.elapsed() < timeLimit) {
            bool improved = false;
            sNodes.clear();
            for (int i = 0; i < N; ++i) if (inS[i]) sNodes.push_back(i);
            shuffle(sNodes.begin(), sNodes.end(), rng);

            for (int u : sNodes) {
                if (tim.elapsed() >= timeLimit) break;
                // Build list P: neighbors v of u with cnt[v] == 1 and not in S
                vector<int> P;
                P.reserve(G[u].size());
                for (int v : G[u]) {
                    if (!inS[v] && cnt[v] == 1) P.push_back(v);
                }
                if ((int)P.size() < 2) continue;
                // Build Pbits
                vector<uint64_t> Pbits(Bsz, 0ULL);
                for (int v : P) Pbits[v / 64] |= (1ULL << (v % 64));
                bool found = false;
                int a = -1, b = -1;
                vector<uint64_t> tmp;
                for (int v : P) {
                    andNot(Pbits, adjBits[v], tmp);
                    clearBit(tmp, v); // remove self
                    int bidx = firstSetBit(tmp);
                    if (bidx != -1 && bidx < N) {
                        a = v; b = bidx;
                        found = true;
                        break;
                    }
                }
                if (!found) continue;

                // Apply 1-out 2-in exchange: remove u, add a and b
                inS[u] = 0;
                for (int x : G[u]) --cnt[x];

                inS[a] = 1;
                for (int x : G[a]) ++cnt[x];

                inS[b] = 1;
                for (int x : G[b]) ++cnt[x];

                // Augment to maximal (vertices with cnt==0 and not in S)
                vector<int> q;
                q.reserve(N);
                for (int v = 0; v < N; ++v) if (!inS[v] && cnt[v] == 0) q.push_back(v);
                while (!q.empty()) {
                    int z = q.back(); q.pop_back();
                    if (inS[z] || cnt[z] != 0) continue;
                    inS[z] = 1;
                    for (int t : G[z]) ++cnt[t];
                }

                improved = true;
                improved_any = true;
                break; // restart scanning S after improvement
            }
            if (!improved) break;
        }
        return improved_any;
    };

    Timer timer;
    double totalTime = 1.95; // seconds
    double improveTimeShare = 0.55; // fraction of time kept for improvement
    double buildLimit = totalTime * (1.0 - improveTimeShare);

    vector<char> bestS(N, 0);
    int bestK = -1;

    // Initial deterministic run
    {
        vector<char> cand = buildMIS_GRASP(0.0);
        int K = 0; for (char c : cand) if (c) ++K;
        if (K > bestK) { bestK = K; bestS = cand; }
    }
    // Randomized restarts
    uniform_real_distribution<double> distAlpha(0.0, 1.0);
    while (timer.elapsed() < buildLimit) {
        double alpha = distAlpha(rng) * 0.7; // cap alpha to 0.7 to keep some greediness
        vector<char> cand = buildMIS_GRASP(alpha);
        int K = 0; for (char c : cand) if (c) ++K;
        if (K > bestK) { bestK = K; bestS = cand; }
    }

    // Improvement phase
    double remTime = totalTime - timer.elapsed();
    if (remTime > 0.01) {
        improve_two_for_one(bestS, timer.elapsed() + remTime, timer);
    }

    // Output result
    for (int i = 0; i < N; ++i) {
        cout << (bestS[i] ? 1 : 0) << '\n';
    }
    return 0;
}