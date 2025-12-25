#include <bits/stdc++.h>
using namespace std;

class Fenwick {
public:
    vector<int> tree;
    int n;
    Fenwick(int _n) : n(_n), tree(_n + 2, 0) {}
    void update(int idx, int val) {
        while (idx <= n) {
            tree[idx] += val;
            idx += idx & -idx;
        }
    }
    int query(int idx) {
        int sum = 0;
        while (idx > 0) {
            sum += tree[idx];
            idx -= idx & -idx;
        }
        return sum;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n;
    cin >> n;
    vector<int> v(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> v[i];
    }
    Fenwick ft(n);
    vector<pair<int, int>> moves;
    ft.update(v[1], 1);
    for (int i = 2; i <= n; i++) {
        int t = v[i];
        int cnt = ft.query(t - 1);
        int y = 1 + cnt;
        if (y != i) {
            moves.emplace_back(i, y);
        }
        ft.update(t, 1);
    }
    long long sumc = 0;
    for (auto& pr : moves) {
        sumc += pr.second;
    }
    int m = moves.size();
    long long cost = (sumc + 1LL) * (m + 1LL);
    cout << cost << " " << m << "\n";
    for (auto& pr : moves) {
        cout << pr.first << " " << pr.second << "\n";
    }
}