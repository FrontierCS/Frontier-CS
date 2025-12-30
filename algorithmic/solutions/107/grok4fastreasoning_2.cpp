#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    bool is_prime[1001];
    memset(is_prime, true, sizeof(is_prime));
    is_prime[0] = is_prime[1] = false;
    vector<long long> primes;
    for (long long i = 2; i <= 1000; ++i) {
        if (is_prime[i]) {
            primes.push_back(i);
            for (long long j = i * i; j <= 1000; j += i) {
                is_prime[j] = false;
            }
        }
    }
    vector<vector<long long>> groups;
    for (size_t i = 0; i < primes.size(); ) {
        vector<long long> grp;
        long long prod = 1LL;
        size_t j = i;
        for (; j < primes.size(); ++j) {
            long long p = primes[j];
            if (prod > 1000000000000000000LL / p) {
                break;
            }
            long long next_prod = prod * p;
            if (next_prod / p != prod || next_prod <= 0) {
                break;
            }
            grp.push_back(p);
            prod = next_prod;
        }
        if (!grp.empty()) {
            groups.push_back(grp);
        }
        i = j;
    }
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        vector<long long> factors;
        for (auto& grp : groups) {
            if (grp.empty()) continue;
            long long Q = 1LL;
            for (auto p : grp) {
                Q *= p;
            }
            cout << "0 " << Q << endl;
            cout.flush();
            long long G;
            cin >> G;
            for (auto p : grp) {
                if (G % p == 0) {
                    factors.push_back(p);
                }
            }
        }
        sort(factors.begin(), factors.end());
        auto it = unique(factors.begin(), factors.end());
        factors.resize(it - factors.begin());
        long long ds = 1LL;
        for (auto p : factors) {
            long long power = 1LL;
            while (true) {
                if (p > 1000000000000000000LL / power) break;
                long long next_power = power * p;
                if (next_power / p != power || next_power <= 0) break;
                power = next_power;
            }
            cout << "0 " << power << endl;
            cout.flush();
            long long gval;
            cin >> gval;
            int vv = 0;
            long long temp = gval;
            while (temp % p == 0 && temp > 0) {
                temp /= p;
                ++vv;
            }
            ds *= (vv + 1LL);
        }
        long long answer = ds * 2LL;
        cout << "1 " << answer << endl;
        cout.flush();
    }
    return 0;
}