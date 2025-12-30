#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

const ll MAX_X = 1000000000;
const ll MAX_Q = 1000000000000000000LL;
const int PRIME_LIMIT = 1000;

vector<int> primes;

void sieve() {
    vector<bool> is_prime(PRIME_LIMIT + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i <= PRIME_LIMIT; ++i) {
        if (is_prime[i]) {
            primes.push_back(i);
            for (int j = i * i; j <= PRIME_LIMIT; j += i)
                is_prime[j] = false;
        }
    }
}

// Precompute batches of primes whose product fits in 1e18
vector<vector<int>> batches;
vector<ll> batch_products;

void prepare_batches() {
    ll LIM = MAX_Q;
    int i = 0;
    while (i < (int)primes.size()) {
        vector<int> batch;
        ll prod = 1;
        while (i < (int)primes.size()) {
            int p = primes[i];
            if (prod > LIM / p) break;
            prod *= p;
            batch.push_back(p);
            i++;
        }
        if (batch.empty()) break; // should not happen
        batches.push_back(batch);
        batch_products.push_back(prod);
    }
}

// Compute p^e, but stop if exceeds 1e9 (since X <= 1e9)
ll power_lim(ll p, ll e, ll lim = MAX_X) {
    ll res = 1;
    for (ll i = 0; i < e; ++i) {
        if (res > lim / p) return lim + 1;
        res *= p;
    }
    return res;
}

void solve_game() {
    unordered_map<int, int> found; // prime -> exponent
    // Phase 1: batch queries to discover which primes divide X
    for (int idx = 0; idx < (int)batches.size(); ++idx) {
        cout << "0 " << batch_products[idx] << endl;
        cout.flush();
        ll g;
        cin >> g;
        if (g > 1) {
            for (int p : batches[idx]) {
                if (g % p == 0) {
                    found[p] = 0; // mark found, exponent to be determined
                }
            }
        }
    }

    // Phase 2: determine exponent for each found prime
    for (auto& entry : found) {
        int p = entry.first;
        // find maximum e such that p^e divides X
        ll low = 1;
        ll high = 0;
        ll temp = p;
        while (temp <= MAX_X) {
            high++;
            if (temp > MAX_X / p) break;
            temp *= p;
        }

        ll e = 0;
        ll cur_pow = 1;
        // exponential search
        for (ll step = 1; ; step *= 2) {
            ll test_exp = e + step;
            ll test_pow = power_lim(p, test_exp);
            if (test_pow > MAX_X) break;
            cout << "0 " << test_pow << endl;
            cout.flush();
            ll res;
            cin >> res;
            if (res == test_pow) {
                e = test_exp;
                cur_pow = test_pow;
            } else {
                break;
            }
        }
        // binary search between e+1 and high
        ll l = e + 1, r = high;
        while (l <= r) {
            ll mid = (l + r) / 2;
            ll mid_pow = power_lim(p, mid);
            if (mid_pow > MAX_X) {
                r = mid - 1;
                continue;
            }
            cout << "0 " << mid_pow << endl;
            cout.flush();
            ll res;
            cin >> res;
            if (res == mid_pow) {
                e = mid;
                l = mid + 1;
            } else {
                r = mid - 1;
            }
        }
        entry.second = e; // store exponent
    }

    ll ans_div = 1;
    for (auto& entry : found) {
        ans_div *= (entry.second + 1);
    }
    if (ans_div > 1) {
        cout << "1 " << ans_div * 2 << endl;
    } else {
        cout << "1 1" << endl;
    }
    cout.flush();
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    sieve();
    prepare_batches();

    int T;
    cin >> T;
    while (T--) {
        solve_game();
    }

    return 0;
}