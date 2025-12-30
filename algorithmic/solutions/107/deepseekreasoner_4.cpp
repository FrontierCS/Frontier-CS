#include <bits/stdc++.h>
using namespace std;

typedef unsigned long long ull;
typedef long long ll;

vector<int> primes;
vector<vector<int>> groups;
vector<ull> group_prods;
vector<ull> prime_pow(1001, 0);

void precompute() {
    // sieve primes up to 1000
    vector<bool> is_prime(1001, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i <= 1000; ++i) {
        if (is_prime[i]) {
            primes.push_back(i);
            for (int j = i * i; j <= 1000; j += i) {
                is_prime[j] = false;
            }
        }
    }

    // for each prime p compute p^e where e is minimal such that p^e > 1e9
    for (int p : primes) {
        ull val = 1;
        while (val <= 1000000000ULL) {
            val *= p;
        }
        prime_pow[p] = val;  // val <= 1e18 for all p <= 1000
    }

    // partition primes into groups with product <= 1e18
    const ull LIMIT = 1000000000000000000ULL;
    vector<int> cur_group;
    ull cur_prod = 1;
    for (int p : primes) {
        if (cur_prod > LIMIT / p) {  // adding p would exceed the limit
            groups.push_back(cur_group);
            group_prods.push_back(cur_prod);
            cur_group.clear();
            cur_prod = 1;
        }
        cur_group.push_back(p);
        cur_prod *= p;
    }
    if (!cur_group.empty()) {
        groups.push_back(cur_group);
        group_prods.push_back(cur_prod);
    }
}

int main() {
    precompute();

    int T;
    cin >> T;
    for (int game = 0; game < T; ++game) {
        vector<int> detected;
        // query each group
        for (size_t i = 0; i < groups.size(); ++i) {
            cout << "0 " << group_prods[i] << endl;
            cout.flush();
            ull g;
            cin >> g;
            if (g != 1) {
                for (int p : groups[i]) {
                    if (g % p == 0) {
                        detected.push_back(p);
                    }
                }
            }
        }

        ll K = 1;
        for (int p : detected) {
            cout << "0 " << prime_pow[p] << endl;
            cout.flush();
            ull g2;
            cin >> g2;
            int exp = 0;
            while (g2 % p == 0) {
                ++exp;
                g2 /= p;
            }
            K *= (exp + 1);
        }

        cout << "1 " << K * 2 << endl;
        cout.flush();
    }
    return 0;
}