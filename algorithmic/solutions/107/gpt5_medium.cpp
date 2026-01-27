#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const unsigned long long LIM = (unsigned long long)1e18;

    // Sieve primes up to 1000
    int MAXP = 1000;
    vector<int> primes;
    vector<bool> is_composite(MAXP + 1, false);
    for (int i = 2; i <= MAXP; ++i) {
        if (!is_composite[i]) {
            primes.push_back(i);
            if ((long long)i * i <= MAXP) {
                for (int j = i * i; j <= MAXP; j += i) is_composite[j] = true;
            }
        }
    }

    // Group primes into products not exceeding 1e18
    vector<vector<int>> groups;
    {
        vector<int> cur;
        unsigned long long prod = 1;
        for (int p : primes) {
            if (prod > LIM / (unsigned long long)p) {
                if (!cur.empty()) groups.push_back(cur);
                cur.clear();
                prod = 1;
            }
            prod *= (unsigned long long)p;
            cur.push_back(p);
        }
        if (!cur.empty()) groups.push_back(cur);
    }

    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; ++tc) {
        vector<int> found;

        // Phase 1: detect which primes <= 1000 divide X
        for (auto &g : groups) {
            unsigned long long Q = 1;
            for (int p : g) Q *= (unsigned long long)p;
            cout << "0 " << Q << "\n";
            cout.flush();
            unsigned long long R;
            if (!(cin >> R)) return 0;
            for (int p : g) {
                if (R % (unsigned long long)p == 0) {
                    found.push_back(p);
                }
            }
        }

        // Phase 2: for each found prime, find its exact exponent
        unsigned long long d_small = 1;
        for (int p : found) {
            // compute max power of p not exceeding 1e18
            unsigned long long Q = 1;
            while (Q <= LIM / (unsigned long long)p) Q *= (unsigned long long)p;
            cout << "0 " << Q << "\n";
            cout.flush();
            unsigned long long R;
            if (!(cin >> R)) return 0;
            int e = 0;
            while (R % (unsigned long long)p == 0) {
                R /= (unsigned long long)p;
                ++e;
            }
            d_small *= (unsigned long long)(e + 1);
        }

        // Final answer: multiply by 2 to account for possible large primes (>1000)
        unsigned long long ans = d_small * 2ULL;

        cout << "1 " << ans << "\n";
        cout.flush();
    }
    return 0;
}