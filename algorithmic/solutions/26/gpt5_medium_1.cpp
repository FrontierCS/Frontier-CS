#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
    int n;
    vector<int> bit;
    Fenwick(int n=0): n(n), bit(n+1,0) {}
    void init(int n_) { n = n_; bit.assign(n+1, 0); }
    void add(int idx, int val) { for (; idx <= n; idx += idx & -idx) bit[idx] += val; }
    int sum(int idx) const { int res = 0; for (; idx > 0; idx -= idx & -idx) res += bit[idx]; return res; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> v(n+1), pos(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> v[i];
        pos[v[i]] = i;
    }

    int t = n;
    while (t > 1 && pos[t-1] < pos[t]) --t;
    int m = t - 1;

    Fenwick fw(n);
    for (int i = 1; i <= n; ++i) fw.add(i, 1);

    vector<pair<int,int>> moves;
    moves.reserve(m);
    long long sumCost = 0;
    int k = 0;
    for (int i = t - 1; i >= 1; --i) {
        int p = pos[i];
        int x = k + fw.sum(p);
        moves.emplace_back(x, 1);
        sumCost += 1;
        fw.add(p, -1);
        ++k;
    }

    long long final_cost = (sumCost + 1) * (static_cast<long long>(m) + 1);
    cout << final_cost << " " << moves.size() << "\n";
    for (auto &mv : moves) {
        cout << mv.first << " " << mv.second << "\n";
    }
    return 0;
}