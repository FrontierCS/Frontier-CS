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
    bool readInt(T &out) {
        char c; T sign = 1; T x = 0;
        c = getChar();
        if (!c) return false;
        while (c!='-' && (c<'0' || c>'9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c>='0' && c<='9'; c = getChar()) x = x*10 + (c - '0');
        out = x * sign;
        return true;
    }
};

static inline uint64_t splitmix64(uint64_t& x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

struct Key {
    uint64_t a, b, c, d;
};
static inline bool operator<(const Key& x, const Key& y) {
    if (x.a != y.a) return x.a < y.a;
    if (x.b != y.b) return x.b < y.b;
    if (x.c != y.c) return x.c < y.c;
    return x.d < y.d;
}
static inline bool operator==(const Key& x, const Key& y) {
    return x.a==y.a && x.b==y.b && x.c==y.c && x.d==y.d;
}

struct NodeKey {
    Key k;
    int gid; // 0 for G1, 1 for G2
    int idx;
};

struct Feature {
    int deg;
    uint64_t s1, s2, sx;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);
    int blocks = (n + 63) >> 6;

    vector<vector<int>> g1(n), g2(n);
    vector<uint64_t> adj1Bits((size_t)n * blocks, 0ULL);
    auto setEdge1 = [&](int u, int v) {
        adj1Bits[(size_t)u * blocks + (v >> 6)] |= (1ULL << (v & 63));
    };
    auto isEdge1 = [&](int u, int v) -> int {
        return (int)((adj1Bits[(size_t)u * blocks + (v >> 6)] >> (v & 63)) & 1ULL);
    };

    // Read G1
    for (int i = 0; i < m; ++i) {
        int u, v; fs.readInt(u); fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        g1[u].push_back(v);
        g1[v].push_back(u);
        setEdge1(u, v);
        setEdge1(v, u);
    }
    // Read G2
    vector<pair<int,int>> edges2;
    edges2.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v; fs.readInt(u); fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        g2[u].push_back(v);
        g2[v].push_back(u);
        if (u < v) edges2.emplace_back(u, v);
        else edges2.emplace_back(v, u);
    }

    vector<int> deg1(n), deg2(n);
    for (int i = 0; i < n; ++i) {
        deg1[i] = (int)g1[i].size();
        deg2[i] = (int)g2[i].size();
    }

    // WL color refinement (combined across both graphs)
    vector<int> col1(n), col2(n);
    for (int i = 0; i < n; ++i) col1[i] = deg1[i];
    for (int i = 0; i < n; ++i) col2[i] = deg2[i];

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    vector<uint64_t> rnd1(1), rnd2(1), rnd3(1);
    auto ensureRandSize = [&](int sz) {
        if (sz < 1) sz = 1;
        while ((int)rnd1.size() <= sz) rnd1.push_back(splitmix64(seed));
        while ((int)rnd2.size() <= sz) rnd2.push_back(splitmix64(seed));
        while ((int)rnd3.size() <= sz) rnd3.push_back(splitmix64(seed));
    };

    auto WL_iterate = [&](vector<int>& c1, vector<int>& c2, int iterations) {
        vector<int> nc1(n), nc2(n);
        bool changed = false;
        for (int it = 0; it < iterations; ++it) {
            int maxCol = 0;
            for (int i = 0; i < n; ++i) if (c1[i] > maxCol) maxCol = c1[i];
            for (int i = 0; i < n; ++i) if (c2[i] > maxCol) maxCol = c2[i];
            ensureRandSize(maxCol + 5);

            vector<NodeKey> all;
            all.reserve(2*n);

            // G1
            for (int v = 0; v < n; ++v) {
                uint64_t s1=0, s2=0, sx=0;
                for (int u : g1[v]) {
                    int cc = c1[u];
                    s1 += rnd1[cc];
                    s2 += rnd2[cc];
                    sx ^= rnd3[cc];
                }
                NodeKey nk;
                nk.k.a = ( (uint64_t)c1[v] << 32 ) ^ (uint64_t)deg1[v];
                nk.k.b = s1;
                nk.k.c = s2;
                nk.k.d = sx;
                nk.gid = 0;
                nk.idx = v;
                all.push_back(nk);
            }
            // G2
            for (int v = 0; v < n; ++v) {
                uint64_t s1=0, s2=0, sx=0;
                for (int u : g2[v]) {
                    int cc = c2[u];
                    s1 += rnd1[cc];
                    s2 += rnd2[cc];
                    sx ^= rnd3[cc];
                }
                NodeKey nk;
                nk.k.a = ( (uint64_t)c2[v] << 32 ) ^ (uint64_t)deg2[v];
                nk.k.b = s1;
                nk.k.c = s2;
                nk.k.d = sx;
                nk.gid = 1;
                nk.idx = v;
                all.push_back(nk);
            }

            sort(all.begin(), all.end(), [](const NodeKey& x, const NodeKey& y){
                return x.k < y.k;
            });

            int curColor = 0;
            auto equalKey = [](const Key& x, const Key& y) {
                return x.a==y.a && x.b==y.b && x.c==y.c && x.d==y.d;
            };
            // Assign new colors
            for (size_t i = 0; i < all.size(); ++i) {
                if (i == 0) {
                    if (all[i].gid == 0) nc1[all[i].idx] = curColor;
                    else nc2[all[i].idx] = curColor;
                } else {
                    if (!equalKey(all[i].k, all[i-1].k)) ++curColor;
                    if (all[i].gid == 0) nc1[all[i].idx] = curColor;
                    else nc2[all[i].idx] = curColor;
                }
            }

            changed = false;
            for (int i = 0; i < n; ++i) if (nc1[i] != c1[i]) { changed = true; break; }
            if (!changed) {
                for (int i = 0; i < n; ++i) if (nc2[i] != c2[i]) { changed = true; break; }
            }
            c1.swap(nc1);
            c2.swap(nc2);
            if (!changed) break;
        }
    };

    WL_iterate(col1, col2, 4);

    // Compute features based on final colors for sorting within color classes
    int maxColor = 0;
    for (int i = 0; i < n; ++i) if (col1[i] > maxColor) maxColor = col1[i];
    for (int i = 0; i < n; ++i) if (col2[i] > maxColor) maxColor = col2[i];
    ensureRandSize(maxColor + 5);

    vector<Feature> feat1(n), feat2(n);
    for (int v = 0; v < n; ++v) {
        uint64_t s1=0, s2=0, sx=0;
        for (int u : g1[v]) {
            int cc = col1[u];
            s1 += rnd1[cc];
            s2 += rnd2[cc];
            sx ^= rnd3[cc];
        }
        feat1[v] = {deg1[v], s1, s2, sx};
    }
    for (int v = 0; v < n; ++v) {
        uint64_t s1=0, s2=0, sx=0;
        for (int u : g2[v]) {
            int cc = col2[u];
            s1 += rnd1[cc];
            s2 += rnd2[cc];
            sx ^= rnd3[cc];
        }
        feat2[v] = {deg2[v], s1, s2, sx};
    }

    vector<vector<int>> cls1(maxColor + 1), cls2(maxColor + 1);
    for (int i = 0; i < n; ++i) cls1[col1[i]].push_back(i);
    for (int i = 0; i < n; ++i) cls2[col2[i]].push_back(i);

    auto cmpFeat1 = [&](int a, int b) {
        const Feature &x = feat1[a], &y = feat1[b];
        if (x.deg != y.deg) return x.deg < y.deg;
        if (x.s1 != y.s1) return x.s1 < y.s1;
        if (x.s2 != y.s2) return x.s2 < y.s2;
        return x.sx < y.sx;
    };
    auto cmpFeat2 = [&](int a, int b) {
        const Feature &x = feat2[a], &y = feat2[b];
        if (x.deg != y.deg) return x.deg < y.deg;
        if (x.s1 != y.s1) return x.s1 < y.s1;
        if (x.s2 != y.s2) return x.s2 < y.s2;
        return x.sx < y.sx;
    };

    vector<int> p(n, -1);
    vector<char> used1(n, 0);
    vector<int> leftover1, leftover2;
    leftover1.reserve(n);
    leftover2.reserve(n);

    for (int c = 0; c <= maxColor; ++c) {
        auto &L1 = cls1[c];
        auto &L2 = cls2[c];
        if (L1.empty() && L2.empty()) continue;
        sort(L1.begin(), L1.end(), cmpFeat1);
        sort(L2.begin(), L2.end(), cmpFeat2);
        int k = min((int)L1.size(), (int)L2.size());
        for (int i = 0; i < k; ++i) {
            p[L2[i]] = L1[i];
            used1[L1[i]] = 1;
        }
        for (int i = k; i < (int)L1.size(); ++i) leftover1.push_back(L1[i]);
        for (int i = k; i < (int)L2.size(); ++i) leftover2.push_back(L2[i]);
    }

    // Sort leftovers and match
    sort(leftover1.begin(), leftover1.end(), cmpFeat1);
    sort(leftover2.begin(), leftover2.end(), cmpFeat2);
    for (size_t i = 0; i < leftover1.size() && i < leftover2.size(); ++i) {
        p[leftover2[i]] = leftover1[i];
        used1[leftover1[i]] = 1;
    }
    // If still unmatched (due to possible rounding), assign arbitrary remaining
    if ((int)leftover2.size() > (int)leftover1.size()) {
        // Collect unused in G1
        vector<int> free1;
        free1.reserve(n);
        for (int i = 0; i < n; ++i) if (!used1[i]) free1.push_back(i);
        size_t j = 0;
        for (size_t i = leftover1.size(); i < leftover2.size(); ++i) {
            if (j >= free1.size()) break;
            p[leftover2[i]] = free1[j++];
        }
    }

    // Ensure all mapped; if any -1 remain, map to any unused
    {
        vector<int> free1;
        for (int i = 0; i < n; ++i) if (!used1[i]) free1.push_back(i);
        size_t j = 0;
        for (int i = 0; i < n; ++i) if (p[i] == -1) {
            if (j < free1.size()) p[i] = free1[j++]; 
        }
    }

    // Ensure permutation correctness: if duplicates occurred, fix by greedy
    {
        vector<int> inv(n, -1);
        vector<int> dup;
        vector<char> seen1(n, 0);
        for (int i = 0; i < n; ++i) {
            if (!seen1[p[i]]) {
                seen1[p[i]] = 1;
                inv[p[i]] = i;
            } else {
                dup.push_back(i);
            }
        }
        if (!dup.empty()) {
            vector<int> free1;
            for (int j = 0; j < n; ++j) if (inv[j] == -1) free1.push_back(j);
            int idx = 0;
            for (int u : dup) {
                if (idx < (int)free1.size()) p[u] = free1[idx++];
            }
        }
    }

    // Compute initial matched edges and s[u]
    long long matched = 0;
    for (auto &e : edges2) {
        int u = e.first, v = e.second;
        int pu = p[u], pv = p[v];
        matched += isEdge1(pu, pv);
    }
    vector<int> s(n, 0);
    for (int u = 0; u < n; ++u) {
        int pu = p[u];
        int cnt = 0;
        for (int v : g2[u]) cnt += isEdge1(pu, p[v]);
        s[u] = cnt;
    }

    // Prepare color classes for G2 for sampling
    vector<vector<int>> cls2_indices(maxColor + 1);
    for (int i = 0; i < n; ++i) cls2_indices[col2[i]].push_back(i);

    // Local improvement by random 2-swaps
    auto compute_delta = [&](int a, int b) -> int {
        if (a == b) return 0;
        int Pa = p[a], Pb = p[b];
        int delta = 0;
        // For neighbors of a
        for (int x : g2[a]) {
            if (x == b) continue;
            int Px = p[x];
            delta += isEdge1(Pb, Px) - isEdge1(Pa, Px);
        }
        // For neighbors of b
        for (int x : g2[b]) {
            if (x == a) continue;
            int Px = p[x];
            delta += isEdge1(Pa, Px) - isEdge1(Pb, Px);
        }
        return delta;
    };
    auto apply_swap_update = [&](int a, int b, int delta) {
        int Pa = p[a], Pb = p[b];
        // Update s for a and its neighbors
        for (int x : g2[a]) {
            if (x == b) continue;
            int Px = p[x];
            int oldv = isEdge1(Pa, Px);
            int newv = isEdge1(Pb, Px);
            int diff = newv - oldv;
            if (diff) {
                s[a] += diff;
                s[x] += diff;
            }
        }
        // Update s for b and its neighbors
        for (int x : g2[b]) {
            if (x == a) continue;
            int Px = p[x];
            int oldv = isEdge1(Pb, Px);
            int newv = isEdge1(Pa, Px);
            int diff = newv - oldv;
            if (diff) {
                s[b] += diff;
                s[x] += diff;
            }
        }
        // Swap mapping
        swap(p[a], p[b]);
        matched += delta;
    };

    // Timing and parameters
    auto t_start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT_SEC = 0.9; // adjustable small budget
    std::mt19937_64 rng(seed ^ 0x9e3779b97f4a7c15ULL);
    uniform_int_distribution<int> distN(0, n-1);

    int MAX_ITERS = 20000;
    int KpickA = 8;  // worst-of-K to pick a
    int KcandB = 24; // candidates for b per a

    for (int iter = 0; iter < MAX_ITERS; ++iter) {
        auto t_now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(t_now - t_start).count();
        if (elapsed > TIME_LIMIT_SEC) break;

        // Pick "a" as worst-of-KpickA
        int bestA = -1;
        int bestLack = -1;
        for (int k = 0; k < KpickA; ++k) {
            int u = distN(rng);
            int lack = deg2[u] - s[u];
            if (lack > bestLack) {
                bestLack = lack;
                bestA = u;
            }
        }
        int a = bestA;
        if (a < 0) a = distN(rng);

        // Prepare candidate b's
        vector<int> candB;
        candB.reserve(KcandB);
        unordered_set<int> seen;
        seen.reserve(KcandB*2+3);
        seen.insert(a);
        int ca = col2[a];
        auto &classA = cls2_indices[ca];

        for (int k = 0; k < KcandB; ++k) {
            int b;
            if ((rng() & 3ULL) != 0ULL && !classA.empty()) {
                // Prefer same color
                int idx = (int)(rng() % classA.size());
                b = classA[idx];
            } else {
                b = distN(rng);
            }
            if (seen.insert(b).second) candB.push_back(b);
        }

        int bestB = -1;
        int bestDelta = 0;
        for (int b : candB) {
            if (b == a) continue;
            int delta = compute_delta(a, b);
            if (delta > bestDelta) {
                bestDelta = delta;
                bestB = b;
            }
        }
        if (bestB != -1 && bestDelta > 0) {
            apply_swap_update(a, bestB, bestDelta);
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