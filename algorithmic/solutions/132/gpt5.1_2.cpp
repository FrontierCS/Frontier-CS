#include <bits/stdc++.h>
using namespace std;

struct Code {
    uint64_t lo, hi;
};

struct UnionCode {
    uint64_t lo, hi;
    uint16_t a, b;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    const int N = 1000;
    int T = R; // use all robots

    int hiBits = (T > 64) ? (T - 64) : 0;
    uint64_t loMask = (T >= 64) ? ~0ull : (T == 0 ? 0ull : ((1ull << T) - 1));
    uint64_t hiMask = (hiBits == 0) ? 0ull : ((1ull << hiBits) - 1);

    mt19937_64 rng(712367231233ull);

    vector<Code> codes(N);
    size_t numPairs = (size_t)N * (N + 1) / 2;
    vector<UnionCode> mapping;
    mapping.reserve(numPairs);

    while (true) {
        // generate random codes
        for (int i = 0; i < N; i++) {
            uint64_t lo, hi;
            while (true) {
                lo = rng();
                if (T < 64) lo &= loMask;
                hi = hiBits ? (rng() & hiMask) : 0ull;
                if ((lo | hi) != 0ull) break; // avoid all-zero codeword
            }
            codes[i] = {lo, hi};
        }

        // build mapping from union codes to pairs
        mapping.clear();
        for (int i = 0; i < N; i++) {
            for (int j = i; j < N; j++) {
                uint64_t ulo = codes[i].lo | codes[j].lo;
                uint64_t uhi = codes[i].hi | codes[j].hi;
                mapping.push_back({ulo, uhi, (uint16_t)i, (uint16_t)j});
            }
        }

        sort(mapping.begin(), mapping.end(),
             [](const UnionCode &x, const UnionCode &y) {
                 if (x.hi != y.hi) return x.hi < y.hi;
                 return x.lo < y.lo;
             });

        bool ok = true;
        for (size_t k = 1; k < mapping.size(); k++) {
            if (mapping[k].hi == mapping[k - 1].hi &&
                mapping[k].lo == mapping[k - 1].lo) {
                ok = false;
                break;
            }
        }
        if (ok) break;
    }

    // build tests from codes
    vector<vector<int>> tests(T);
    for (int i = 0; i < N; i++) {
        uint64_t lo = codes[i].lo;
        int upto = min(T, 64);
        for (int b = 0; b < upto; b++)
            if ((lo >> b) & 1ull)
                tests[b].push_back(i);
        if (T > 64) {
            uint64_t hi = codes[i].hi;
            for (int b = 0; b < hiBits; b++)
                if ((hi >> b) & 1ull)
                    tests[64 + b].push_back(i);
        }
    }

    // send all robots
    for (int t = 0; t < T; t++) {
        cout << "? " << tests[t].size();
        for (int idx : tests[t]) cout << ' ' << (idx + 1);
        cout << '\n' << flush;
    }

    // wait one hour and get all answers
    cout << "@\n" << flush;
    int L;
    if (!(cin >> L)) return 0;
    vector<int> ans(L);
    for (int i = 0; i < L; i++) cin >> ans[i];

    uint64_t Blo = 0, Bhi = 0;
    for (int t = 0; t < L; t++) if (ans[t]) {
        if (t < 64) Blo |= (1ull << t);
        else Bhi |= (1ull << (t - 64));
    }

    // decode: find pair whose union matches (Blo,Bhi)
    UnionCode key{Blo, Bhi, 0, 0};
    int l = 0, r = (int)mapping.size();
    while (l < r) {
        int m = (l + r) / 2;
        const UnionCode &u = mapping[m];
        if (u.hi < key.hi || (u.hi == key.hi && u.lo < key.lo))
            l = m + 1;
        else
            r = m;
    }

    int a = 0, b = 0;
    if (l < (int)mapping.size() &&
        mapping[l].hi == key.hi && mapping[l].lo == key.lo) {
        a = mapping[l].a;
        b = mapping[l].b;
    } else {
        // fallback (should not happen)
        a = b = 0;
    }

    cout << "! " << (a + 1) << ' ' << (b + 1) << '\n' << flush;
    return 0;
}