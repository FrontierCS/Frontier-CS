#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

const int M = 1000; // step size for baby-step giant-step

ll query(ll v, ll x) {
    cout << "? " << v << " " << x << endl;
    ll res;
    cin >> res;
    return res;
}

void answer(ll s) {
    cout << "! " << s << endl;
}

vector<ll> get_divisors(ll D) {
    vector<ll> divs;
    for (ll d = 1; d * d <= D; ++d) {
        if (D % d == 0) {
            divs.push_back(d);
            if (d * d != D) {
                divs.push_back(D / d);
            }
        }
    }
    sort(divs.begin(), divs.end());
    return divs;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    for (int g = 0; g < n; ++g) {
        // Get a vertex on the cycle by moving one step from vertex 1
        ll a = query(1, 1);

        unordered_map<ll, int> baby;
        baby[a] = 0;           // step 0
        ll D = 0;
        bool found = false;

        // Baby steps: store f^i(a) for i = 1 .. M-1
        for (int i = 1; i < M; ++i) {
            ll res = query(a, i);
            if (baby.count(res)) {
                int j = baby[res];
                D = i - j;
                found = true;
                break;
            }
            baby[res] = i;
        }

        // Giant steps: compute f^(k*M)(a) for k = 1 .. M
        if (!found) {
            for (int k = 1; k <= M; ++k) {
                ll x = 1LL * k * M;
                ll res = query(a, x);
                if (baby.count(res)) {
                    int j = baby[res];
                    D = x - j;   // = k*M - j
                    found = true;
                    break;
                }
            }
        }

        // D is a multiple of the cycle length L.
        // Find L by testing divisors of D.
        vector<ll> divisors = get_divisors(D);
        ll L = -1;
        for (ll cand : divisors) {
            if (cand >= 3 && cand <= 1000000) {
                ll res = query(a, cand);
                if (res == a) {
                    L = cand;
                    break;
                }
            }
        }

        // Fallback (should not happen if logic is correct)
        if (L == -1 && D >= 3 && D <= 1000000) {
            L = D;
        }

        answer(L);

        // Read verdict
        int verdict;
        cin >> verdict;
        if (verdict == -1) {
            return 0;
        }
    }

    return 0;
}