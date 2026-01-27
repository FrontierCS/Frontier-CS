#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    static uint64_t splitmix64(uint64_t x) {
        x += 0x9e3779b97f4a7c15ULL;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    size_t operator()(uint64_t x) const {
        static const uint64_t FIXED_RANDOM =
            chrono::steady_clock::now().time_since_epoch().count();
        return (size_t)splitmix64(x + FIXED_RANDOM);
    }
};

struct Anchor { int i, j; };

static inline void alignSegmentGreedy(
    const string& a, const string& b,
    int a0, int b0, int L1, int L2,
    string& out,
    int lookahead = 6,
    int maxShift = 2
) {
    const char* A = a.data() + a0;
    const char* B = b.data() + b0;
    int p = 0, q = 0;
    while (p < L1 && q < L2) {
        char ca = A[p], cb = B[q];
        if (ca == cb) {
            out.push_back('M');
            ++p; ++q;
            continue;
        }

        int ins = INT_MAX, del = INT_MAX;

        int qlim = min(L2, q + lookahead + 1);
        for (int t = 1; t <= maxShift && q + t < qlim; ++t) {
            if (ca == B[q + t]) { ins = t; break; }
        }
        int plim = min(L1, p + lookahead + 1);
        for (int t = 1; t <= maxShift && p + t < plim; ++t) {
            if (A[p + t] == cb) { del = t; break; }
        }

        if (ins < del) {
            out.append((size_t)ins, 'I');
            q += ins;
            out.push_back('M');
            ++p; ++q;
        } else if (del < ins) {
            out.append((size_t)del, 'D');
            p += del;
            out.push_back('M');
            ++p; ++q;
        } else {
            out.push_back('M');
            ++p; ++q;
        }
    }
    if (p < L1) out.append((size_t)(L1 - p), 'D');
    if (q < L2) out.append((size_t)(L2 - q), 'I');
}

struct PairIJ { int i, j; };

template<int CAP>
struct PosList {
    uint8_t cnt;
    int p[CAP];
    PosList() : cnt(0) {}
};

static vector<Anchor> findAnchors(
    const string& s1, const string& s2,
    int K, int step,
    int totalPairsCap
) {
    int N = (int)s1.size(), M = (int)s2.size();
    if (N < K || M < K) return {};

    static uint8_t cmap[128];
    static bool inited = false;
    if (!inited) {
        memset(cmap, 0, sizeof(cmap));
        for (char c = '0'; c <= '9'; ++c) cmap[(int)c] = (uint8_t)(c - '0' + 1);
        for (char c = 'A'; c <= 'Z'; ++c) cmap[(int)c] = (uint8_t)(c - 'A' + 11);
        inited = true;
    }

    const uint64_t base = 911382323ULL;

    uint64_t powK = 1;
    for (int t = 0; t < K; ++t) powK *= base;

    unordered_map<uint64_t, PosList<4>, SplitMix64> mp;
    mp.reserve((size_t)N / (size_t)step + 1024);

    auto getv = [&](char c) -> uint64_t { return (uint64_t)cmap[(int)c]; };

    // hashes for s1
    uint64_t h = 0;
    for (int t = 0; t < K; ++t) h = h * base + getv(s1[t]);

    for (int p = 0; p <= N - K; ++p) {
        if ((p % step) == 0) {
            auto &pl = mp[h];
            if (pl.cnt < 4) pl.p[pl.cnt++] = p;
        }
        if (p + K < N) {
            uint64_t add = getv(s1[p + K]);
            uint64_t sub = (uint64_t)((unsigned __int128)getv(s1[p]) * powK);
            h = h * base + add - sub;
        }
    }

    vector<PairIJ> pairs;
    pairs.reserve(min(totalPairsCap, (int)((size_t)M / (size_t)step * 2 + 1024)));

    // hashes for s2 and create pairs
    h = 0;
    for (int t = 0; t < K; ++t) h = h * base + getv(s2[t]);

    bool capHit = false;
    for (int p = 0; p <= M - K && !capHit; ++p) {
        if ((p % step) == 0) {
            auto it = mp.find(h);
            if (it != mp.end()) {
                const auto &pl = it->second;
                for (int t = 0; t < (int)pl.cnt; ++t) {
                    pairs.push_back({pl.p[t], p});
                    if ((int)pairs.size() >= totalPairsCap) { capHit = true; break; }
                }
            }
        }
        if (p + K < M) {
            uint64_t add = getv(s2[p + K]);
            uint64_t sub = (uint64_t)((unsigned __int128)getv(s2[p]) * powK);
            h = h * base + add - sub;
        }
    }

    if (pairs.empty()) return {};

    sort(pairs.begin(), pairs.end(), [](const PairIJ& a, const PairIJ& b) {
        if (a.i != b.i) return a.i < b.i;
        return a.j > b.j; // tie-break for LIS strictness
    });

    int P = (int)pairs.size();
    vector<int> prev(P, -1);
    vector<int> tailJ;
    vector<int> tailIdx;
    tailJ.reserve(1024);
    tailIdx.reserve(1024);

    for (int idx = 0; idx < P; ++idx) {
        int j = pairs[idx].j;
        auto it = lower_bound(tailJ.begin(), tailJ.end(), j);
        int pos = (int)(it - tailJ.begin());
        if (pos == (int)tailJ.size()) {
            tailJ.push_back(j);
            tailIdx.push_back(idx);
        } else {
            tailJ[pos] = j;
            tailIdx[pos] = idx;
        }
        if (pos > 0) prev[idx] = tailIdx[pos - 1];
    }

    vector<Anchor> chain;
    int cur = tailIdx.empty() ? -1 : tailIdx.back();
    while (cur != -1) {
        chain.push_back({pairs[cur].i, pairs[cur].j});
        cur = prev[cur];
    }
    reverse(chain.begin(), chain.end());

    // verify and enforce non-overlap
    vector<Anchor> res;
    res.reserve(chain.size());
    int ci = 0, cj = 0;
    for (auto &a : chain) {
        if (a.i < ci || a.j < cj) continue;
        if (a.i + K > N || a.j + K > M) continue;
        bool ok = true;
        for (int t = 0; t < K; ++t) {
            if (s1[a.i + t] != s2[a.j + t]) { ok = false; break; }
        }
        if (!ok) continue;
        res.push_back(a);
        ci = a.i + K;
        cj = a.j + K;
    }

    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) return 0;

    const int N = (int)s1.size();
    const int M = (int)s2.size();

    vector<Anchor> bestAnchors;
    int bestK = 0;
    long long bestCoverage = 0;

    const int step = 256;

    auto tryK = [&](int K, int capPairs) {
        auto anchors = findAnchors(s1, s2, K, step, capPairs);
        long long coverage = (long long)anchors.size() * (long long)K;
        if (coverage > bestCoverage || (coverage == bestCoverage && K > bestK)) {
            bestCoverage = coverage;
            bestAnchors = std::move(anchors);
            bestK = K;
        }
    };

    tryK(64, 400000);
    if (bestCoverage < 8192) tryK(32, 400000);
    if (bestCoverage == 0) tryK(16, 300000);

    string out;
    out.reserve((size_t)N + (size_t)M);

    if (bestK == 0 || bestAnchors.empty()) {
        alignSegmentGreedy(s1, s2, 0, 0, N, M, out);
    } else {
        int i = 0, j = 0;
        for (const auto &a : bestAnchors) {
            int L1 = a.i - i;
            int L2 = a.j - j;
            if (L1 < 0 || L2 < 0) continue;
            alignSegmentGreedy(s1, s2, i, j, L1, L2, out);
            out.append((size_t)bestK, 'M');
            i = a.i + bestK;
            j = a.j + bestK;
        }
        if (i < N || j < M) {
            alignSegmentGreedy(s1, s2, i, j, N - i, M - j, out);
        }
    }

    cout.write(out.data(), (streamsize)out.size());
    cout.put('\n');
    return 0;
}