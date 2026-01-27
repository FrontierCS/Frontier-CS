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
    int N,M,K;
    if(!(cin>>N>>M>>K)) return 0;
    vector<long long> x(N), y(N);
    for(int i=0;i<N;i++) cin>>x[i]>>y[i];
    struct Edge {int u,v; long long w; int idx;};
    vector<Edge> edges(M);
    for(int j=0;j<M;j++){
        int u,v; long long w;
        cin>>u>>v>>w;
        --u;--v;
        edges[j]={u,v,w,j};
    }
    vector<long long> a(K), b(K);
    for(int k=0;k<K;k++) cin>>a[k]>>b[k];

    // Kruskal MST
    vector<int> B(M,0);
    DSU dsu(N);
    vector<int> ord(M);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int i, int j){
        if(edges[i].w != edges[j].w) return edges[i].w < edges[j].w;
        return edges[i].idx < edges[j].idx;
    });
    int taken = 0;
    for(int id: ord){
        if(dsu.unite(edges[id].u, edges[id].v)){
            B[edges[id].idx] = 1;
            taken++;
            if(taken == N-1) break;
        }
    }

    // Set P_i = 5000 for all vertices
    vector<int> P(N, 5000);

    // Output
    for(int i=0;i<N;i++){
        if(i) cout << ' ';
        cout << P[i];
    }
    cout << '\n';
    for(int j=0;j<M;j++){
        if(j) cout << ' ';
        cout << B[j];
    }
    cout << '\n';
    return 0;
}