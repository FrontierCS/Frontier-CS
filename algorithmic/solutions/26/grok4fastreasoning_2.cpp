#include <bits/stdc++.h>
using namespace std;

class Fenwick {
public:
    vector<int> tree;
    int nn;
    Fenwick(int n) : nn(n), tree(n + 2, 0) {}
    void update(int idx, int val) {
        while (idx <= nn) {
            tree[idx] += val;
            idx += idx & -idx;
        }
    }
    int prefix(int idx) {
        int sum = 0;
        while (idx > 0) {
            sum += tree[idx];
            idx -= idx & -idx;
        }
        return sum;
    }
    int query(int l, int r) {
        if (l > r) return 0;
        return prefix(r) - prefix(l - 1);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    vector<int> v(n + 1);
    vector<int> position(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> v[i];
        position[v[i]] = i;
    }
    // Prefix method
    Fenwick ft1(n + 1);
    vector<int> counts(n + 1);
    for (int i = 1; i <= n; i++) {
        int val = v[i];
        counts[val] = ft1.query(val, n);
        ft1.update(val, 1);
    }
    long long total_cost1 = 0;
    int m1 = 0;
    vector<pair<int, int>> moves1;
    for (int k = 1; k <= n; k++) {
        int cnt = counts[k];
        if (cnt > 0) {
            int x = k + cnt;
            int y = k;
            moves1.emplace_back(x, y);
            total_cost1 += y;
            m1++;
        }
    }
    long long cost1 = (total_cost1 + 1LL) * (m1 + 1LL);
    // Suffix method
    Fenwick ft2(n + 1);
    vector<bool> needs_move(n + 1, false);
    vector<int> move_x(n + 1, 0);
    for (int k = 1; k <= n; k++) {
        int p = position[k];
        int cnt = ft2.query(1, p - 1);
        if (cnt != k - 1) {
            needs_move[k] = true;
            move_x[k] = cnt + 1;
        }
        ft2.update(p, 1);
    }
    long long total_cost2 = 0;
    int m2 = 0;
    vector<pair<int, int>> moves2;
    for (int k = n; k >= 1; k--) {
        if (needs_move[k]) {
            int x = move_x[k];
            int y = k;
            moves2.emplace_back(x, y);
            total_cost2 += y;
            m2++;
        }
    }
    long long cost2 = (total_cost2 + 1LL) * (m2 + 1LL);
    // Choose the better one
    if (cost1 <= cost2) {
        cout << cost1 << " " << m1 << "\n";
        for (auto p : moves1) {
            cout << p.first << " " << p.second << "\n";
        }
    } else {
        cout << cost2 << " " << m2 << "\n";
        for (auto p : moves2) {
            cout << p.first << " " << p.second << "\n";
        }
    }
    return 0;
}