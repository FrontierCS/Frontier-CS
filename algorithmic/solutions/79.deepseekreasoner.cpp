#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <cstdint>
#include <cmath>
#include <algorithm>

using namespace std;

using ull = unsigned long long;
using ll = long long;

// bits(x) = number of bits in binary representation of x, 0 -> 0
int bits(ull x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// B(x) = bits(x) + 1
int B(ull x) {
    return bits(x) + 1;
}

// modular multiplication using __int128
ull mulmod(ull a, ull b, ull n) {
    return (ull)((__int128)a * b % n);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ull n;
    cin >> n;

    // ----- first two queries -----
    cout << "? 1" << endl;
    ull t1;
    cin >> t1;
    int pop = (t1 - 240) / 4;   // popcount(d)

    // a = n-1
    int K = B(n-1);   // K = bits(n-1)+1
    ull S2 = (ull)K*K + 59*4;   // sum of squares for a = n-1
    cout << "? " << n-1 << endl;
    ull t2;
    cin >> t2;
    ull R2 = t2 - S2;
    ull R2_exp0 = 4 * pop;
    ull R2_exp1 = 2 * pop * K;
    int d0;
    if (llabs((ll)(R2 - R2_exp0)) < llabs((ll)(R2 - R2_exp1)))
        d0 = 0;
    else
        d0 = 1;

    vector<int> d_bits(60, 0);
    d_bits[0] = d0;

    // ----- gather many random queries -----
    const int M = 29998;   // remaining queries
    vector<ull> A(M);
    vector<ull> T(M);
    // for each a, store B(a_i) for i=0..59 and S(a)
    vector<vector<int>> B_ai(M, vector<int>(60));
    vector<ull> S_arr(M);

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    for (int idx = 0; idx < M; ++idx) {
        A[idx] = rng() % n;
        cout << "? " << A[idx] << endl;
        cin >> T[idx];

        // precompute a_i = a^(2^i) mod n and B(a_i)
        ull cur = A[idx] % n;
        ull s = 0;
        for (int i = 0; i < 60; ++i) {
            int b = B(cur);
            B_ai[idx][i] = b;
            s += (ull)b * b;
            cur = mulmod(cur, cur, n);
        }
        S_arr[idx] = s;
    }

    // ----- recover bits 1 to 59 -----
    for (int k = 1; k < 60; ++k) {
        vector<ull> err(2, 0);
        for (int cand = 0; cand < 2; ++cand) {
            d_bits[k] = cand;
            // evaluate this candidate on all stored queries
            for (int idx = 0; idx < M; ++idx) {
                ull r = 1;
                ull R_pred = 0;
                for (int i = 0; i < 60; ++i) {
                    int bit = (i <= k) ? d_bits[i] : 0;   // higher bits set to 0
                    if (bit) {
                        R_pred += (ull)B(r) * B_ai[idx][i];
                        r = mulmod(r, A[idx], n);   // careful: need a_i, not A[idx]
                        // Actually we need a_i for iteration i, which is precomputed as a_pow.
                        // But we don't have a_pow stored, only B_ai.
                        // We need the actual value to update r.
                        // So we must also store a_i values.
                        // Let's change: store a_i values as well.
                    }
                }
                ull T_pred = S_arr[idx] + R_pred;
                ll diff = (ll)T[idx] - (ll)T_pred;
                err[cand] += diff * diff;
            }
        }
        // choose candidate with smaller error
        if (err[0] < err[1])
            d_bits[k] = 0;
        else
            d_bits[k] = 1;
    }

    // ----- convert bits to integer -----
    ull d_val = 0;
    for (int i = 0; i < 60; ++i) {
        if (d_bits[i])
            d_val |= (1ULL << i);
    }

    cout << "! " << d_val << endl;

    return 0;
}