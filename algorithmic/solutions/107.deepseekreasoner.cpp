#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

vector<int> primes;
const int MAXP = 2000; // cover primes up to 2000

void sieve() {
    vector<bool> isPrime(MAXP + 1, true);
    for (int i = 2; i <= MAXP; i++) {
        if (isPrime[i]) {
            primes.push_back(i);
            for (int j = i * i; j <= MAXP; j += i)
                isPrime[j] = false;
        }
    }
}

ll powll(ll a, int b) {
    ll res = 1;
    for (int i = 0; i < b; i++) {
        res *= a;
        if (res > 1e18) return 1e18 + 1; // safety, not actually used
    }
    return res;
}

int main() {
    sieve();
    // maximum exponent for each prime such that p^e <= 1e9
    map<int, int> maxExp;
    for (int p : primes) {
        int e = 0;
        ll val = 1;
        while (val * p <= 1e9) {
            val *= p;
            e++;
        }
        maxExp[p] = e;
    }

    // group primes so that product of each group <= 1e18
    vector<vector<int>> groups;
    vector<ll> groupProd;
    __int128 prod = 1;
    vector<int> cur;
    for (int p : primes) {
        if (prod * p > (__int128)1e18) {
            groups.push_back(cur);
            groupProd.push_back((ll)prod);
            cur.clear();
            prod = 1;
        }
        cur.push_back(p);
        prod *= p;
    }
    if (!cur.empty()) {
        groups.push_back(cur);
        groupProd.push_back((ll)prod);
    }

    int T;
    cin >> T;
    while (T--) {
        map<int, int> exp;
        set<int> candidates;

        // batch queries to detect small prime factors
        for (size_t i = 0; i < groups.size(); i++) {
            cout << "0 " << groupProd[i] << endl;
            cout.flush();
            ll g;
            cin >> g;
            if (g > 1) {
                for (int p : groups[i]) {
                    if (g % p == 0)
                        candidates.insert(p);
                }
            }
        }

        // estimate exponent for each candidate prime
        for (int p : candidates) {
            int lo = 1, hi = maxExp[p];
            int e = 0;
            while (lo <= hi) {
                int mid = (lo + hi) / 2;
                ll q = powll(p, mid);
                cout << "0 " << q << endl;
                cout.flush();
                ll g;
                cin >> g;
                ll expected = powll(p, mid);
                if (g == expected) {
                    e = mid;
                    lo = mid + 1;
                } else {
                    hi = mid - 1;
                }
            }
            exp[p] = e;
        }

        // compute divisor count from small primes
        ll d_small = 1;
        for (auto &[p, e] : exp)
            d_small *= (e + 1);

        ll ans = d_small * 2;
        cout << "1 " << ans << endl;
        cout.flush();
    }
    return 0;
}