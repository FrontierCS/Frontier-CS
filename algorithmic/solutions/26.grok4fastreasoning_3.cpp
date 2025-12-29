#include <bits/stdc++.h>
using namespace std;
using ll = long long;

class Fenwick {
private:
    vector<ll> tree;
    int n;
public:
    Fenwick(int _n) : n(_n), tree(_n + 1, 0) {}
    void update(int idx, ll val) {
        while (idx <= n) {
            tree[idx] += val;
            idx += idx & -idx;
        }
    }
    ll query(int idx) {
        ll sum = 0;
        while (idx > 0) {
            sum += tree[idx];
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
    for (int i = 1; i <= n; i++) {
        cin >> v[i];
    }
    vector<int> pos(n + 1);
    for (int i = 1; i <= n; i++) {
        pos[v[i]] = i;
    }
    vector<int> minpos(n + 1);
    minpos[n] = pos[n];
    for (int i = n - 1; i >= 1; i--) {
        minpos[i] = min(pos[i], minpos[i + 1]);
    }
    Fenwick ft(n);
    vector<pair<int, int>> moves;
    ll total_sum = 0;
    for (int i = n; i >= 1; i--) {
        ll cnt = (pos[i] > 1 ? ft.query(1, pos[i] - 1) : 0);
        int t = 1 + (int)cnt;
        if (t > 1) {
            int x = i + t - 1;
            int y = i;
            moves.emplace_back(x, y);
            total_sum += y;
        }
        ft.update(pos[i], 1);
    }
    reverse(moves.begin(), moves.end());
    ll m = moves.size();
    ll final_cost = (total_sum + 1) * (m + 1);
    cout << final_cost << " " << m << "\n";
    for (auto [x, y] : moves) {
        cout << x << " " << y << "\n";
    }
    return 0;
}