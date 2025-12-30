#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

typedef long long ll;

vector<ll> solve(ll m, ll C) {
    vector<ll> candidates;
    ll twoC = 2 * C;
    for (ll k = 1; k <= m; ++k) {
        if (twoC % k != 0) continue;
        ll num = 2 * m - twoC / k;
        if (num <= 0) continue;
        ll denom = k + 1;
        if (num % denom != 0) continue;
        ll n = num / denom;
        if (n < 2 || n > 1000000000) continue;
        if (m / n != k) continue;
        ll r = m - k * n;
        ll expected = (k * (n * (k - 1) + 2 * r)) / 2;
        if (expected == C) {
            candidates.push_back(n);
        }
    }
    return candidates;
}

int main() {
    const ll L = 1000;
    const ll M = 1000000 - L; // 999000

    // First query with small m
    cout << "0 " << L;
    for (ll i = 1; i <= L; ++i) cout << " " << i;
    cout << endl;
    cout.flush();

    ll C1;
    cin >> C1;
    if (C1 > 0) {
        vector<ll> cand = solve(L, C1);
        if (!cand.empty()) {
            cout << "1 " << cand[0] << endl;
            cout.flush();
            return 0;
        }
    }

    // Second query with large m
    cout << "0 " << M;
    for (ll i = 1; i <= M; ++i) cout << " " << i;
    cout << endl;
    cout.flush();

    ll C2;
    cin >> C2;
    if (C2 > 0) {
        vector<ll> cand = solve(M, C2);
        if (!cand.empty()) {
            cout << "1 " << cand[0] << endl;
            cout.flush();
            return 0;
        }
    }

    // If both queries gave zero collisions, guess n = 1000000
    cout << "1 1000000" << endl;
    cout.flush();

    return 0;
}