#include <bits/stdc++.h>
using namespace std;

long long compute_power(long long p) {
    const long long MAXQ = 1000000000000000000LL;
    long long res = 1;
    while (res <= MAXQ / p) {
        res *= p;
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int L = 1000;
    vector<bool> is_composite(L + 1, false);
    vector<long long> primes;
    for (int i = 2; i <= L; ++i) {
        if (!is_composite[i]) {
            primes.push_back(i);
            for (long long j = (long long)i * i; j <= L; j += i) {
                is_composite[j] = true;
            }
        }
    }
    // Form groups using first-fit decreasing
    vector<long long> sorted_primes = primes;
    sort(sorted_primes.rbegin(), sorted_primes.rend());
    vector<vector<long long>> groups;
    vector<long long> current_prods;
    for (auto p : sorted_primes) {
        bool placed = false;
        for (size_t i = 0; i < current_prods.size(); ++i) {
            if (current_prods[i] <= 1000000000000000000LL / p) {
                current_prods[i] *= p;
                groups[i].push_back(p);
                placed = true;
                break;
            }
        }
        if (!placed) {
            groups.emplace_back(vector<long long>{p});
            current_prods.push_back(p);
        }
    }
    // Precompute group products
    vector<long long> group_prods;
    for (auto prod : current_prods) {
        group_prods.push_back(prod);
    }
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        set<long long> small_primes_set;
        // Query groups
        for (size_t g = 0; g < groups.size(); ++g) {
            cout << "0 " << group_prods[g] << endl;
            cout.flush();
            long long D;
            cin >> D;
            for (auto p : groups[g]) {
                if (D % p == 0) {
                    small_primes_set.insert(p);
                }
            }
        }
        // Now get exponents
        map<long long, int> factors;
        vector<long long> small_primes(small_primes_set.begin(), small_primes_set.end());
        for (auto p : small_primes) {
            long long powq = compute_power(p);
            cout << "0 " << powq << endl;
            cout.flush();
            long long D;
            cin >> D;
            int e = 0;
            long long temp = D;
            while (temp % p == 0 && temp > 0) {
                temp /= p;
                ++e;
            }
            if (e > 0) {
                factors[p] = e;
            }
        }
        // Compute d_S
        long long ds = 1;
        for (auto& pr : factors) {
            long long ex = (long long)pr.second + 1;
            ds *= ex;
        }
        long long ans = ds * 2;
        cout << "1 " << ans << endl;
        cout.flush();
    }
    return 0;
}