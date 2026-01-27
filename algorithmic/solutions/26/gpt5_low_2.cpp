#include <bits/stdc++.h>
using namespace std;

struct BIT {
    int n;
    vector<int> f;
    BIT(int n): n(n), f(n+1,0) {}
    void add(int i,int v){ for(; i<=n; i+=i&-i) f[i]+=v; }
    int sum(int i){ int s=0; for(; i>0; i-=i&-i) s+=f[i]; return s; }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin>>n)) return 0;
    vector<int> v(n+1), pos(n+1);
    for(int i=1;i<=n;i++){ cin>>v[i]; pos[v[i]]=i; }
    BIT bit(n);
    vector<pair<long long,long long>> moves;
    long long totalY = 0;
    for(int i=1;i<=n;i++){
        int p = pos[i];
        int placedBefore = bit.sum(p);
        long long x = (long long)(i-1) + (long long)(p - placedBefore);
        long long y = i;
        if(x != y){
            moves.emplace_back(x, y);
            totalY += y;
        }
        bit.add(p,1);
    }
    long long k = (long long)moves.size();
    long long final_cost = (totalY + 1) * (k + 1);
    cout << final_cost << " " << k << "\n";
    for(auto &mv : moves){
        cout << mv.first << " " << mv.second << "\n";
    }
    return 0;
}