#include <bits/stdc++.h>
using namespace std;

static const int MAX_QUERIES_LIMIT = 4269;

mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

struct PairHash {
    size_t operator()(const uint64_t &x) const noexcept {
        return std::hash<uint64_t>()(x);
    }
};

int n;
unordered_map<uint64_t, int, PairHash> cache_or;

inline uint64_t make_key(int a, int b) {
    if (a > b) swap(a, b);
    // n <= 2048, so 12 bits per index is safe
    return (uint64_t(a) << 12) | uint64_t(b);
}

int ask_or(int i, int j) {
    if (i == j) return -1; // Should not happen
    uint64_t key = make_key(i, j);
    auto it = cache_or.find(key);
    if (it != cache_or.end()) return it->second;
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    cache_or[key] = x;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    // Determine bit width
    int B = 0;
    while ((1 << B) < n) B++;
    int fullMask = (1 << B) - 1;

    // Sampling parameters
    // Keep sampling overhead modest to stay within total query limit
    int M = min(12, B + 1);        // number of random partners per sampled index
    int S = min(n, 9);             // number of sampled indices

    // Prepare shuffled indices for sampling
    vector<int> indices(n);
    iota(indices.begin(), indices.end(), 1);
    shuffle(indices.begin(), indices.end(), rng);

    vector<int> sampleIdx;
    vector<int> sampleA; // approximate p_r via AND of ORs
    vector<int> samplePop;

    for (int t = 0; t < S; ++t) {
        int r = indices[t];
        int A = fullMask;
        for (int m = 0; m < M; ++m) {
            int j = uniform_int_distribution<int>(1, n)(rng);
            if (j == r) {
                // ensure j != r
                j = (j % n) + 1;
                if (j == r) j = (j % n) + 1;
            }
            int val = ask_or(r, j);
            A &= val;
        }
        sampleIdx.push_back(r);
        sampleA.push_back(A);
        samplePop.push_back(__builtin_popcount((unsigned)A));
    }

    // Choose r1: minimal popcount(A)
    int r1 = sampleIdx[0];
    int bestPop = samplePop[0];
    int bestA = sampleA[0];
    for (int i = 1; i < (int)sampleIdx.size(); ++i) {
        if (samplePop[i] < bestPop || (samplePop[i] == bestPop && sampleA[i] < bestA)) {
            r1 = sampleIdx[i];
            bestPop = samplePop[i];
            bestA = sampleA[i];
        }
    }

    // Full pass with r1
    vector<int> q1(n + 1, -1);
    int min1 = INT_MAX;
    vector<int> cand;
    cand.reserve(n);
    for (int i = 1; i <= n; ++i) {
        if (i == r1) continue;
        int val = ask_or(i, r1);
        q1[i] = val;
        if (val < min1) {
            min1 = val;
            cand.clear();
            cand.push_back(i);
        } else if (val == min1) {
            cand.push_back(i);
        }
    }

    vector<int> ans(n + 1, -1);
    ans[r1] = min1; // p[r1] found
    int maskSoFar = min1;

    // Prepare a pool of candidate r's for further elimination:
    // sort sample indices (excluding r1) by popcount(maskSoFar & sampleA)
    vector<int> sampleOrder;
    for (int idx : sampleIdx) if (idx != r1) sampleOrder.push_back(idx);

    auto scoreFunc = [&](int idx) {
        int Ar = fullMask;
        // find approximate A for idx in sample
        for (int i = 0; i < (int)sampleIdx.size(); ++i) {
            if (sampleIdx[i] == idx) {
                Ar = sampleA[i];
                break;
            }
        }
        return __builtin_popcount((unsigned)(maskSoFar & Ar));
    };

    sort(sampleOrder.begin(), sampleOrder.end(), [&](int a, int b) {
        int sa = scoreFunc(a);
        int sb = scoreFunc(b);
        if (sa != sb) return sa < sb;
        return a < b;
    });

    vector<char> usedAsR(n + 1, 0);
    usedAsR[r1] = 1;

    // elimination loop
    int ptrSample = 0;
    while ((int)cand.size() > 1) {
        int r = -1;
        // pick next r from sampleOrder if available and unused
        while (ptrSample < (int)sampleOrder.size() && usedAsR[sampleOrder[ptrSample]]) ptrSample++;
        if (ptrSample < (int)sampleOrder.size()) {
            r = sampleOrder[ptrSample++];
        } else {
            // if no more pre-sampled indices, pick a random unused index
            // ensure we don't loop infinitely
            for (int tries = 0; tries < 100; ++tries) {
                int rr = uniform_int_distribution<int>(1, n)(rng);
                if (!usedAsR[rr]) { r = rr; break; }
            }
            if (r == -1) {
                // fallback: linear search for unused
                for (int i = 1; i <= n; ++i) if (!usedAsR[i]) { r = i; break; }
            }
            if (r == -1) {
                // all used, pick any (shouldn't happen)
                r = 1;
            }
        }
        usedAsR[r] = 1;

        int minv = INT_MAX;
        for (int c : cand) {
            int val = ask_or(c, r);
            if (val < minv) minv = val;
        }
        ans[r] = minv;
        maskSoFar &= minv;

        vector<int> newCand;
        newCand.reserve(cand.size());
        for (int c : cand) {
            int val = ask_or(c, r);
            if (val == minv) newCand.push_back(c);
        }
        cand.swap(newCand);

        // Re-sort remaining sampleOrder based on updated maskSoFar to speed reduction
        if (ptrSample < (int)sampleOrder.size()) {
            sort(sampleOrder.begin() + ptrSample, sampleOrder.end(), [&](int a, int b) {
                int sa = scoreFunc(a);
                int sb = scoreFunc(b);
                if (sa != sb) return sa < sb;
                return a < b;
            });
        }
    }

    int z = cand[0];
    ans[z] = 0;

    // Final retrieval: for unknown ans[i], query with z
    for (int i = 1; i <= n; ++i) {
        if (i == z) continue;
        if (ans[i] == -1) {
            int v = ask_or(i, z);
            ans[i] = v;
        }
    }

    // Output final permutation
    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << ans[i] << (i == n ? '\n' : ' ');
    }
    cout.flush();

    return 0;
}