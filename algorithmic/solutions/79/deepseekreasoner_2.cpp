#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <cstdlib>
#include <cmath>
#include <algorithm>
using namespace std;

using ull = unsigned long long;
using ll = long long;

ull n; // global modulo

// Return number of bits in binary representation of x (0 -> 0)
int bits(ull x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// Modular multiplication using 128-bit integers
ull mulmod(ull a, ull b, ull mod) {
    return ((__int128)a * b) % mod;
}

// Compute a^{2^i} mod n for i=0..59
vector<ull> compute_powers(ull a) {
    vector<ull> A(60);
    A[0] = a % n;
    for (int i = 1; i < 60; ++i) {
        A[i] = mulmod(A[i-1], A[i-1], n);
    }
    return A;
}

// Compute the time the device would take for given a and given bits of d
ull compute_time(const vector<ull>& A, const vector<int>& bits_A, const vector<bool>& d_bits) {
    ull r = 1;
    ull total = 0;
    for (int i = 0; i < 60; ++i) {
        if (d_bits[i]) {
            int b1 = bits(r) + 1;
            total += (ull)b1 * bits_A[i];
            r = mulmod(r, A[i], n);
        }
        total += (ull)bits_A[i] * bits_A[i];
    }
    return total;
}

int main() {
    cin >> n;
    cout << "? 0" << endl;
    ull T0;
    cin >> T0;
    int pop = T0 - 61;   // popcount(d)

    vector<bool> d_bits(60, false);
    int pop_low = 0;   // number of set bits among already determined bits

    // Random number generator
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<ull> dist(0, n-1);

    const int R = 10;   // number of random candidates per query

    for (int j = 0; j < 60; ++j) {
        int Q = (j < 59) ? 500 : 499;   // queries for this bit
        int votes0 = 0, votes1 = 0;

        for (int q = 0; q < Q; ++q) {
            // Try R random a's, pick the one that maximizes the difference
            // between the expected times for d_j=0 and d_j=1.
            ull best_a = 0;
            ull best_diff = 0;

            for (int rnd = 0; rnd < R; ++rnd) {
                ull a = dist(rng);
                vector<ull> A = compute_powers(a);
                vector<int> bits_A(60);
                for (int i = 0; i < 60; ++i)
                    bits_A[i] = bits(A[i]) + 1;

                // Create two hypothesis for d: one with d_j=0, one with d_j=1.
                // For bits < j use known values, for bits > j assume 0.
                vector<bool> hyp0 = d_bits;
                vector<bool> hyp1 = d_bits;
                hyp0[j] = false;
                hyp1[j] = true;

                ull T0_hyp = compute_time(A, bits_A, hyp0);
                ull T1_hyp = compute_time(A, bits_A, hyp1);
                ull diff = (T0_hyp > T1_hyp) ? T0_hyp - T1_hyp : T1_hyp - T0_hyp;
                if (diff > best_diff) {
                    best_diff = diff;
                    best_a = a;
                }
            }

            // Perform the query with the best a
            cout << "? " << best_a << endl;
            ull T_meas;
            cin >> T_meas;

            // Recompute expected times for the chosen a
            vector<ull> A_best = compute_powers(best_a);
            vector<int> bits_A_best(60);
            for (int i = 0; i < 60; ++i)
                bits_A_best[i] = bits(A_best[i]) + 1;

            vector<bool> hyp0 = d_bits;
            vector<bool> hyp1 = d_bits;
            hyp0[j] = false;
            hyp1[j] = true;

            ull T0_hyp = compute_time(A_best, bits_A_best, hyp0);
            ull T1_hyp = compute_time(A_best, bits_A_best, hyp1);

            if (llabs((ll)T_meas - (ll)T0_hyp) < llabs((ll)T_meas - (ll)T1_hyp))
                votes0++;
            else
                votes1++;
        }

        // Decide the value of bit j
        if (votes0 > votes1) {
            d_bits[j] = false;
        } else {
            d_bits[j] = true;
            pop_low++;
        }
    }

    // Reconstruct d from its bits
    ull d = 0;
    for (int i = 0; i < 60; ++i) {
        if (d_bits[i])
            d |= (1ULL << i);
    }

    cout << "! " << d << endl;

    return 0;
}