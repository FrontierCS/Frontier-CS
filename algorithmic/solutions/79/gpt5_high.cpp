#include <bits/stdc++.h>
using namespace std;

static inline unsigned long long mul_mod(unsigned long long a, unsigned long long b, unsigned long long mod) {
    return (unsigned __int128)a * b % mod;
}

static inline int bits_len(unsigned long long x) {
    return x ? 64 - __builtin_clzll(x) : 0;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned long long n;
    if (!(cin >> n)) return 0;

    // Number of queries (must be <= 30000)
    const int BITS = 60;
    const int M = 20000;

    vector<unsigned long long> times(M);
    vector<unsigned long long> a0(M);

    // Query random 'a' values
    std::mt19937_64 rng((unsigned long long)chrono::high_resolution_clock::now().time_since_epoch().count());
    for (int j = 0; j < M; ++j) {
        unsigned long long a = rng() % n;
        a0[j] = a;
        cout << "? " << a << endl;
        cout.flush();
        unsigned long long t;
        if (!(cin >> t)) return 0;
        times[j] = t;
    }

    // Precompute a_i = a^(2^i) % n and bits(a_i)+1
    vector<unsigned long long> aseq((size_t)M * BITS);
    vector<unsigned char> abitp1((size_t)M * BITS);
    vector<unsigned long long> baseSquares(M, 0);

    for (int j = 0; j < M; ++j) {
        unsigned long long x = a0[j];
        for (int i = 0; i < BITS; ++i) {
            size_t idx = (size_t)j * BITS + i;
            aseq[idx] = x;
            int ba = bits_len(x) + 1;
            abitp1[idx] = (unsigned char)ba;
            baseSquares[j] += (unsigned long long)ba * (unsigned long long)ba;
            x = mul_mod(x, x, n);
        }
    }

    // unknownPart = total time - sum of squares costs
    vector<long long> rem(M);
    for (int j = 0; j < M; ++j) {
        rem[j] = (long long)times[j] - (long long)baseSquares[j];
    }

    // r for each query during iterative bit recovery
    vector<unsigned long long> r(M, 1ULL);

    unsigned long long d = 0;

    for (int i = 0; i < BITS; ++i) {
        long long sumRemG = 0;
        unsigned long long sumGG = 0;

        // compute g_j for each j
        vector<int> g(M);
        for (int j = 0; j < M; ++j) {
            int br = bits_len(r[j]) + 1;
            int ba = abitp1[(size_t)j * BITS + i];
            int gj = br * ba;
            g[j] = gj;
            sumRemG += (long long)gj * rem[j];
            sumGG += (unsigned long long)gj * (unsigned long long)gj;
        }

        // Decide bit using SSE comparison: SSE1 < SSE0 iff 2*sumRemG > sumGG
        int bit = ( ( (__int128)2 * ( (__int128)sumRemG ) ) > (__int128)sumGG ) ? 1 : 0;
        if (bit) d |= (1ULL << i);

        // Update rem and r for next bit if bit is 1
        if (bit) {
            for (int j = 0; j < M; ++j) {
                rem[j] -= g[j];
                r[j] = mul_mod(r[j], aseq[(size_t)j * BITS + i], n);
            }
        }
    }

    cout << "! " << d << endl;
    cout.flush();
    return 0;
}