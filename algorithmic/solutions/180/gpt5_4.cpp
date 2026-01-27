#include <bits/stdc++.h>
using namespace std;

struct BitMatrix {
    int n, W;
    vector<uint64_t> data;
    BitMatrix() : n(0), W(0) {}
    BitMatrix(int n_, int W_) : n(n_), W(W_), data((size_t)n_ * W_, 0) {}
    inline uint64_t* row(int i) { return data.data() + (size_t)i * W; }
    inline const uint64_t* row(int i) const { return data.data() + (size_t)i * W; }
    inline void set(int i, int j) { data[(size_t)i*W + (j>>6)] |= (1ULL << (j & 63)); }
    inline bool get(int i, int j) const { return (data[(size_t)i*W + (j>>6)] >> (j & 63)) & 1ULL; }
    inline void toggle(int i, int j) { data[(size_t)i*W + (j>>6)] ^= (1ULL << (j & 63)); }
};

static inline int popcount_and(const uint64_t* a, const uint64_t* b, int W) {
    int s = 0;
    for (int i = 0; i < W; ++i) s += __builtin_popcountll(a[i] & b[i]);
    return s;
}

static inline uint64_t splitmix64(uint64_t z) {
    z += 0x9e3779b97f4a7c15ULL;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

struct Key {
    uint64_t a, b, c;
    bool operator==(Key const& o) const { return a==o.a && b==o.b && c==o.c; }
};
struct KeyHasher {
    size_t operator()(Key const& k) const {
        uint64_t h = k.a;
        h ^= splitmix64(k.b + 0x9e3779b97f4a7c15ULL);
        h ^= splitmix64(k.c + 0x243f6a8885a308d3ULL);
        return (size_t)h;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    int W = (n + 63) >> 6;

    vector<vector<int>> adj1(n), adj2(n);
    BitMatrix bits1(n, W), bits2(n, W);
    vector<int> deg1(n, 0), deg2(n, 0);

    for (long long i = 0; i < m; ++i) {
        int u,v; cin >> u >> v; --u; --v;
        if (u==v) continue;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
        bits1.set(u, v);
        bits1.set(v, u);
        deg1[u]++; deg1[v]++;
    }
    for (long long i = 0; i < m; ++i) {
        int u,v; cin >> u >> v; --u; --v;
        if (u==v) continue;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        bits2.set(u, v);
        bits2.set(v, u);
        deg2[u]++; deg2[v]++;
    }

    // WL color refinement with hashed multisets (order-invariant)
    int iterations = 5;
    vector<int> color1(n), color2(n);
    for (int i = 0; i < n; ++i) { color1[i] = deg1[i]; color2[i] = deg2[i]; }
    for (int it = 0; it < iterations; ++it) {
        vector<Key> keys(2*n);
        for (int u = 0; u < n; ++u) {
            uint64_t h0 = (uint64_t)color1[u] * 0x9e3779b185ebca87ULL + (uint64_t)deg1[u];
            uint64_t s1 = 0, s2 = 0, s3 = 0;
            for (int v : adj1[u]) {
                uint64_t hv = splitmix64((uint64_t)color1[v] * 0x2545F4914F6CDD1DULL + 0x517cc1b727220a95ULL);
                uint64_t hv2 = splitmix64((uint64_t)color1[v] * 0x9e3779b97f4a7c15ULL + 0x94d049bb133111ebULL);
                s1 += hv;
                s2 += hv2;
                s3 ^= (hv ^ (hv2 << 1));
            }
            keys[u] = Key{h0, s1, s2 ^ s3};
        }
        for (int u = 0; u < n; ++u) {
            uint64_t h0 = (uint64_t)color2[u] * 0x9e3779b185ebca87ULL + (uint64_t)deg2[u];
            uint64_t s1 = 0, s2 = 0, s3 = 0;
            for (int v : adj2[u]) {
                uint64_t hv = splitmix64((uint64_t)color2[v] * 0x2545F4914F6CDD1DULL + 0x517cc1b727220a95ULL);
                uint64_t hv2 = splitmix64((uint64_t)color2[v] * 0x9e3779b97f4a7c15ULL + 0x94d049bb133111ebULL);
                s1 += hv;
                s2 += hv2;
                s3 ^= (hv ^ (hv2 << 1));
            }
            keys[n + u] = Key{h0, s1, s2 ^ s3};
        }
        unordered_map<Key,int,KeyHasher> mp;
        mp.reserve((size_t)2*n*2);
        int nxt = 0;
        vector<int> newC1(n), newC2(n);
        for (int i = 0; i < n; ++i) {
            auto itf = mp.find(keys[i]);
            if (itf == mp.end()) { mp.emplace(keys[i], nxt); newC1[i] = nxt++; }
            else newC1[i] = itf->second;
        }
        for (int i = 0; i < n; ++i) {
            auto itf = mp.find(keys[n+i]);
            if (itf == mp.end()) { mp.emplace(keys[n+i], nxt); newC2[i] = nxt++; }
            else newC2[i] = itf->second;
        }
        bool same = (newC1 == color1) && (newC2 == color2);
        color1.swap(newC1);
        color2.swap(newC2);
        if (same) break;
    }

    // Features for ordering within color classes
    vector<long long> sdeg1(n, 0), sdeg2(n, 0);
    vector<uint64_t> whash1(n, 0), whash2(n, 0);
    for (int u = 0; u < n; ++u) {
        long long s=0; uint64_t w=0;
        for (int v: adj1[u]) { s += deg1[v]; w += splitmix64((uint64_t)color1[v] + 0x9e3779b97f4a7c15ULL); }
        sdeg1[u]=s; whash1[u]=w;
    }
    for (int u = 0; u < n; ++u) {
        long long s=0; uint64_t w=0;
        for (int v: adj2[u]) { s += deg2[v]; w += splitmix64((uint64_t)color2[v] + 0x9e3779b97f4a7c15ULL); }
        sdeg2[u]=s; whash2[u]=w;
    }

    int maxColor = 0;
    for (int i = 0; i < n; ++i) { if (color1[i] > maxColor) maxColor = color1[i]; if (color2[i] > maxColor) maxColor = color2[i]; }
    vector<vector<int>> group1(maxColor+1), group2(maxColor+1);
    for (int i = 0; i < n; ++i) group1[color1[i]].push_back(i);
    for (int i = 0; i < n; ++i) group2[color2[i]].push_back(i);

    auto cmp1 = [&](int a, int b){
        if (deg1[a] != deg1[b]) return deg1[a] > deg1[b];
        if (sdeg1[a] != sdeg1[b]) return sdeg1[a] > sdeg1[b];
        if (whash1[a] != whash1[b]) return whash1[a] > whash1[b];
        return a < b;
    };
    auto cmp2 = [&](int a, int b){
        if (deg2[a] != deg2[b]) return deg2[a] > deg2[b];
        if (sdeg2[a] != sdeg2[b]) return sdeg2[a] > sdeg2[b];
        if (whash2[a] != whash2[b]) return whash2[a] > whash2[b];
        return a < b;
    };

    vector<int> p(n, -1);
    vector<char> used1(n, 0);
    vector<int> rem2;
    for (int c = 0; c <= maxColor; ++c) {
        auto &A = group1[c], &B = group2[c];
        if (A.empty() && B.empty()) continue;
        sort(A.begin(), A.end(), cmp1);
        sort(B.begin(), B.end(), cmp2);
        int k = min(A.size(), B.size());
        for (int i = 0; i < k; ++i) {
            p[B[i]] = A[i];
            used1[A[i]] = 1;
        }
        for (int i = k; i < (int)B.size(); ++i) rem2.push_back(B[i]);
    }
    vector<int> rem1;
    for (int i = 0; i < n; ++i) if (!used1[i]) rem1.push_back(i);
    sort(rem1.begin(), rem1.end(), cmp1);
    sort(rem2.begin(), rem2.end(), cmp2);
    for (size_t i = 0; i < rem2.size(); ++i) {
        p[rem2[i]] = rem1[i];
        used1[rem1[i]] = 1;
    }

    // Ensure permutation valid
    vector<int> inv(n, -1);
    for (int i = 0; i < n; ++i) inv[p[i]] = i;
    // Build bitsets of images of neighbors for G2
    BitMatrix imagesSet(n, W);
    for (int u = 0; u < n; ++u) {
        uint64_t* row = imagesSet.row(u);
        for (int v : adj2[u]) {
            int im = p[v];
            row[im>>6] |= (1ULL << (im & 63));
        }
    }

    // Initial scores and matched edges
    vector<int> score(n, 0);
    long long sumScore = 0;
    for (int u = 0; u < n; ++u) {
        score[u] = popcount_and(bits1.row(p[u]), imagesSet.row(u), W);
        sumScore += score[u];
    }
    long long matchedEdges = sumScore / 2;

    // Local improvement (swap-based hill-climbing)
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto randInt = [&](int l, int r)->int {
        uniform_int_distribution<int> dist(l, r);
        return (int)dist(rng);
    };

    vector<int> mis(n);
    for (int i = 0; i < n; ++i) mis[i] = deg2[i] - score[i];

    auto sort_order = [&](){
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b){
            if (mis[a] != mis[b]) return mis[a] > mis[b];
            return deg2[a] > deg2[b];
        });
        return order;
    };

    int maxPass = 3;
    for (int pass = 0; pass < maxPass; ++pass) {
        auto order = sort_order();
        int T = min(n, 250);
        vector<int> topList(order.begin(), order.begin()+T);
        bool improved = false;
        for (int idx = 0; idx < n; ++idx) {
            int u = order[idx];
            if (mis[u] <= 0) break;
            int a = p[u];
            int bestV = -1;
            long long bestDeltaEdges = 0;
            int candChecks = 0;

            // Candidates from neighbors of image a in G1
            int triesNbr = min((int)adj1[a].size(), 10);
            for (int t = 0; t < triesNbr; ++t) {
                int g = adj1[a][randInt(0, (int)adj1[a].size()-1)];
                int v = inv[g];
                if (v == u) continue;
                int b = p[v];
                const uint64_t* setU = imagesSet.row(u);
                const uint64_t* setV = imagesSet.row(v);
                int pop1 = popcount_and(bits1.row(b), setU, W);
                int pop2 = popcount_and(bits1.row(a), setV, W);
                int oldU = score[u];
                int oldV = score[v];
                bool e = bits2.get(u, v);
                bool Aab = bits1.get(a, b);
                long long deltaSum = (long long)(pop1 - oldU) + (long long)(pop2 - oldV) + (e ? (2LL * (Aab ? 1 : 0)) : 0LL);
                long long deltaEdges = deltaSum / 2;
                if (deltaEdges > bestDeltaEdges) {
                    bestDeltaEdges = deltaEdges;
                    bestV = v;
                }
                if (++candChecks >= 16) break;
            }
            // Candidates from top mis list
            int extraTries = 16 - candChecks;
            for (int t = 0; t < extraTries; ++t) {
                int v = topList[randInt(0, (int)topList.size()-1)];
                if (v == u) continue;
                int a2 = p[u], b = p[v];
                const uint64_t* setU = imagesSet.row(u);
                const uint64_t* setV = imagesSet.row(v);
                int pop1 = popcount_and(bits1.row(b), setU, W);
                int pop2 = popcount_and(bits1.row(a2), setV, W);
                int oldU = score[u];
                int oldV = score[v];
                bool e = bits2.get(u, v);
                bool Aab = bits1.get(a2, b);
                long long deltaSum = (long long)(pop1 - oldU) + (long long)(pop2 - oldV) + (e ? (2LL * (Aab ? 1 : 0)) : 0LL);
                long long deltaEdges = deltaSum / 2;
                if (deltaEdges > bestDeltaEdges) {
                    bestDeltaEdges = deltaEdges;
                    bestV = v;
                }
            }

            if (bestV != -1 && bestDeltaEdges > 0) {
                int v = bestV;
                int a0 = p[u];
                int b0 = p[v];
                bool e = bits2.get(u, v);
                bool Aab = bits1.get(a0, b0);
                const uint64_t* setU = imagesSet.row(u);
                const uint64_t* setV = imagesSet.row(v);
                int pop1 = popcount_and(bits1.row(b0), setU, W);
                int pop2 = popcount_and(bits1.row(a0), setV, W);
                int oldU = score[u];
                int oldV = score[v];
                int deltaU = (pop1 - oldU) + (e ? (Aab ? 1 : 0) : 0);
                int deltaV = (pop2 - oldV) + (e ? (Aab ? 1 : 0) : 0);
                // apply swap
                // update imagesSet for neighbors (toggle bits)
                for (int z : adj2[u]) {
                    imagesSet.toggle(z, a0);
                    imagesSet.toggle(z, b0);
                    if (z != u && z != v) {
                        int pz = p[z];
                        score[z] += (bits1.get(pz, b0) ? 1 : 0) - (bits1.get(pz, a0) ? 1 : 0);
                        mis[z] = deg2[z] - score[z];
                    }
                }
                for (int z : adj2[v]) {
                    imagesSet.toggle(z, b0);
                    imagesSet.toggle(z, a0);
                    if (z != u && z != v) {
                        int pz = p[z];
                        score[z] += (bits1.get(pz, a0) ? 1 : 0) - (bits1.get(pz, b0) ? 1 : 0);
                        mis[z] = deg2[z] - score[z];
                    }
                }
                // swap mapping
                p[u] = b0; p[v] = a0;
                inv[a0] = v; inv[b0] = u;

                score[u] += deltaU;
                score[v] += deltaV;
                mis[u] = deg2[u] - score[u];
                mis[v] = deg2[v] - score[v];

                matchedEdges += bestDeltaEdges;
                improved = true;
            }
        }
        if (!improved) break;
    }

    // Output mapping 1-based
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}