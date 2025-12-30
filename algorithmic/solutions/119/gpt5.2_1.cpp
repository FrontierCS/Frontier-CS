#include <bits/stdc++.h>
using namespace std;

static const long long MOD = 1000000007LL;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed) : x(seed) {}
    uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    SplitMix64 rng(seed);

    auto randVal = [&]() -> long long {
        // Returns value in [2, MOD-2]
        return 2 + (long long)(rng.next() % (uint64_t)(MOD - 3));
    };

    int queryCount = 0;
    auto ask = [&](const vector<long long>& a) -> long long {
        ++queryCount;
        cout << "?";
        for (int i = 0; i <= n; i++) {
            cout << ' ' << a[i];
        }
        cout << '\n';
        cout.flush();
        long long res;
        if (!(cin >> res)) exit(0);
        if (res < 0) exit(0);
        return res;
    };

    vector<int> ops(n + 1, -1); // 1..n, 0:+, 1:*
    const int B = 16;

    for (int l = 1; l <= n; l += B) {
        int r = min(n, l + B - 1);
        int k = r - l + 1;
        int SZ = 1 << k;

        // Fixed prefix operands for this block: a0..a_{l-1}
        vector<long long> prefixA(l);
        for (int i = 0; i < l; i++) prefixA[i] = randVal();

        // Compute start value s after applying known ops 1..l-1 on prefixA
        long long s = prefixA[0] % MOD;
        for (int i = 1; i < l; i++) {
            if (ops[i] == -1) {
                // Should not happen: all ops before l must be known
                // Fallback: treat as '+' (won't happen in correct flow)
                s = (s + prefixA[i]) % MOD;
            } else if (ops[i] == 0) {
                s = (s + prefixA[i]) % MOD;
            } else {
                s = (s * prefixA[i]) % MOD;
            }
        }

        vector<vector<long long>> blockVals; // per query, size k
        vector<long long> responses;

        auto makeQuery = [&]() {
            vector<long long> a(n + 1, 1);
            for (int i = 0; i < l; i++) a[i] = prefixA[i];
            vector<long long> bv(k);
            for (int j = 0; j < k; j++) {
                bv[j] = randVal();
                a[l + j] = bv[j];
            }
            // a[r+1..n] already 1
            long long res = ask(a);
            blockVals.push_back(std::move(bv));
            responses.push_back(res);
        };

        // Start with 3 queries
        makeQuery();
        makeQuery();
        makeQuery();

        // Precompute baseEnd for all masks with query0 blockVals[0]
        vector<long long> baseEnd(SZ);
        for (int mask = 0; mask < SZ; mask++) {
            long long v = s;
            for (int j = 0; j < k; j++) {
                if ((mask >> j) & 1) v = (v * blockVals[0][j]) % MOD;
                else v = (v + blockVals[0][j]) % MOD;
            }
            baseEnd[mask] = v;
        }

        vector<int> cand(SZ);
        iota(cand.begin(), cand.end(), 0);

        auto filterWithQuery = [&](int qIdx) {
            long long obs = (responses[qIdx] - responses[0]) % MOD;
            if (obs < 0) obs += MOD;

            vector<int> nc;
            nc.reserve(cand.size());
            for (int mask : cand) {
                long long v = s;
                for (int j = 0; j < k; j++) {
                    if ((mask >> j) & 1) v = (v * blockVals[qIdx][j]) % MOD;
                    else v = (v + blockVals[qIdx][j]) % MOD;
                }
                long long delta = (v - baseEnd[mask]) % MOD;
                if (delta < 0) delta += MOD;
                if (delta == obs) nc.push_back(mask);
            }
            cand.swap(nc);
        };

        filterWithQuery(1);
        if (cand.size() > 1) filterWithQuery(2);

        int extraTries = 0;
        while (cand.size() > 1) {
            if (queryCount >= 600) break;
            if (++extraTries > 20) break;
            makeQuery();
            filterWithQuery((int)responses.size() - 1);
        }

        if (cand.empty()) {
            // Extremely unlikely; fallback to single-bit brute via extra queries (should never be needed)
            // We'll assume not happening in valid runs.
            cand.push_back(0);
        }

        int chosen = cand[0];
        for (int j = 0; j < k; j++) ops[l + j] = (chosen >> j) & 1;
    }

    cout << "!";
    for (int i = 1; i <= n; i++) cout << ' ' << ops[i];
    cout << '\n';
    cout.flush();
    return 0;
}