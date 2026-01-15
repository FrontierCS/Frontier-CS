#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using u64 = unsigned long long;
using i128 = __int128_t;

static inline u64 mul_mod(u64 a, u64 b, u64 mod) {
    return (u64)(((__int128)a * b) % mod);
}

static inline int bits_u64(u64 x) {
    if (!x) return 0;
    return 64 - __builtin_clzll(x);
}

static inline int64 mult_cost(u64 x, u64 y) {
    int bx = bits_u64(x) + 1;
    int by = bits_u64(y) + 1;
    return (int64)bx * (int64)by;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    u64 n;
    if (!(cin >> n)) return 0;

    const int BITS = 60;
    vector<int> d(BITS, 0);

    // Number of random queries per bit
    const int Ni = 450;
    int totalQueriesLimit = 30000;
    int usedQueries = 0;

    // Optional: one query for sanity (not used in algorithm, but keeps margin)
    // We skip extra sanity queries to maximize samples for correlation.

    // RNG
    mt19937_64 rng((u64)chrono::steady_clock::now().time_since_epoch().count());

    for (int bit = 0; bit < BITS; ++bit) {
        int curNi = Ni;
        if (usedQueries + curNi > totalQueriesLimit - 1) { // leave space for final "!"
            curNi = max(0, totalQueriesLimit - 1 - usedQueries);
        }
        if (curNi <= 0) break; // no more queries possible, but should not happen

        vector<long double> Z;
        vector<long double> R;
        Z.reserve(curNi);
        R.reserve(curNi);

        for (int q = 0; q < curNi; ++q) {
            u64 a = rng() % n;
            cout << "? " << a << '\n';
            cout.flush();
            ++usedQueries;

            long long T;
            if (!(cin >> T)) return 0;

            u64 A[BITS];
            A[0] = a % n;
            for (int i = 1; i < BITS; ++i) {
                A[i] = mul_mod(A[i - 1], A[i - 1], n);
            }

            long long Bsq = 0;
            for (int i = 0; i < BITS; ++i) {
                int b = bits_u64(A[i]) + 1;
                long long c = (long long)b * (long long)b;
                Bsq += c;
            }

            long long S = T - Bsq;

            u64 r = 1;
            for (int k = 0; k < bit; ++k) {
                if (d[k]) {
                    S -= mult_cost(r, A[k]);
                    r = mul_mod(r, A[k], n);
                }
            }

            long double Rval = (long double)S;
            long double Zval = (long double)mult_cost(r, A[bit]);

            R.push_back(Rval);
            Z.push_back(Zval);
        }

        if (curNi == 0) break;

        long double meanZ = 0.0L, meanR = 0.0L;
        for (int i = 0; i < curNi; ++i) {
            meanZ += Z[i];
            meanR += R[i];
        }
        meanZ /= (long double)curNi;
        meanR /= (long double)curNi;

        long double numer = 0.0L;
        long double denomZ = 0.0L, denomR = 0.0L;
        for (int i = 0; i < curNi; ++i) {
            long double dz = Z[i] - meanZ;
            long double dr = R[i] - meanR;
            numer += dz * dr;
            denomZ += dz * dz;
            denomR += dr * dr;
        }

        // Decide bit based on sign of covariance (numerator of correlation)
        if (numer > 0) d[bit] = 1;
        else d[bit] = 0;

        if (usedQueries >= totalQueriesLimit - 1) break;
    }

    // Reconstruct d as 64-bit integer
    unsigned long long D = 0;
    for (int i = 0; i < (int)d.size(); ++i) {
        if (d[i]) D |= (1ULL << i);
    }

    cout << "! " << D << '\n';
    cout.flush();

    return 0;
}