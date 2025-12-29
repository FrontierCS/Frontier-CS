#include <bits/stdc++.h>
using namespace std;

struct Code {
    unsigned long long lo, hi;
};

struct PairCode {
    unsigned long long lo, hi;
    bool operator<(const PairCode &o) const {
        return (hi < o.hi) || (hi == o.hi && lo < o.lo);
    }
};

static unsigned long long seed_rand = 88172645463325252ull;
unsigned long long rng() {
    seed_rand ^= seed_rand << 7;
    seed_rand ^= seed_rand >> 9;
    return seed_rand;
}

void generate_codes(int T, vector<Code> &codes) {
    const int N = 1000;
    size_t K = (size_t)N * (N + 1) / 2;
    vector<PairCode> arr(K);

    uint64_t maskLo, maskHi;
    if (T >= 64) {
        maskLo = ~0ULL;
        if (T > 64) maskHi = (1ULL << (T - 64)) - 1;
        else maskHi = 0;
    } else {
        maskLo = (1ULL << T) - 1;
        maskHi = 0;
    }

    while (true) {
        // generate random codes for positions 1..N
        for (int i = 1; i <= N; ++i) {
            uint64_t lo = rng();
            uint64_t hi = rng();
            lo &= maskLo;
            hi &= maskHi;
            if (T > 0 && lo == 0 && hi == 0) {
                int b = i % T;
                if (b < 64) lo |= (1ULL << b);
                else hi |= (1ULL << (b - 64));
            }
            codes[i].lo = lo;
            codes[i].hi = hi;
        }

        // build OR-codes for all unordered pairs (i,j), i <= j
        size_t idx = 0;
        for (int i = 1; i <= N; ++i) {
            for (int j = i; j <= N; ++j) {
                arr[idx].lo = codes[i].lo | codes[j].lo;
                arr[idx].hi = codes[i].hi | codes[j].hi;
                ++idx;
            }
        }

        sort(arr.begin(), arr.end());
        bool ok = true;
        for (size_t i = 1; i < K; ++i) {
            if (arr[i].lo == arr[i - 1].lo && arr[i].hi == arr[i - 1].hi) {
                ok = false;
                break;
            }
        }
        if (ok) break;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;
    const int N = 1000;

    int T = R;
    if (T <= 0) {
        cout << "! 1 1\n";
        cout.flush();
        return 0;
    }
    if (T > 75) T = 75; // Problem guarantees R=75; this is just a safety cap.

    vector<Code> codes(N + 1);
    generate_codes(T, codes);

    // Build test sets for each robot (bit position)
    vector<vector<int>> tests(T);
    for (int pos = 1; pos <= N; ++pos) {
        uint64_t lo = codes[pos].lo;
        uint64_t hi = codes[pos].hi;
        int uptoLo = min(T, 64);
        for (int b = 0; b < uptoLo; ++b) {
            if (lo & (1ULL << b)) tests[b].push_back(pos);
        }
        if (T > 64) {
            int hiBits = T - 64;
            for (int b = 0; b < hiBits; ++b) {
                if (hi & (1ULL << b)) tests[64 + b].push_back(pos);
            }
        }
    }

    // Send all queries
    for (int j = 0; j < T; ++j) {
        vector<int> &v = tests[j];
        cout << "? " << (int)v.size();
        for (int x : v) cout << ' ' << x;
        cout << '\n';
        cout.flush();
    }

    // Get all answers in one hour
    cout << "@\n";
    cout.flush();

    int L;
    if (!(cin >> L)) return 0;
    vector<int> ansBits(T, 0);
    for (int i = 0; i < L; ++i) {
        int x;
        cin >> x;
        if (i < T) ansBits[i] = x;
    }

    // Build observed OR-code
    Code y{0, 0};
    int uptoLo = min(T, 64);
    for (int b = 0; b < uptoLo; ++b) {
        if (ansBits[b]) y.lo |= (1ULL << b);
    }
    if (T > 64) {
        int hiBits = T - 64;
        for (int b = 0; b < hiBits; ++b) {
            if (ansBits[64 + b]) y.hi |= (1ULL << b);
        }
    }

    // Decode: find unique pair (a,b) such that code[a] OR code[b] == y
    int ansA = 1, ansB = 1;
    bool found = false;
    for (int i = 1; i <= N && !found; ++i) {
        for (int j = i; j <= N; ++j) {
            uint64_t plo = codes[i].lo | codes[j].lo;
            uint64_t phi = codes[i].hi | codes[j].hi;
            if (plo == y.lo && phi == y.hi) {
                ansA = i;
                ansB = j;
                found = true;
                break;
            }
        }
    }

    if (!found) {
        ansA = 1;
        ansB = 1;
    }

    cout << "! " << ansA << ' ' << ansB << '\n';
    cout.flush();

    return 0;
}