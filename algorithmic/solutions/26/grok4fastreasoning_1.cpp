#include <bits/stdc++.h>
using namespace std;

using ll = long long;

class Fenwick {
public:
    vector<ll> t;
    int n;
    Fenwick(int _n) : n(_n), t(_n + 2, 0) {}
    void update(int idx, ll val) {
        while (idx <= n) {
            t[idx] += val;
            idx += idx & -idx;
        }
    }
    ll query(int idx) {
        ll sum = 0;
        while (idx > 0) {
            sum += t[idx];
            idx -= idx & -idx;
        }
        return sum;
    }
    ll query(int l, int r) {
        if (l > r) return 0;
        return query(r) - query(l - 1);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    vector<int> v(n + 1);
    vector<int> pos(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> v[i];
        pos[v[i]] = i;
    }
    Fenwick ft(n);
    for (int i = 1; i <= n; ++i) {
        ft.update(i, 1);
    }
    vector<pair<int, int>> moves;
    ll sumy = 0;
    for (int i = 1; i < n; ++i) {
        int p = pos[i];
        ll cnt = (p > 1 ? ft.query(1, p - 1) : 0LL);
        ll rr = cnt + 1;
        if (rr > 1) {
            int jj = i + (int)rr - 1;
            moves.emplace_back(jj, i);
            sumy += i;
        }
        ft.update(p, -1);
    }
    ll m = moves.size();
    ll min_cost = (sumy + 1) * (m + 1);
    cout << min_cost << " " << m << "\n";
    for (auto [x, y] : moves) {
        cout << x << " " << y << "\n";
    }
    return 0;
}