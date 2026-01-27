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
    struct Edge { int u,v,d,idx; };
    vector<Edge> edges(M);
    vector<int> eu(M), ev(M), dd(M);
    for(int i=0;i<M;i++){
        int u,v;
        cin>>u>>v;
        eu[i]=u; ev[i]=v;
        long long dx = x[u]-x[v];
        long long dy = y[u]-y[v];
        int d = (int)llround(sqrt((double)(dx*dx + dy*dy)));
        dd[i]=d;
        edges[i]={u,v,d,i};
    }

    // Compute MST using d as weight
    vector<char> in_mst(M, 0);
    DSU dsu(N);
    vector<Edge> sorted = edges;
    sort(sorted.begin(), sorted.end(), [](const Edge& a, const Edge& b){
        if(a.d != b.d) return a.d < b.d;
        return a.idx < b.idx;
    });
    int picked = 0;
    for(auto &e: sorted){
        if(dsu.unite(e.u, e.v)){
            in_mst[e.idx] = 1;
            picked++;
            if(picked == N-1) break;
        }
    }

    // Online process
    DSU live(N);
    for(int i=0;i<M;i++){
        int li;
        if(!(cin>>li)) return 0;
        if(in_mst[i]){
            // Should always connect different components
            live.unite(eu[i], ev[i]);
            cout << 1 << endl;
        }else{
            cout << 0 << endl;
        }
        cout.flush();
    }
    return 0;
}