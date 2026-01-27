#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n=0): n(n), p(n), r(n,0) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a, int b){
        a = find(a); b = find(b);
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
    int N, M, K;
    if(!(cin >> N >> M >> K)) return 0;
    vector<long long> x(N), y(N);
    for(int i=0;i<N;i++){
        cin >> x[i] >> y[i];
    }
    struct Edge { int u,v,idx; long long w; };
    vector<Edge> edges(M);
    for(int j=0;j<M;j++){
        int u,v; long long w;
        cin >> u >> v >> w;
        --u; --v;
        edges[j] = {u,v,j,w};
    }
    vector<long long> a(K), b(K);
    for(int k=0;k<K;k++){
        cin >> a[k] >> b[k];
    }
    // Build MST
    vector<int> B(M,0);
    vector<Edge> sorted = edges;
    sort(sorted.begin(), sorted.end(), [](const Edge& A, const Edge& B){ 
        if(A.w != B.w) return A.w < B.w; 
        return A.idx < B.idx; 
    });
    DSU dsu(N);
    int added = 0;
    for(auto &e: sorted){
        if(dsu.unite(e.u, e.v)){
            B[e.idx] = 1;
            added++;
            if(added == N-1) break;
        }
    }
    // Compute P_i: assign each resident to nearest station
    auto ceil_sqrt = [](long long s)->int{
        if(s <= 0) return 0;
        long long r = sqrt((long double)s);
        while(r*r < s) ++r;
        while((r-1)>=0 && (r-1)*(r-1) >= s) --r;
        return (int)r;
    };
    vector<int> P(N, 0);
    for(int k=0;k<K;k++){
        long long bestDist = LLONG_MAX;
        int bestIdx = 0;
        for(int i=0;i<N;i++){
            long long dx = a[k] - x[i];
            long long dy = b[k] - y[i];
            long long d2 = dx*dx + dy*dy;
            if(d2 < bestDist){
                bestDist = d2;
                bestIdx = i;
            }
        }
        int r = ceil_sqrt(bestDist);
        if(r > 5000) r = 5000; // safety clamp
        if(r > P[bestIdx]) P[bestIdx] = r;
    }
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