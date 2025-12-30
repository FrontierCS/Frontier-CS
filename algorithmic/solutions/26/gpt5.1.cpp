#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
    int n;
    vector<int> bit;
    Fenwick(int n = 0) { init(n); }
    void init(int n_) {
        n = n_;
        bit.assign(n + 1, 0);
    }
    void add(int idx, int val) {
        for (; idx <= n; idx += idx & -idx) bit[idx] += val;
    }
    int sum(int idx) const {
        int res = 0;
        for (; idx > 0; idx -= idx & -idx) res += bit[idx];
        return res;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> v(n + 1), pos(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> v[i];
        pos[v[i]] = i;
    }

    Fenwick bit(n);
    vector<long long> step_pos(n + 1);

    for (int val = n; val >= 1; --val) {
        bit.add(pos[val], 1);
        long long rank = bit.sum(pos[val]);
        long long p = (long long)(val - 1) + rank;
        step_pos[val] = p;
    }

    vector<pair<int,int>> ops;
    long long sumY = 0;
    for (int i = 1; i <= n; ++i) {
        long long x = step_pos[i];
        if (x > i) {
            ops.emplace_back((int)x, i);
            sumY += i; // y = i
        }
    }

    long long k = (long long)ops.size();
    long long min_cost = (sumY + 1) * (k + 1);

    cout << min_cost << ' ' << k << '\n';
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }

    return 0;
}