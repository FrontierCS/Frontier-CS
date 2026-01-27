#include <bits/stdc++.h>
using namespace std;

struct BIT {
    int n;
    vector<int> f;
    BIT(int n=0): n(n), f(n+1,0) {}
    void init(int n_) { n = n_; f.assign(n+1, 0); }
    void add(int i, int v){ for(; i<=n; i+=i&-i) f[i]+=v; }
    int sumPrefix(int i){ int s=0; for(; i>0; i-=i&-i) s+=f[i]; return s; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<int> v(n+1), pos(n+1);
    for(int i=1;i<=n;i++){
        cin >> v[i];
        pos[v[i]] = i;
    }
    BIT bit(n);
    for(int i=1;i<=n;i++) bit.add(i,1);
    vector<pair<int,int>> ops;
    ops.reserve(n);
    long long totalY = 0;
    for(int val = n; val >= 1; --val){
        int m = n - val;
        int cnt_before = bit.sumPrefix(pos[val]-1);
        int x = m + cnt_before + 1;
        ops.emplace_back(x, 1);
        totalY += 1;
        bit.add(pos[val], -1);
    }
    long long moves = ops.size();
    __int128 cost = (__int128)(totalY + 1) * (__int128)(moves + 1);
    long long min_cost = (long long)cost;
    cout << min_cost << " " << moves << "\n";
    for(auto &p: ops){
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}