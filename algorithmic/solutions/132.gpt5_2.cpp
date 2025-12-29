#include <bits/stdc++.h>
using namespace std;

static uint64_t splitmix64_state;

static inline uint64_t splitmix64() {
    uint64_t z = (splitmix64_state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    const int N = 1000;
    int mbits = min(R, 64);

    // Seed RNG
    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    splitmix64_state = seed ^ 0x123456789abcdef0ULL;

    vector<uint64_t> code(N + 1);
    vector<pair<uint64_t, uint64_t>> arr; // (OR value, (i<<10)|j)
    const int M = N * (N + 1) / 2;

    uint64_t mask = (mbits == 64) ? ~0ULL : ((1ULL << mbits) - 1);

    auto build_unique = [&]() -> bool {
        for (int i = 1; i <= N; ++i) {
            // random 64-bit masked to mbits
            uint64_t x = splitmix64() & mask;
            // Ensure non-zero to avoid empty rows too often (not necessary but helps)
            if (x == 0) x = 1ULL << (i % mbits);
            code[i] = x;
        }
        // Ensure each bit appears at least once
        vector<int> cnt(mbits, 0);
        for (int i = 1; i <= N; ++i) {
            uint64_t x = code[i];
            for (int b = 0; b < mbits; ++b) if ((x >> b) & 1ULL) cnt[b]++;
        }
        for (int b = 0; b < mbits; ++b) {
            if (cnt[b] == 0) {
                int i = (b % N) + 1;
                if (((code[i] >> b) & 1ULL) == 0) code[i] |= (1ULL << b);
            }
        }

        arr.clear();
        arr.reserve(M);
        for (int i = 1; i <= N; ++i) {
            uint64_t ci = code[i];
            for (int j = i; j <= N; ++j) {
                uint64_t key = ci | code[j];
                uint64_t val = (uint64_t(i) << 10) | uint64_t(j);
                arr.emplace_back(key, val);
            }
        }
        sort(arr.begin(), arr.end(), [](const auto &a, const auto &b){
            return a.first < b.first;
        });
        for (size_t k = 1; k < arr.size(); ++k) {
            if (arr[k].first == arr[k-1].first && arr[k].second != arr[k-1].second) {
                return false; // collision detected
            }
        }
        return true;
    };

    // Try a few times (though collision is astronomically unlikely)
    for (int tries = 0; tries < 5; ++tries) {
        if (build_unique()) break;
        if (tries == 4) {
            // As a fallback, reduce mbits and try again (should not happen)
            mbits = min(mbits, 60);
        }
    }

    // Send queries: one robot per bit position
    for (int b = 0; b < mbits; ++b) {
        vector<int> P;
        P.reserve(N/2);
        for (int i = 1; i <= N; ++i) {
            if ((code[i] >> b) & 1ULL) P.push_back(i);
        }
        cout << "? " << P.size();
        for (int v : P) cout << " " << v;
        cout << "\n";
        cout.flush();
    }

    // Get results
    cout << "@\n";
    cout.flush();

    int L;
    if (!(cin >> L)) return 0;
    vector<int> ans(L);
    for (int i = 0; i < L; ++i) cin >> ans[i];

    // Build result mask
    uint64_t res = 0;
    for (int i = 0; i < min(L, mbits); ++i) {
        if (ans[i]) res |= (1ULL << i);
    }

    // Decode using binary search on arr
    auto it = lower_bound(arr.begin(), arr.end(), res, [](const pair<uint64_t,uint64_t>& a, const uint64_t& val){
        return a.first < val;
    });

    int a = 1, b = 1;
    if (it != arr.end() && it->first == res) {
        uint64_t val = it->second;
        a = int(val >> 10);
        b = int(val & 1023ULL);
    }

    cout << "! " << a << " " << b << "\n";
    cout.flush();
    return 0;
}