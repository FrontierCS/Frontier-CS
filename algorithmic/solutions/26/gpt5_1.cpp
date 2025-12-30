#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
    int n;
    vector<int> bit;
    Fenwick(int n=0): n(n), bit(n+1,0) {}
    void init(int n_) { n = n_; bit.assign(n+1,0); }
    void add(int idx, int delta){ for(; idx<=n; idx+=idx&-idx) bit[idx]+=delta; }
    int sum(int idx){ int s=0; for(; idx>0; idx-=idx&-idx) s+=bit[idx]; return s; }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    vector<int> v(n+1), pos(n+1);
    for(int i=1;i<=n;i++){
        cin >> v[i];
        pos[v[i]] = i;
    }
    
    int t = n;
    while(t > 1 && pos[t-1] < pos[t]) --t; // keep suffix [t..n]
    
    Fenwick fw(n);
    for(int i=1;i<=n;i++) fw.add(i,1);
    
    vector<pair<int,int>> moves;
    moves.reserve(max(0, t-1));
    int moved = 0;
    for(int val = t-1; val >= 1; --val){
        int x = moved + fw.sum(pos[val]);
        int y = 1;
        moves.emplace_back(x, y);
        fw.add(pos[val], -1);
        moved++;
    }
    
    long long sum_y = 0;
    for(auto &p: moves) sum_y += p.second;
    long long k = (long long)moves.size();
    long long final_cost = (sum_y + 1) * (k + 1);
    
    cout << final_cost << " " << moves.size() << "\n";
    for(auto &p: moves){
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}