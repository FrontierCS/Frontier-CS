#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n, m;
    if (!(cin >> n >> m)) return 0;

    long long limit = max(n, m);
    int LIM = (int)limit;
    vector<bool> is_prime(LIM + 1, true);
    is_prime.assign(LIM + 1, true);
    if (LIM >= 0) is_prime[0] = false;
    if (LIM >= 1) is_prime[1] = false;
    for (int i = 2; i * 1LL * i <= LIM; ++i) {
        if (is_prime[i]) {
            for (long long j = 1LL * i * i; j <= LIM; j += i) {
                is_prime[(int)j] = false;
            }
        }
    }
    vector<int> primes;
    for (int i = 2; i <= LIM; ++i) if (is_prime[i]) primes.push_back(i);

    // Evaluate candidates
    long long bestK = -1;
    int bestMethod = -1; // 0: trivial rows, 1: trivial cols, 2: A (lines over columns), 3: B (lines over rows, transposed)
    int bestP_A = -1, bestP_B = -1;

    // Trivial methods
    if (n > bestK) { bestK = n; bestMethod = 0; }
    if (m > bestK) { bestK = m; bestMethod = 1; }

    // Strategy A: columns indexed as (u,v) with v mod P, u in [0..L-1]
    for (int p : primes) {
        if (p > m) break;
        long long L = m / p;
        if (L <= 0) continue;
        long long Rcap = min(n, 1LL * p * p);
        long long k = L * Rcap;
        if (k > bestK) {
            bestK = k;
            bestMethod = 2;
            bestP_A = p;
        }
    }

    // Strategy B: swapped roles
    for (int q : primes) {
        if (q > n) break;
        long long T = n / q;
        if (T <= 0) continue;
        long long Ccap = min(m, 1LL * q * q);
        long long k = T * Ccap;
        if (k > bestK) {
            bestK = k;
            bestMethod = 3;
            bestP_B = q;
        }
    }

    // Output based on best method
    cout << bestK << "\n";
    if (bestMethod == 0) {
        // One per row
        for (int r = 1; r <= (int)n; ++r) {
            int c = (int)((r - 1) % m) + 1;
            cout << r << " " << c << "\n";
        }
    } else if (bestMethod == 1) {
        // One per column
        for (int c = 1; c <= (int)m; ++c) {
            int r = (int)((c - 1) % n) + 1;
            cout << r << " " << c << "\n";
        }
    } else if (bestMethod == 2) {
        int p = bestP_A;
        long long L = m / p;
        long long R = min(n, 1LL * p * p);
        long long rowsUsed = 0;
        for (int a = 0; a < p && rowsUsed < R; ++a) {
            for (int b = 0; b < p && rowsUsed < R; ++b) {
                int row = (int)rowsUsed + 1;
                for (int u = 0; u < (int)L; ++u) {
                    int v = (int)((1LL * a * u + b) % p);
                    int col = u * p + v + 1;
                    cout << row << " " << col << "\n";
                }
                ++rowsUsed;
            }
        }
    } else if (bestMethod == 3) {
        int q = bestP_B;
        long long T = n / q;                   // number of u blocks along rows (swapped)
        long long Rprime = min(m, 1LL * q * q); // number of rows (swapped) i.e., columns in original
        long long rowsUsed = 0;
        for (int a = 0; a < q && rowsUsed < Rprime; ++a) {
            for (int b = 0; b < q && rowsUsed < Rprime; ++b) {
                int rs = (int)rowsUsed + 1; // swapped row -> original column
                for (int u = 0; u < (int)T; ++u) {
                    int v = (int)((1LL * a * u + b) % q);
                    int cs = u * q + v + 1; // swapped column -> original row
                    cout << cs << " " << rs << "\n";
                }
                ++rowsUsed;
            }
        }
    }
    return 0;
}