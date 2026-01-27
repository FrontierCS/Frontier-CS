#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;
using u64 = unsigned long long;

static inline u64 splitmix64(u64 x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long m;
    if (!(cin >> n >> m)) return 0;

    int W = (n + 63) >> 6;

    vector<vector<int>> adj1(n), adj2(n);
    vector<vector<u64>> adj1Bits(n, vector<u64>(W, 0));

    vector<int> deg1(n, 0), deg2(n, 0);

    // Read G1
    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
        deg1[u]++; deg1[v]++;
        adj1Bits[u][v >> 6] |= (1ULL << (v & 63));
        adj1Bits[v][u >> 6] |= (1ULL << (u & 63));
    }

    // Read G2
    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        deg2[u]++; deg2[v]++;
    }

    auto isAdj1 = [&](int u, int v) -> int {
        return int((adj1Bits[u][v >> 6] >> (v & 63)) & 1ULL);
    };

    // WL-like signatures (2 rounds)
    auto computeSig = [&](const vector<vector<int>>& adj, const vector<int>& deg) {
        vector<u64> sig(n);
        u64 salt0 = 0x1234567890abcdefULL;
        for (int i = 0; i < n; ++i) sig[i] = splitmix64((u64)deg[i] + salt0);

        for (int r = 0; r < 2; ++r) {
            vector<u64> nsig(n);
            u64 sa = splitmix64(0xA5A5A5A5A5A5A5A5ULL + r);
            u64 sb = splitmix64(0x5A5A5A5A5A5A5A5AULL + r);
            u64 sc = splitmix64(0xDEADBEEFCAFEBABEULL + r);
            u64 sd = splitmix64(0xC001D00DC0FFEE00ULL + r);
            for (int u = 0; u < n; ++u) {
                u64 sum1 = 0, sum2 = 0, xr = 0, sumd = 0;
                for (int v : adj[u]) {
                    u64 t1 = splitmix64(sig[v] + sa);
                    u64 t2 = splitmix64(sig[v] ^ sb);
                    sum1 += t1;
                    sum2 += t2 + sig[v] * 0x9e3779b97f4a7c15ULL;
                    xr ^= (t1 + 0x9e3779b97f4a7c15ULL);
                    sumd += (u64)deg[v] * 1315423911ULL;
                }
                u64 val = sig[u] * 0x9ddfea08eb382d69ULL;
                val ^= sum1 + (sum2 << 1);
                val += (xr << 1) ^ (xr >> 1);
                val ^= (u64)deg[u] * 0x94d049bb133111ebULL + sumd * 0xbf58476d1ce4e5b9ULL;
                val += (u64)adj[u].size() * 0x2545F4914F6CDD1DULL;
                nsig[u] = splitmix64(val + sc) ^ sd;
            }
            sig.swap(nsig);
        }
        return sig;
    };

    vector<u64> sig1 = computeSig(adj1, deg1);
    vector<u64> sig2 = computeSig(adj2, deg2);

    // Buckets for G1 by signature
    unordered_map<u64, vector<int>> bucket1;
    bucket1.reserve(n * 2);
    for (int v = 0; v < n; ++v) bucket1[sig1[v]].push_back(v);

    // Rarity of G2 nodes based on G1 buckets
    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);
    vector<int> rarity(n, n + 1);
    for (int u = 0; u < n; ++u) {
        auto it = bucket1.find(sig2[u]);
        if (it != bucket1.end()) rarity[u] = (int)it->second.size();
    }

    // Order: smaller rarity first, then higher degree first
    stable_sort(ord.begin(), ord.end(), [&](int a, int b) {
        if (rarity[a] != rarity[b]) return rarity[a] < rarity[b];
        return deg2[a] > deg2[b];
    });

    // Initial greedy mapping
    vector<int> p(n, -1);
    vector<char> used1(n, 0);

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    auto rand64 = [&]() -> u64 { return rng(); };

    const int Ksame = 24;
    const int Kdeg = 24;

    // Precompute list of all vertices for fallback scanning
    vector<int> allIdx(n);
    iota(allIdx.begin(), allIdx.end(), 0);

    for (int idx = 0; idx < n; ++idx) {
        int u = ord[idx];

        vector<int> candidates;
        candidates.reserve(Ksame + Kdeg);

        // same signature candidates
        auto it = bucket1.find(sig2[u]);
        if (it != bucket1.end()) {
            const auto& vec = it->second;
            // collect up to Ksame unused
            int cnt = 0;
            for (int v : vec) {
                if (!used1[v]) {
                    candidates.push_back(v);
                    if (++cnt >= Ksame) break;
                }
            }
        }

        // Degree-close candidates if needed
        if ((int)candidates.size() < Ksame) {
            int need = Kdeg;
            // scan all unused and pick best by degree difference
            // Keep small heap-like buffer
            struct Cand { int diff; int v; };
            vector<Cand> best;
            best.reserve(need + 5);
            int targetDeg = deg2[u];
            for (int v = 0; v < n; ++v) {
                if (used1[v]) continue;
                int diff = abs(deg1[v] - targetDeg);
                if ((int)best.size() < need) {
                    best.push_back({diff, v});
                    if ((int)best.size() == need) {
                        // build max-heap by diff
                        make_heap(best.begin(), best.end(), [](const Cand& a, const Cand& b){ return a.diff < b.diff; });
                    }
                } else if (diff < best.front().diff) {
                    pop_heap(best.begin(), best.end(), [](const Cand& a, const Cand& b){ return a.diff < b.diff; });
                    best.back() = {diff, v};
                    push_heap(best.begin(), best.end(), [](const Cand& a, const Cand& b){ return a.diff < b.diff; });
                }
            }
            // Append from heap
            for (auto &c : best) candidates.push_back(c.v);
        }

        if (candidates.empty()) {
            // fallback: any unused (random sample)
            for (int v = 0; v < n && (int)candidates.size() < Kdeg; ++v) {
                if (!used1[v]) candidates.push_back(v);
            }
        }

        // Choose best candidate by immediate matched edges to already assigned neighbors
        int bestV = -1;
        long long bestScore = LLONG_MIN;
        int udeg = deg2[u];
        for (int v : candidates) {
            // immediate matches with already assigned neighbors
            int match = 0;
            for (int w : adj2[u]) {
                int pw = p[w];
                if (pw != -1) match += isAdj1(v, pw);
            }
            long long penalty = abs(deg1[v] - udeg);
            long long score = match * 1000LL - penalty;
            if (score > bestScore) {
                bestScore = score;
                bestV = v;
            }
        }
        if (bestV == -1) {
            // Should not happen, but pick any unused
            for (int v = 0; v < n; ++v) if (!used1[v]) { bestV = v; break; }
        }
        p[u] = bestV;
        used1[bestV] = 1;
    }

    // Compute initial matched edges
    auto computeMatched = [&](const vector<int>& mapP) -> long long {
        long long cnt = 0;
        for (int u = 0; u < n; ++u) {
            for (int v : adj2[u]) if (v > u) {
                cnt += isAdj1(mapP[u], mapP[v]);
            }
        }
        return cnt;
    };

    long long cur = computeMatched(p);

    // Local improvement by random swaps
    auto deltaSwap = [&](int a, int b) -> long long {
        int pa = p[a], pb = p[b];
        if (pa == pb) return 0;
        long long delta = 0;
        // edges incident to a
        for (int v : adj2[a]) {
            if (v == b) continue;
            delta += isAdj1(pb, p[v]) - isAdj1(pa, p[v]);
        }
        // edges incident to b
        for (int v : adj2[b]) {
            if (v == a) continue;
            delta += isAdj1(pa, p[v]) - isAdj1(pb, p[v]);
        }
        // edge (a,b) contributes the same before/after; delta 0
        return delta;
    };

    auto mismatches = [&](int u) -> int {
        int mis = 0;
        int pu = p[u];
        for (int v : adj2[u]) {
            if (!isAdj1(pu, p[v])) ++mis;
        }
        return mis;
    };

    int ITER = 10000;
    if (n >= 1500) ITER = 15000;
    else if (n >= 1000) ITER = 12000;

    uniform_int_distribution<int> distNode(0, n - 1);

    for (int it = 0; it < ITER; ++it) {
        // pick a with high mismatch among samples
        int a = distNode(rng);
        int bestMis = -1;
        int samplesA = 8;
        for (int s = 0; s < samplesA; ++s) {
            int u = distNode(rng);
            int mis = mismatches(u);
            if (mis > bestMis) {
                bestMis = mis;
                a = u;
            }
        }
        // pick b among samples with best delta
        long long bestDelta = 0;
        int bestB = -1;
        int samplesB = 24;
        for (int s = 0; s < samplesB; ++s) {
            int b = distNode(rng);
            if (b == a) continue;
            long long d = deltaSwap(a, b);
            if (d > bestDelta) {
                bestDelta = d;
                bestB = b;
            }
        }
        if (bestB != -1 && bestDelta > 0) {
            swap(p[a], p[bestB]);
            cur += bestDelta;
        }
    }

    // Output permutation (1-based)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}