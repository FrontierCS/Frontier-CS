#include <bits/stdc++.h>
using namespace std;

static inline long long query(long long x) {
    cout << "walk " << x << endl;
    cout.flush();
    long long y;
    if (!(cin >> y)) exit(0);
    if (y == -1) exit(0);
    return y;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Initial query to get current label
    long long cur = query(0);

    // Single large step to obtain a multiple of n
    const long long X = 1000000000LL;
    long long y = query(X);
    long long ans = llabs(X - (y - cur));
    if (ans == 0) ans = 1; // Fallback, though this should not generally happen

    // Factorize ans to reduce it to n using interactive checks
    long long temp = ans;
    vector<long long> primes;
    for (long long p = 2; p * p <= temp; ++p) {
        if (temp % p == 0) {
            primes.push_back(p);
            while (temp % p == 0) temp /= p;
        }
    }
    if (temp > 1) primes.push_back(temp);

    // Current label after the last query
    cur = y;

    for (long long p : primes) {
        while (ans % p == 0) {
            long long newAns = ans / p;
            // Test if n divides newAns by checking if walking newAns returns to the same label
            long long y1 = query(newAns);
            if (y1 == cur) {
                ans = newAns; // Successful division; we stayed at the same label
                // cur remains unchanged
            } else {
                // Revert to the original label by walking the remaining distance to complete 'ans'
                long long back = ans - newAns; // This is <= 1e9 since ans <= 2e9 and p >= 2
                long long y2 = query(back);
                cur = y2; // Should be equal to original 'cur'
                break;
            }
        }
    }

    // Output the final guess
    cout << "guess " << ans << endl;
    cout.flush();

    return 0;
}