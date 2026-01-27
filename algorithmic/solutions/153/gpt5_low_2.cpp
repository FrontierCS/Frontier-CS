#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n): n(n), p(n), r(n,0) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        return true;
    }
    bool same(int a,int b){ return find(a)==find(b); }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 400;
    const int M = 1995;

    vector<pair<int,int>> coord(N);
    for(int i=0;i<N;i++){
        int x,y;
        if(!(cin>>x>>y)) return 0;
        coord[i]={x,y};
    }
    vector<pair<int,int>> edges(M);
    for(int i=0;i<M;i++){
        int u,v; 
        cin>>u>>v;
        edges[i]={u,v};
    }

    DSU dsu(N);
    for(int i=0;i<M;i++){
        long long li;
        if(!(cin>>li)) return 0;
        int u = edges[i].first, v = edges[i].second;
        bool take = !dsu.same(u,v);
        if(take) dsu.unite(u,v);
        cout << (take?1:0) << endl;
    }
    return 0;
}