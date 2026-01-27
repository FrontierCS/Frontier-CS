#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n=0): n(n), p(n), r(n,0){ iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a, int b){
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
    struct Edge{int u,v; long long w; int idx;};
    vector<Edge> edges(M);
    for(int j=0;j<M;j++){
        int u,v; long long w;
        cin>>u>>v>>w;
        --u;--v;
        edges[j]={u,v,w,j};
    }
    // read residents (unused)
    for(int k=0;k<K;k++){
        long long a,b; cin>>a>>b;
    }
    // Kruskal to connect all vertices
    vector<int> B(M,0);
    DSU dsu(N);
    vector<Edge> ord = edges;
    sort(ord.begin(), ord.end(), [](const Edge& a, const Edge& b){
        if(a.w!=b.w) return a.w<b.w;
        return a.idx<b.idx;
    });
    int cnt=0;
    for(auto &e: ord){
        if(dsu.unite(e.u, e.v)){
            B[e.idx]=1;
            cnt++;
            if(cnt==N-1) break;
        }
    }
    // Output strengths: 5000 for all vertices
    for(int i=0;i<N;i++){
        if(i) cout<<' ';
        cout<<5000;
    }
    cout<<"\n";
    for(int j=0;j<M;j++){
        if(j) cout<<' ';
        cout<<B[j];
    }
    cout<<"\n";
    return 0;
}