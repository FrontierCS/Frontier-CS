#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long n;
    if (!(cin >> n)) return 0;

    // Precompute powers of two up to sufficient range
    const int P = 70;
    vector<unsigned __int128> pow2(P);
    pow2[0] = 1;
    for (int i = 1; i < P; ++i) pow2[i] = pow2[i-1] * 2;

    // Sieve primes up to 1e6 for smallest prime factor computations
    const int LIM = 1000000;
    vector<bool> is_prime(LIM + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i * 1LL * i <= LIM; ++i) {
        if (is_prime[i]) {
            for (int j = i * i; j <= LIM; j += i) is_prime[j] = false;
        }
    }
    vector<int> primes;
    for (int i = 2; i <= LIM; ++i) if (is_prime[i]) primes.push_back(i);

    auto composite_with_spf = [&](unsigned long long x, unsigned long long &spf) -> bool {
        if (x < 4) return false;
        if ((x & 1ULL) == 0ULL) { spf = 2; return true; }
        unsigned long long r = (unsigned long long) sqrtl((long double)x);
        for (int p : primes) {
            if ((unsigned long long)p > r) break;
            if (x % (unsigned long long)p == 0ULL) { spf = (unsigned long long)p; return true; }
        }
        return false;
    };

    unsigned __int128 bestV = 0;
    int bestType = 0; // 1 = A, 2 = B, 3 = C
    int bestK = 1;
    unsigned long long bestS = 0; // store parameter s for A
    unsigned long long bestB1 = 0, bestP = 0; // parameters for C, B uses b1 recalculated

    // Option A
    for (int k = 1; k < P; ++k) {
        if (pow2[k-1] > (unsigned __int128)n) break;
        unsigned long long s = (unsigned long long)((unsigned __int128)n / pow2[k-1]);
        unsigned __int128 S = (unsigned __int128)s * (pow2[k] - 1);
        unsigned __int128 V = (unsigned __int128)k * S;
        if (V > bestV) {
            bestV = V;
            bestType = 1;
            bestK = k;
            bestS = s;
        }
    }

    // Option B
    for (int k = 2; k < P; ++k) {
        if (pow2[k-2] > (unsigned __int128)n) break;
        unsigned long long b1 = (unsigned long long)((unsigned __int128)n / pow2[k-2]);
        if (b1 >= 2ULL) {
            unsigned __int128 last = (unsigned __int128)b1 * pow2[k-2];
            unsigned __int128 S = 2 * last - 1;
            unsigned __int128 V = (unsigned __int128)k * S;
            if (V > bestV) {
                bestV = V;
                bestType = 2;
                bestK = k;
                bestB1 = b1; // will recompute anyway, but store for clarity
            }
        }
    }

    // Option C (two-prefix strategy)
    for (int k = 3; k < P; ++k) {
        if (pow2[k-3] > (unsigned __int128)n) break;
        unsigned long long d = (unsigned long long)pow2[k-3];
        unsigned long long b1max = n / d;
        if (b1max < 4ULL) continue;
        unsigned long long b1 = b1max;
        unsigned long long spf = 0;
        // Find composite b1 <= b1max
        while (b1 >= 4ULL) {
            if ((b1 & 1ULL) == 0ULL) { spf = 2ULL; break; }
            unsigned long long tmp_spf = 0;
            if (composite_with_spf(b1, tmp_spf)) { spf = tmp_spf; break; }
            --b1;
        }
        if (b1 >= 4ULL) {
            unsigned long long p = spf;
            unsigned __int128 last = (unsigned __int128)b1 * d;
            if (last > (unsigned __int128)n) continue; // safety
            unsigned __int128 S = 2 * last + (unsigned __int128)b1 - 2 * (unsigned __int128)p - 1;
            unsigned __int128 V = (unsigned __int128)k * S;
            if (V > bestV) {
                bestV = V;
                bestType = 3;
                bestK = k;
                bestB1 = b1;
                bestP = p;
            }
        }
    }

    // Output based on bestType
    cout << bestK << "\n";
    if (bestType == 1) {
        // A: a_i = s * 2^{i-1}
        for (int i = 0; i < bestK; ++i) {
            unsigned long long val = (unsigned long long)((unsigned __int128)bestS * pow2[i]);
            if (i) cout << ' ';
            cout << val;
        }
        cout << "\n";
    } else if (bestType == 2) {
        // B: a1 = b1 - 1; then b1 * 2^j for j=0..k-2
        unsigned long long d = (unsigned long long)pow2[bestK-2];
        unsigned long long b1 = n / d;
        cout << (b1 - 1);
        for (int j = 0; j <= bestK - 2; ++j) {
            unsigned long long val = (unsigned long long)((unsigned __int128)b1 * pow2[j]);
            cout << ' ' << val;
        }
        cout << "\n";
    } else if (bestType == 3) {
        // C: a1 = b1 - p - 1; a2 = b1 - p; then b1 * 2^j for j=0..k-3
        unsigned long long b1 = bestB1, p = bestP;
        cout << (b1 - p - 1) << ' ' << (b1 - p);
        for (int j = 0; j <= bestK - 3; ++j) {
            unsigned long long val = (unsigned long long)((unsigned __int128)b1 * pow2[j]);
            cout << ' ' << val;
        }
        cout << "\n";
    } else {
        // Fallback (should not happen): single element n
        cout << 1 << "\n" << n << "\n";
    }

    return 0;
}