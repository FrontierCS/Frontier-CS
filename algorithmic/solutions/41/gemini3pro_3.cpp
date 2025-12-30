#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

using namespace std;

typedef long long ll;

const int MAX_VAL = 2000005;
int min_prime[MAX_VAL];
vector<int> primes;

void sieve() {
    for (int i = 2; i < MAX_VAL; ++i) {
        if (min_prime[i] == 0) {
            min_prime[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            if (p > min_prime[i] || (ll)i * p >= MAX_VAL) break;
            min_prime[i * p] = p;
        }
    }
}

// Factorize number <= 10^12
// Optimized for numbers up to MAX_VAL via sieve, else trial division
vector<ll> get_prime_factors(ll x) {
    vector<ll> factors;
    if (x < MAX_VAL) {
        while (x > 1) {
            factors.push_back(min_prime[x]);
            x /= min_prime[x];
        }
    } else {
        for (int p : primes) {
            if ((ll)p * p > x) break;
            while (x % p == 0) {
                factors.push_back(p);
                x /= p;
            }
        }
        if (x > 1) factors.push_back(x);
    }
    return factors;
}

// Generate all divisors from prime factors
vector<ll> get_divisors_from_pf(vector<ll>& pf) {
    vector<ll> divs = {1};
    if (pf.empty()) return divs;
    sort(pf.begin(), pf.end());
    
    int n = pf.size();
    for (int i = 0; i < n; ) {
        int j = i;
        while (j < n && pf[j] == pf[i]) j++;
        int count = j - i;
        ll p = pf[i];
        
        int sz = divs.size();
        ll p_pow = p;
        for (int k = 0; k < count; ++k) {
            for (int l = 0; l < sz; ++l) {
                divs.push_back(divs[l] * p_pow);
            }
            p_pow *= p;
        }
        i = j;
    }
    return divs;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    sieve();

    ll n;
    if (!(cin >> n)) return 0;

    // Try multiple start values to maximize objective
    vector<ll> starts;
    for (int i = 1; i <= 50; ++i) starts.push_back(i);
    starts.push_back(60);
    starts.push_back(120);
    starts.push_back(360);
    starts.push_back(2520);
    
    vector<ll> best_seq;
    // Store best V as __int128 to compare accurately
    unsigned __int128 best_obj = 0;

    for (ll a_start : starts) {
        if (a_start > n) continue;

        vector<ll> seq;
        seq.reserve(2000000); // Preallocate
        seq.push_back(a_start);
        
        // Track prime factors of current 'a'
        vector<ll> current_pf = get_prime_factors(a_start);
        
        ll g_prev = 0;
        ll current_a = a_start;
        
        while (true) {
            vector<ll> divs = get_divisors_from_pf(current_pf);
            sort(divs.begin(), divs.end());
            
            auto it = upper_bound(divs.begin(), divs.end(), g_prev);
            if (it == divs.end()) break;
            
            ll d = *it;
            if (n - current_a < d) break;
            
            ll next_a = current_a + d;
            seq.push_back(next_a);
            
            // a_new = d * (a/d + 1)
            // pf_new = pf(d) + pf(a/d + 1)
            vector<ll> pf_d = get_prime_factors(d);
            vector<ll> pf_X = get_prime_factors(current_a / d + 1);
            
            current_pf = pf_d;
            current_pf.insert(current_pf.end(), pf_X.begin(), pf_X.end());
            
            current_a = next_a;
            g_prev = d;
        }
        
        unsigned __int128 current_sum = 0;
        for (ll val : seq) current_sum += val;
        unsigned __int128 current_obj = current_sum * seq.size();
        
        if (current_obj > best_obj) {
            best_obj = current_obj;
            best_seq = seq;
        }
    }

    cout << best_seq.size() << "\n";
    for (size_t i = 0; i < best_seq.size(); ++i) {
        cout << best_seq[i] << (i == best_seq.size() - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}