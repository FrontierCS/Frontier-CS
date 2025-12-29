#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n, comps;
    vector<int> p, r;
    DSU(int n=0): n(n), comps(n), p(n), r(n,0) {
        iota(p.begin(), p.end(), 0);
    }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a, int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        comps--;
        return true;
    }
    bool same(int a, int b){ return find(a)==find(b); }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N_default = 400, M_default = 1995;
    long long a, b;
    if(!(cin >> a >> b)) return 0;
    int N, M;
    bool firstIsNM = (a > 800 || b > 800);
    vector<pair<int,int>> coords;
    if(firstIsNM){
        N = (int)a; M = (int)b;
        coords.resize(N);
        for(int i=0;i<N;i++){
            int x,y; cin>>x>>y;
            coords[i]={x,y};
        }
    }else{
        N = N_default; M = M_default;
        coords.resize(N);
        coords[0] = {(int)a, (int)b};
        for(int i=1;i<N;i++){
            int x,y; cin>>x>>y;
            coords[i]={x,y};
        }
    }
    vector<int> U(M), V(M);
    for(int i=0;i<M;i++){
        int u,v; cin>>u>>v;
        U[i]=u; V[i]=v;
    }

    DSU dsu(N);
    for(int i=0;i<M;i++){
        int l;
        if(!(cin>>l)) l=0; // just in case
        int u = U[i], v = V[i];
        if(!dsu.same(u,v)){
            cout << 1 << "\n" << flush;
            dsu.unite(u,v);
        }else{
            cout << 0 << "\n" << flush;
        }
    }
    return 0;
}