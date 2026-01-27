#include <bits/stdc++.h>
using namespace std;

struct Fenwick {
    int n;
    vector<int> bit;
    Fenwick(int n=0): n(n), bit(n+1,0) {}
    void init(int n_) { n = n_; bit.assign(n+1,0); }
    void add(int idx, int delta){
        for(; idx<=n; idx+=idx&-idx) bit[idx]+=delta;
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
    // Find minimal t such that values [t..n] are in increasing order by positions
    int t = n;
    for(int i=n-1;i>=1;i--){
        if(pos[i] < pos[i+1]) t = i;
        else break;
    }
    // We will move values 1..t-1 to the front, in descending order
    Fenwick fw(n);
    for(int i=1;i<=n;i++) fw.add(i,1);
    vector<pair<int,int>> moves;
    moves.reserve(max(0, t-1));
    for(int val = t-1; val >= 1; --val){
        int x = (int)moves.size() + fw.sum(pos[val]);
        moves.emplace_back(x, 1);
        fw.add(pos[val], -1);
    }
    long long k = (long long)moves.size();
    long long final_cost = (k + 1) * (k + 1);
    cout << final_cost << " " << moves.size() << "\n";
    for(auto &mv : moves){
        cout << mv.first << " " << mv.second << "\n";
    }
    return 0;
}