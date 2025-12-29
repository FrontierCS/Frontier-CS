#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const ll MAXQ = 1000000000000000000LL;
const ll MAX_X = 1000000000LL;

map<ll, int> factor(ll n) {
    map<ll, int> res;
    for (ll i = 2; i * i <= n; ++i) {
        while (n % i == 0) {
            res[i]++;
            n /= i;
        }
    }
    if (n > 1) res[n]++;
    return res;
}

ll compute_power(ll p, ll max_allowed) {
    ll powq = 1;
    while (true) {
        if (p > max_allowed / p) break;
        ll next = powq * p;
        if (next > max_allowed || next / p != powq) break;
        powq = next;
    }
    return powq;
}

vector<ll> get_primes(ll limit) {
    vector<bool> is_p(limit + 1, true);
    is_p[0] = is_p[1] = false;
    for (ll i = 2; i * i <= limit; ++i) {
        if (is_p[i]) {
            for (ll j = i * i; j <= limit; j += i) {
                is_p[j] = false;
            }
        }
    }
    vector<ll> pr;
    for (ll i = 2; i <= limit; ++i) {
        if (is_p[i]) pr.push_back(i);
    }
    return pr;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    vector<ll> all_p = get_primes(1000);
    vector<ll> small_p;
    vector<ll> medium_base;
    for (ll p : all_p) {
        if (p <= 47) small_p.push_back(p);
        else medium_base.push_back(p);
    }
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        ll s = 1;
        ll dd = 1;
        map<ll, int> factors;
        // small primes
        for (ll p : small_p) {
            ll powq = compute_power(p, MAXQ);
            cout << "0 " << powq << '\n';
            cout.flush();
            ll g;
            cin >> g;
            int ex = 0;
            ll ttemp = g;
            while (ttemp % p == 0) {
                ttemp /= p;
                ++ex;
            }
            if (ex > 0) {
                factors[p] = ex;
                dd *= (ex + 1LL);
            }
        }
        // compute s
        s = 1;
        for (auto& pa : factors) {
            ll p = pa.first;
            int ex = pa.second;
            ll contrib = 1;
            for (int i = 0; i < ex; ++i) {
                contrib *= p;
            }
            s *= contrib;
        }
        // check if Y=1
        ll maxy_ = (s == 0 ? MAX_X : MAX_X / s);
        if (s == 1) maxy_ = MAX_X;
        if (maxy_ < 2) {
            cout << "1 " << dd << '\n';
            cout.flush();
            continue;
        }
        // compute trial limit
        ll tr_limit = (ll)(sqrt((double)maxy_) + 1.0);
        tr_limit = min(tr_limit, 1000LL);
        if (tr_limit < 53) {
            dd *= 2;
            cout << "1 " << dd << '\n';
            cout.flush();
            continue;
        }
        // relevant medium
        vector<ll> rel_med;
        for (ll p : medium_base) {
            if (p > tr_limit) break;
            rel_med.push_back(p);
        }
        // group
        ll max_allowed = MAXQ / s;
        vector<vector<ll>> groups;
        vector<ll> curr_g;
        ll curr_p = 1;
        for (ll p : rel_med) {
            bool can_add = (p != 0 && curr_p <= max_allowed / p);
            if (!can_add) {
                if (!curr_g.empty()) {
                    groups.push_back(curr_g);
                    curr_g.clear();
                    curr_p = 1;
                }
                curr_g.push_back(p);
                curr_p = p;
            } else {
                curr_g.push_back(p);
                curr_p *= p;
            }
        }
        if (!curr_g.empty()) groups.push_back(curr_g);
        // process groups
        for (auto& gr : groups) {
            ll prod = 1;
            for (ll pp : gr) {
                prod *= pp;
            }
            ll q = s * prod;
            if (q > MAXQ || q <= 0) continue;
            cout << "0 " << q << '\n';
            cout.flush();
            ll g_in;
            cin >> g_in;
            ll gg = g_in / s;
            if (gg <= 1) continue;
            auto fgg = factor(gg);
            for (auto& prr : fgg) {
                ll pp = prr.first;
                // full exp
                ll maxrpp = MAXQ / s;
                ll powq = compute_power(pp, maxrpp);
                ll qp = s * powq;
                cout << "0 " << qp << '\n';
                cout.flush();
                ll dg;
                cin >> dg;
                ll ggg = dg / s;
                int exx = 0;
                ll ttt = ggg;
                while (ttt % pp == 0) {
                    ttt /= pp;
                    ++exx;
                }
                if (ttt != 1) continue; // unexpected
                factors[pp] = exx;
                dd *= (exx + 1LL);
            }
        }
        // remaining
        dd *= 2;
        cout << "1 " << dd << '\n';
        cout.flush();
    }
    return 0;
}