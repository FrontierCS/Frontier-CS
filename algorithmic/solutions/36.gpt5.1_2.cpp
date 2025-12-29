#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int NUM_QUERIES = 3;
    const long long TOTAL_COST = 900000; // total number of elements we send
    const int M_EACH = TOTAL_COST / NUM_QUERIES; // 300000
    const unsigned long long BLOCK = 1000000000000ULL; // 1e12, for uniqueness
    const long long MAX_N = 1000000000LL;

    mt19937_64 rng(123456789);

    long double sumPairs = 0.0L;
    long double sumCollisions = 0.0L;

    for (int q = 0; q < NUM_QUERIES; ++q) {
        int m = M_EACH;
        cout << 0 << ' ' << m;
        for (int i = 0; i < m; ++i) {
            unsigned long long r = rng() % BLOCK;
            unsigned long long x = (unsigned long long)(i + 1) * BLOCK + r; // unique and < 1e18
            if (x == 0) x = 1; // just in case
            cout << ' ' << x;
        }
        cout << '\n';
        cout.flush();

        long long c;
        if (!(cin >> c)) {
            // If interaction fails, just exit.
            return 0;
        }

        sumCollisions += (long double)c;
        long long pairs = 1LL * m * (m - 1) / 2;
        sumPairs += (long double)pairs;
    }

    long long guess;
    if (sumCollisions <= 0.0L) {
        guess = MAX_N;
    } else {
        long double n_est = sumPairs / sumCollisions;
        if (n_est < 2.0L) n_est = 2.0L;
        if (n_est > (long double)MAX_N) n_est = (long double)MAX_N;
        guess = (long long)llround(n_est);
        if (guess < 2) guess = 2;
        if (guess > MAX_N) guess = MAX_N;
    }

    cout << 1 << ' ' << guess << '\n';
    cout.flush();

    return 0;
}