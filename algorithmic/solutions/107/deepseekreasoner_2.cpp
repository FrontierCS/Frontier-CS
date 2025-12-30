#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

// Precompute primes up to 1000
vector<int> primes;
void sieve() {
    vector<bool> is_prime(1001, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i <= 1000; ++i) {
        if (is_prime[i]) {
            primes.push_back(i);
            for (int j = i * i; j <= 1000; j += i)
                is_prime[j] = false;
        }
    }
}

// Precompute max exponent for each prime p such that p^e <= 1e9
vector<int> max_exp;
vector<vector<ll>> pow_table;

void precompute_powers() {
    max_exp.resize(primes.size());
    pow_table.resize(primes.size());
    for (size_t i = 0; i < primes.size(); ++i) {
        int p = primes[i];
        ll val = 1;
        int e = 0;
        while (val * p <= 1000000000LL) {
            val *= p;
            ++e;
        }
        max_exp[i] = e;
        // store powers p^0 to p^e
        pow_table[i].resize(e + 1);
        pow_table[i][0] = 1;
        for (int j = 1; j <= e; ++j)
            pow_table[i][j] = pow_table[i][j-1] * p;
    }
}

// Get exponent v from g = p^v using precomputed powers
int get_exponent(int prime_idx, ll g) {
    if (g == 1) return 0;
    int lo = 0, hi = max_exp[prime_idx];
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (pow_table[prime_idx][mid] == g) return mid;
        if (pow_table[prime_idx][mid] < g) lo = mid + 1;
        else hi = mid - 1;
    }
    return 0; // should not happen
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    sieve();
    precompute_powers();
    
    // First 22 primes (indices 0..21)
    vector<int> first_prime_idx;
    for (int i = 0; i < 22; ++i) first_prime_idx.push_back(i);
    
    // 5 groups of 5 primes each, starting from index 22
    vector<vector<int>> groups;
    for (int g = 0; g < 5; ++g) {
        vector<int> grp;
        for (int j = 0; j < 5; ++j) {
            int idx = 22 + g*5 + j;
            if (idx < (int)primes.size()) grp.push_back(idx);
        }
        if (!grp.empty()) groups.push_back(grp);
    }
    
    int T;
    cin >> T;
    
    while (T--) {
        ll ans = 1;
        ll prod = 1;   // product of found prime powers (capped at 1e9+1)
        
        // Query first 22 primes with p^max_exp
        for (int idx : first_prime_idx) {
            int p = primes[idx];
            ll Q = pow_table[idx][max_exp[idx]];
            cout << "0 " << Q << endl;
            cout.flush();
            ll g;
            cin >> g;
            int v = 0;
            if (g > 1) {
                v = get_exponent(idx, g);
                for (int i = 0; i < v; ++i) {
                    prod *= p;
                    if (prod > 1000000000LL) prod = 1000000001LL;
                }
            }
            ans *= (v + 1);
        }
        
        // Query groups
        for (const auto& grp : groups) {
            ll Q_grp = 1;
            for (int idx : grp) {
                Q_grp *= primes[idx];
                if (Q_grp > 1000000000000000000LL) break; // safety
            }
            cout << "0 " << Q_grp << endl;
            cout.flush();
            ll g;
            cin >> g;
            if (g > 1) {
                // Check which primes in the group divide g
                for (int idx : grp) {
                    int p = primes[idx];
                    if (g % p == 0) {
                        // Query exponent for this prime
                        ll Q_exp = pow_table[idx][max_exp[idx]];
                        cout << "0 " << Q_exp << endl;
                        cout.flush();
                        ll g2;
                        cin >> g2;
                        int v = 0;
                        if (g2 > 1) {
                            v = get_exponent(idx, g2);
                            for (int i = 0; i < v; ++i) {
                                prod *= p;
                                if (prod > 1000000000LL) prod = 1000000001LL;
                            }
                        }
                        ans *= (v + 1);
                    }
                }
            }
        }
        
        // Final heuristic adjustment
        if (prod < 1000000LL) {
            ans *= 4;
        } else if (prod < 1000000000LL) {
            ans *= 2;
        }
        
        cout << "1 " << ans << endl;
        cout.flush();
    }
    
    return 0;
}