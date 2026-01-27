#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n=0): n(n), p(n), r(n,0) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        return true;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 400;
    const int M = 1995;

    vector<int> x(N), y(N);
    for(int i=0;i<N;i++){
        if(!(cin>>x[i]>>y[i])) return 0;
    }
    vector<int> u(M), v(M);
    for(int i=0;i<M;i++){
        cin>>u[i]>>v[i];
    }

    DSU dsu(N);
    int taken = 0;

    for(int i=0;i<M;i++){
        int l; 
        if(!(cin>>l)) return 0;
        bool take = false;
        if(taken < N-1){
            if(dsu.unite(u[i], v[i])){
                take = true;
                taken++;
            }
        }
        cout << (take ? 1 : 0) << '\n' << flush;
    }
    return 0;
}