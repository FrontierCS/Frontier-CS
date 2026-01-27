#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
    int n;
    vector<int> bit;
    Fenwick(int n): n(n), bit(n+1,0) {}
    void add(int idx, int val){
        for(; idx<=n; idx+=idx&-idx) bit[idx]+=val;
        }
    int sum(int idx){
        int r=0;
        for(; idx>0; idx-=idx&-idx) r+=bit[idx];
        return r;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin>>n)) return 0;
    vector<int> v(n+1), pos(n+1);
    for(int i=1;i<=n;i++){ cin>>v[i]; pos[v[i]] = i; }
    // Find longest suffix of values in correct order (values s..n with increasing positions)
    int s = n;
    int last = pos[n];
    for(int k=n-1;k>=1;k--){
        if(pos[k] < last){
            last = pos[k];
            s = k;
        } else break;
    }
    int moves = s-1;
    Fenwick fw(n);
    for(int i=1;i<=n;i++) fw.add(i,1);
    vector<pair<int,int>> ops;
    ops.reserve(moves);
    long long total_cost = 0;
    int moved = 0;
    for(int val = s-1; val >= 1; --val){
        int p = pos[val];
        int r = fw.sum(p);
        int x = moved + r;
        int y = 1;
        ops.emplace_back(x,y);
        total_cost += y;
        fw.add(p, -1);
        moved++;
    }
    long long final_cost = (total_cost + 1) * (moves + 1LL);
    cout << final_cost << " " << moves << "\n";
    for(auto &op : ops){
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}