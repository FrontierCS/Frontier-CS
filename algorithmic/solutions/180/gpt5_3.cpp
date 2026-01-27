#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool nextInt(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) {
            val = val * 10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
};

struct RNG {
    uint64_t x;
    RNG() {
        uint64_t t = chrono::high_resolution_clock::now().time_since_epoch().count();
        x = splitmix64(t);
    }
    static uint64_t splitmix64(uint64_t z) {
        z += 0x9e3779b97f4a7c15ULL;
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint64_t next() {
        x = splitmix64(x);
        return x;
    }
    inline int nextInt(int n) {
        return (int)(next() % (uint64_t)n);
    }
    inline double nextDouble() {
        return (next() >> 11) * (1.0 / 9007199254740992.0);
    }
};

int main() {
    FastScanner fs;
    int n;
    long long m;
    if (!fs.nextInt(n)) return 0;
    fs.nextInt(m);

    int W = (n + 63) >> 6;
    vector<uint64_t> g1bits((size_t)n * W, 0ULL);
    auto setEdgeG1 = [&](int u, int v) {
        g1bits[(size_t)u * W + (v >> 6)] |= (1ULL << (v & 63));
        g1bits[(size_t)v * W + (u >> 6)] |= (1ULL << (u & 63));
    };
    auto hasEdgeG1 = [&](int u, int v) -> int {
        return (int)((g1bits[(size_t)u * W + (v >> 6)] >> (v & 63)) & 1ULL);
    };

    vector<int> deg1(n, 0), deg2(n, 0);
    // Read G1 edges
    for (long long i = 0; i < m; ++i) {
        int u, v;
        fs.nextInt(u); fs.nextInt(v);
        --u; --v;
        if (u == v) continue;
        setEdgeG1(u, v);
        deg1[u]++; deg1[v]++;
    }

    // Read G2 edges
    vector<vector<int>> g2(n);
    g2.reserve(n);
    for (long long i = 0; i < m; ++i) {
        int u, v;
        fs.nextInt(u); fs.nextInt(v);
        --u; --v;
        if (u == v) continue;
        g2[u].push_back(v);
        g2[v].push_back(u);
        deg2[u]++; deg2[v]++;
    }

    // Precompute neighbor degree sums
    vector<long long> sumNbrDeg1(n, 0), sumNbrDeg2(n, 0);
    // For G2 using adjacency lists
    for (int i = 0; i < n; ++i) {
        long long s = 0;
        for (int v : g2[i]) s += deg2[v];
        sumNbrDeg2[i] = s;
    }
    // For G1 using bitsets
    for (int i = 0; i < n; ++i) {
        long long s = 0;
        int base = i * W;
        for (int w = 0; w < W; ++w) {
            uint64_t row = g1bits[base + w];
            while (row) {
                int b = __builtin_ctzll(row);
                int v = (w << 6) + b;
                if (v < n) s += deg1[v];
                row &= row - 1;
            }
        }
        sumNbrDeg1[i] = s;
    }

    // Initial mappings based on sorting by (deg, sumNbrDeg)
    vector<int> ord1(n), ord2(n);
    iota(ord1.begin(), ord1.end(), 0);
    iota(ord2.begin(), ord2.end(), 0);

    auto cmp1 = [&](int a, int b) {
        if (deg1[a] != deg1[b]) return deg1[a] < deg1[b];
        if (sumNbrDeg1[a] != sumNbrDeg1[b]) return sumNbrDeg1[a] < sumNbrDeg1[b];
        return a < b;
    };
    auto cmp2 = [&](int a, int b) {
        if (deg2[a] != deg2[b]) return deg2[a] < deg2[b];
        if (sumNbrDeg2[a] != sumNbrDeg2[b]) return sumNbrDeg2[a] < sumNbrDeg2[b];
        return a < b;
    };
    sort(ord1.begin(), ord1.end(), cmp1);
    sort(ord2.begin(), ord2.end(), cmp2);

    auto computeContribAndScore = [&](const vector<int> &p, vector<int> &contrib) -> long long {
        contrib.assign(n, 0);
        long long sumc = 0;
        for (int u = 0; u < n; ++u) {
            int pu = p[u];
            int baseRow = pu * W;
            int cnt = 0;
            for (int v : g2[u]) {
                int pv = p[v];
                cnt += (int)((g1bits[(size_t)baseRow + (pv >> 6)] >> (pv & 63)) & 1ULL);
            }
            contrib[u] = cnt;
            sumc += cnt;
        }
        return sumc / 2;
    };

    vector<int> p_best(n, 0), p_candidate(n, 0);
    for (int i = 0; i < n; ++i) p_candidate[ord2[i]] = ord1[i];
    vector<int> contrib(n);
    long long bestMatched = computeContribAndScore(p_candidate, contrib);
    p_best = p_candidate;

    // Try reversed mapping as alternative
    vector<int> p_rev(n);
    for (int i = 0; i < n; ++i) p_rev[ord2[i]] = ord1[n - 1 - i];
    vector<int> contrib_rev;
    contrib_rev.resize(n);
    long long matched_rev = computeContribAndScore(p_rev, contrib_rev);

    if (matched_rev > bestMatched) {
        p_best.swap(p_rev);
        contrib.swap(contrib_rev);
        bestMatched = matched_rev;
    }

    // Local search improvement (randomized hill-climbing)
    RNG rng;
    auto startTime = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 1.85; // Soft time budget for improvement
    const double INIT_TEMP = 0.1;
    const double FINAL_TEMP = 0.01;

    auto elapsedSec = [&]() -> double {
        auto now = chrono::steady_clock::now();
        chrono::duration<double> diff = now - startTime;
        return diff.count();
    };

    auto trySwapDelta = [&](int a, int b, const vector<int> &p) -> int {
        int pa = p[a], pb = p[b];
        int baseA_old = pa * W;
        int baseB_old = pb * W;
        int delta = 0;

        // For neighbors of a (excluding b)
        for (int u : g2[a]) {
            if (u == b) continue;
            int pu = p[u];
            int before = (int)((g1bits[(size_t)baseA_old + (pu >> 6)] >> (pu & 63)) & 1ULL);
            int after  = (int)((g1bits[(size_t)baseB_old + (pu >> 6)] >> (pu & 63)) & 1ULL);
            delta += (after - before);
        }
        // For neighbors of b (excluding a)
        for (int v : g2[b]) {
            if (v == a) continue;
            int pv = p[v];
            int before = (int)((g1bits[(size_t)baseB_old + (pv >> 6)] >> (pv & 63)) & 1ULL);
            int after  = (int)((g1bits[(size_t)baseA_old + (pv >> 6)] >> (pv & 63)) & 1ULL);
            delta += (after - before);
        }
        // Edge (a,b) remains unchanged
        return delta;
    };

    auto applySwapUpdate = [&](int a, int b, vector<int> &p, vector<int> &contrib, long long &matched) {
        int pa = p[a], pb = p[b];
        int baseA_old = pa * W;
        int baseB_old = pb * W;

        int sumA = 0;
        for (int u : g2[a]) {
            if (u == b) continue;
            int pu = p[u];
            int before = (int)((g1bits[(size_t)baseA_old + (pu >> 6)] >> (pu & 63)) & 1ULL);
            int after  = (int)((g1bits[(size_t)baseB_old + (pu >> 6)] >> (pu & 63)) & 1ULL);
            int diff = after - before;
            if (diff) {
                contrib[u] += diff;
                sumA += diff;
            }
        }
        int sumB = 0;
        for (int v : g2[b]) {
            if (v == a) continue;
            int pv = p[v];
            int before = (int)((g1bits[(size_t)baseB_old + (pv >> 6)] >> (pv & 63)) & 1ULL);
            int after  = (int)((g1bits[(size_t)baseA_old + (pv >> 6)] >> (pv & 63)) & 1ULL);
            int diff = after - before;
            if (diff) {
                contrib[v] += diff;
                sumB += diff;
            }
        }
        // Update contrib[a], contrib[b]
        contrib[a] += sumA;
        contrib[b] += sumB;
        // Update mapping
        p[a] = pb;
        p[b] = pa;
        // Update matched edges count
        matched += (sumA + sumB);
    };

    vector<int> p = p_best;
    long long matched = bestMatched;
    // If contrib corresponds to p_best; else recompute
    if (true) {
        // Ensure contrib matches p
        computeContribAndScore(p, contrib);
        matched = 0;
        for (int i = 0; i < n; ++i) matched += contrib[i];
        matched /= 2;
    }

    int S1 = max(10, min(50, n / 20)); // sample size for choosing 'a'
    int KRandB = max(20, min(60, n / 30)); // random candidate b's
    int KNeighB = 8; // neighbor-based b candidates

    // Build an index vector for convenience
    vector<int> idxVertices(n);
    iota(idxVertices.begin(), idxVertices.end(), 0);

    // Local search loop
    while (elapsedSec() < TIME_LIMIT_SEC) {
        // Temperature for simulated annealing acceptance (optional)
        double t = elapsedSec() / TIME_LIMIT_SEC;
        double TEMP = INIT_TEMP * pow(FINAL_TEMP / max(1e-12, INIT_TEMP), t);

        // Choose a candidate 'a' with high mismatch
        int bestA = -1;
        int bestBad = -1;
        for (int r = 0; r < S1; ++r) {
            int a = rng.nextInt(n);
            int bad = deg2[a] - contrib[a];
            if (bad > bestBad) {
                bestBad = bad;
                bestA = a;
            }
        }
        if (bestA == -1) bestA = rng.nextInt(n);

        // Build candidate b list
        vector<int> candidates;
        candidates.reserve(KRandB + KNeighB + 4);

        // From neighbors of 'a' in G2
        if (!g2[bestA].empty()) {
            int d = (int)g2[bestA].size();
            if (d <= KNeighB) {
                for (int v : g2[bestA]) {
                    if (v != bestA) candidates.push_back(v);
                }
            } else {
                for (int k = 0; k < KNeighB; ++k) {
                    int v = g2[bestA][rng.nextInt(d)];
                    if (v != bestA) candidates.push_back(v);
                }
            }
        }

        // Random candidates
        while ((int)candidates.size() < KRandB + KNeighB) {
            int b = rng.nextInt(n);
            if (b == bestA) continue;
            candidates.push_back(b);
        }

        // Pick best b among candidates
        int bestB = -1;
        int bestDelta = INT_MIN;
        // Deduplicate small set
        sort(candidates.begin(), candidates.end());
        candidates.erase(unique(candidates.begin(), candidates.end()), candidates.end());

        for (int b : candidates) {
            if (b == bestA) continue;
            int delta = trySwapDelta(bestA, b, p);
            if (delta > bestDelta) {
                bestDelta = delta;
                bestB = b;
            }
        }

        if (bestB != -1) {
            if (bestDelta > 0) {
                applySwapUpdate(bestA, bestB, p, contrib, matched);
            } else if (bestDelta == 0) {
                // occasionally accept neutral move to escape plateaus
                if (rng.nextDouble() < 0.001) {
                    applySwapUpdate(bestA, bestB, p, contrib, matched);
                }
            } else {
                // simulated annealing acceptance for negative moves (rare)
                double prob = exp((double)bestDelta / max(1e-9, TEMP));
                if (rng.nextDouble() < prob) {
                    applySwapUpdate(bestA, bestB, p, contrib, matched);
                }
            }
        }
    }

    // Output permutation p: map vertex i of G2 to vertex p[i] of G1 (1-based)
    for (int i = 0; i < n; ++i) {
        if (i) putchar(' ');
        int out = p[i] + 1;
        // print int quickly
        char buf[20];
        int pos = 0;
        if (out == 0) buf[pos++] = '0';
        else {
            int x = out;
            char tmp[20];
            int tpos = 0;
            while (x > 0) {
                tmp[tpos++] = char('0' + (x % 10));
                x /= 10;
            }
            while (tpos--) buf[pos++] = tmp[tpos];
        }
        fwrite(buf, 1, pos, stdout);
    }
    putchar('\n');
    return 0;
}