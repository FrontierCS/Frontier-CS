#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
    int n;
    vector<int> bit;
    Fenwick(int n=0): n(n), bit(n+1,0) {}
    void init(int n_) { n = n_; bit.assign(n+1,0); }
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
    if(!(cin >> n)) return 0;
    vector<int> v(n+1), pos(n+1);
    for(int i=1;i<=n;i++){
        cin >> v[i];
        pos[v[i]] = i;
    }
    Fenwick fw(n);
    for(int i=1;i<=n;i++) fw.add(i,1);
    vector<pair<int,int>> moves;
    moves.reserve(n);
    long long sumY = 0;
    int m = 0; // number of moved elements so far
    for(int val = n; val >= 1; --val){
        int p = pos[val];
        int rankRem = fw.sum(p);
        int x = m + rankRem;
        int y = 1;
        moves.emplace_back(x, y);
        sumY += y;
        fw.add(p, -1);
        m++;
    }
    long long k = (long long)moves.size();
    long long final_cost = (sumY + 1LL) * (k + 1LL);
    cout << final_cost << " " << moves.size() << "\n";
    for(auto &mv : moves){
        cout << mv.first << " " << mv.second << "\n";
    }
    return 0;
}