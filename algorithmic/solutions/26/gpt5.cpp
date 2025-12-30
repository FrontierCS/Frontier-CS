#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
    int n;
    vector<int> f;
    Fenwick(int n=0): n(n), f(n+1,0) {}
    void init(int n_) { n = n_; f.assign(n+1,0); }
    void add(int i, int v) { for (; i<=n; i+=i&-i) f[i]+=v; }
    int sum(int i) const { int s=0; for (; i>0; i-=i&-i) s+=f[i]; return s; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> v(n+1), pos(n+1);
    for (int i=1;i<=n;i++){
        cin >> v[i];
        pos[v[i]] = i;
    }
    int j = n;
    while (j > 1 && pos[j-1] < pos[j]) --j;
    int m = j - 1;
    Fenwick bit(n);
    vector<pair<int,int>> ops;
    ops.reserve(m);
    int tot = 0;
    for (int t = j-1; t >= 1; --t) {
        int p = pos[t];
        int leq = bit.sum(p);
        int greater = tot - leq;
        int x_cur = p + greater;
        ops.emplace_back(x_cur, 1);
        bit.add(p, 1);
        ++tot;
    }
    long long total_y = m; // all y = 1
    long long final_cost = (total_y + 1) * (m + 1LL);
    cout << final_cost << " " << m << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}