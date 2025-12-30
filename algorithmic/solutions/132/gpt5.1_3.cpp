#include <bits/stdc++.h>
using namespace std;

struct Code {
    uint64_t lo, hi;
};

struct UnionEntry {
    uint64_t lo, hi;
    int a, b;
};

uint64_t rng_state = 123456789123456789ULL;

uint64_t rand64() {
    uint64_t z = (rng_state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) {
        return 0;
    }

    const int N = 1000;
    int T = min(R, 75); // use at most 75 robots

    vector<Code> codes(N + 1);
    size_t totalPairs = (size_t)N * (N + 1) / 2;
    vector<UnionEntry> unions;
    unions.resize(totalPairs);

    // Build a 2-separable code for N items with length T
    while (true) {
        // Generate codes
        for (int i = 1; i <= N; ++i) {
            uint64_t lo, hi;
            if (T <= 64) {
                uint64_t mask = (T == 64) ? ~0ULL : ((1ULL << T) - 1);
                lo = rand64() & mask;
                hi = 0;
            } else {
                int rem = T - 64;
                uint64_t hiMask = (rem == 64) ? ~0ULL : ((1ULL << rem) - 1);
                lo = rand64();
                hi = rand64() & hiMask;
            }
            if (lo == 0 && hi == 0) lo = 1; // avoid all-zero
            codes[i].lo = lo;
            codes[i].hi = hi;
        }

        // Build unions
        size_t idx = 0;
        for (int i = 1; i <= N; ++i) {
            uint64_t li = codes[i].lo, hi = codes[i].hi;
            for (int j = i; j <= N; ++j) {
                unions[idx].lo = li | codes[j].lo;
                unions[idx].hi = hi | codes[j].hi;
                unions[idx].a = i;
                unions[idx].b = j;
                ++idx;
            }
        }

        // Sort and check uniqueness
        sort(unions.begin(), unions.end(), [](const UnionEntry &x, const UnionEntry &y) {
            if (x.hi != y.hi) return x.hi < y.hi;
            return x.lo < y.lo;
        });

        bool ok = true;
        for (size_t i = 1; i < totalPairs; ++i) {
            if (unions[i].hi == unions[i - 1].hi && unions[i].lo == unions[i - 1].lo) {
                ok = false;
                break;
            }
        }
        if (ok) break;
    }

    // Build tests: for each bit position, list of positions to scout
    vector<vector<int>> tests(T);
    for (int p = 1; p <= N; ++p) {
        uint64_t lo = codes[p].lo, hi = codes[p].hi;
        int t = 0;
        for (; t < min(T, 64); ++t) {
            if ((lo >> t) & 1ULL) tests[t].push_back(p);
        }
        for (; t < T; ++t) {
            int k = t - 64;
            if ((hi >> k) & 1ULL) tests[t].push_back(p);
        }
    }

    // Send all robots
    int robotsSent = 0;
    for (int t = 0; t < T; ++t) {
        cout << "? " << (int)tests[t].size();
        for (int pos : tests[t]) cout << ' ' << pos;
        cout << '\n';
        cout.flush();
        ++robotsSent;
    }

    // Get all answers in a single hour
    cout << "@\n";
    cout.flush();

    int L;
    if (!(cin >> L)) {
        return 0;
    }
    vector<int> res(L);
    for (int i = 0; i < L; ++i) cin >> res[i];

    uint64_t ans_lo = 0, ans_hi = 0;
    for (int t = 0; t < L; ++t) {
        if (res[t]) {
            if (t < 64) ans_lo |= (1ULL << t);
            else ans_hi |= (1ULL << (t - 64));
        }
    }

    // Decode using binary search on unions
    int left = 0, right = (int)unions.size() - 1;
    int fa = 1, fb = 1; // default (should be overwritten)
    while (left <= right) {
        int mid = (left + right) >> 1;
        const auto &e = unions[mid];
        if (e.hi == ans_hi && e.lo == ans_lo) {
            fa = e.a;
            fb = e.b;
            break;
        } else if (e.hi < ans_hi || (e.hi == ans_hi && e.lo < ans_lo)) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }

    cout << "! " << fa << ' ' << fb << '\n';
    cout.flush();

    return 0;
}