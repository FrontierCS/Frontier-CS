#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;
using i64 = long long;

static inline int bitlen_u64(u64 x) {
    return x ? (64 - __builtin_clzll(x)) : 0;
}

static inline int mul_cost(u64 x, u64 y) {
    int bx = bitlen_u64(x);
    int by = bitlen_u64(y);
    return (bx + 1) * (by + 1);
}

static inline u64 mulmod(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

struct RecoverResult {
    u64 d = 0;
    bool exact = false;
};

struct Samples {
    u64 n = 0;
    vector<u64> A;          // flattened [sample*60 + i]
    vector<uint8_t> bitsA;  // flattened
    vector<i64> timeTotal;  // per sample
    vector<i64> squareSum;  // per sample
    int queriesUsed = 0;

    int count() const { return (int)timeTotal.size(); }
};

static RecoverResult recover_d(const Samples& S) {
    const int Q = S.count();
    RecoverResult res;
    if (Q == 0) return res;

    vector<i64> residual(Q);
    vector<u64> r(Q, 1);
    for (int s = 0; s < Q; ++s) residual[s] = S.timeTotal[s] - S.squareSum[s];

    vector<int> c(Q);

    const int G = 5;
    for (int i = 0; i < 60; ++i) {
        long double sumRes[G]{}, sumC[G]{}, sumRC[G]{}, sumCC[G]{};
        int cnt[G]{};

        for (int s = 0; s < Q; ++s) {
            int br = bitlen_u64(r[s]);
            int ba = (int)S.bitsA[s * 60 + i];
            int cost = (br + 1) * (ba + 1);
            c[s] = cost;

            int g = s % G;
            cnt[g]++;
            sumRes[g] += (long double)residual[s];
            sumC[g] += (long double)cost;
            sumRC[g] += (long double)residual[s] * (long double)cost;
            sumCC[g] += (long double)cost * (long double)cost;
        }

        int vote1 = 0, vote0 = 0;
        for (int g = 0; g < G; ++g) {
            if (cnt[g] == 0) continue;
            long double N = (long double)cnt[g];
            long double cov = sumRC[g] - sumRes[g] * sumC[g] / N;
            long double varc = sumCC[g] - sumC[g] * sumC[g] / N;
            long double D = 2 * cov - varc;
            if (D > 0) vote1++;
            else vote0++;
        }

        bool bit = (vote1 > vote0);
        if (bit) {
            res.d |= (1ULL << i);
            for (int s = 0; s < Q; ++s) {
                residual[s] -= c[s];
                r[s] = mulmod(r[s], S.A[s * 60 + i], S.n);
            }
        }
    }

    bool exact = true;
    for (int s = 0; s < Q; ++s) {
        if (residual[s] != 0) {
            exact = false;
            break;
        }
    }
    res.exact = exact;
    return res;
}

static void collect_samples(Samples& S, int need, mt19937_64& rng) {
    uniform_int_distribution<u64> dist(0, S.n - 1);

    for (int k = 0; k < need; ++k) {
        u64 a = dist(rng);

        cout << "? " << a << "\n" << flush;
        i64 t;
        if (!(cin >> t)) exit(0);
        if (t < 0) exit(0);

        u64 base = a;
        i64 sq = 0;
        for (int i = 0; i < 60; ++i) {
            S.A.push_back(base);
            int b = bitlen_u64(base);
            S.bitsA.push_back((uint8_t)b);
            sq += (i64)(b + 1) * (i64)(b + 1);
            base = mulmod(base, base, S.n);
        }

        S.timeTotal.push_back(t);
        S.squareSum.push_back(sq);
        S.queriesUsed++;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Samples S;
    if (!(cin >> S.n)) return 0;

    mt19937_64 rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (u64)(uintptr_t)&S);

    const int LIMIT = 30000;
    vector<int> batches = {8000, 8000, 8000, 5000};

    RecoverResult best;
    for (int bi = 0; bi < (int)batches.size(); ++bi) {
        int canTake = min(batches[bi], LIMIT - S.queriesUsed);
        if (canTake <= 0) break;

        collect_samples(S, canTake, rng);
        best = recover_d(S);
        if (best.exact) break;
    }

    cout << "! " << best.d << "\n" << flush;
    return 0;
}