#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

int main() {
    ll n;
    cin >> n;
    
    // Sieve primes up to 1e6 (sqrt(1e12))
    const int MAXP = 1000000;
    vector<bool> is_prime(MAXP + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i * i <= MAXP; ++i) {
        if (is_prime[i]) {
            for (int j = i * i; j <= MAXP; j += i) {
                is_prime[j] = false;
            }
        }
    }
    vector<ll> primes;
    for (int i = 2; i <= MAXP; ++i) {
        if (is_prime[i]) primes.push_back(i);
    }
    
    // Build pairwise coprime sequence d starting with 1
    vector<ll> d = {1};
    for (ll p : primes) {
        if (d.back() * p <= n) {
            d.push_back(p);
        } else {
            break;
        }
    }
    
    // Construct the BSU
    vector<ll> a;
    a.push_back(d[0]);                     // a1 = 1
    int m = (int)d.size() - 1;             // index of last prime in d
    for (int i = 1; i <= m; ++i) {
        a.push_back(d[i - 1] * d[i]);      // a_i = d_{i-1} * d_i
    }
    
    // Try to append one extra term to increase the sum
    if (m >= 1) {
        ll last_d = d[m];
        ll prev_d = d[m - 1];
        ll y = n / last_d;                 // largest possible multiplier
        while (y > prev_d) {
            if (y % prev_d != 0) {
                ll cand = last_d * y;
                if (cand > a.back() && cand <= n) {
                    a.push_back(cand);
                    break;
                }
            }
            --y;
        }
    }
    
    // Output
    cout << a.size() << "\n";
    for (size_t i = 0; i < a.size(); ++i) {
        if (i) cout << " ";
        cout << a[i];
    }
    cout << "\n";
    
    return 0;
}