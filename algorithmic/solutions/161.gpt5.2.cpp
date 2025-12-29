#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n=0){ init(n); }
    void init(int n_) {
        n = n_;
        p.resize(n+1);
        r.assign(n+1, 0);
        iota(p.begin(), p.end(), 0);
    }
    int find(int a){ return p[a]==a?a:p[a]=find(p[a]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        return true;
    }
};

struct Edge {
    int u,v,idx;
    long long w;
};

static inline long long sqll(long long x){ return x*x; }

static inline int isqrt_ceil_ll(long long x){
    if(x <= 0) return 0;
    long long r = (long long)floor(sqrt((long double)x));
    while(r*r < x) ++r;
    while((r-1) > 0 && (r-1)*(r-1) >= x) --r;
    if(r > 5000) r = 5000;
    return (int)r;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, K;
    cin >> N >> M >> K;
    vector<int> x(N+1), y(N+1);
    for(int i=1;i<=N;i++) cin >> x[i] >> y[i];

    vector<int> U(M+1), V(M+1);
    vector<long long> W(M+1);
    vector<Edge> edges;
    edges.reserve(M);
    for(int j=1;j<=M;j++){
        cin >> U[j] >> V[j] >> W[j];
        edges.push_back({U[j], V[j], j, W[j]});
    }

    vector<int> a(K), b(K);
    for(int k=0;k<K;k++) cin >> a[k] >> b[k];

    // Build MST by edge weight
    sort(edges.begin(), edges.end(), [](const Edge& e1, const Edge& e2){
        if(e1.w != e2.w) return e1.w < e2.w;
        return e1.idx < e2.idx;
    });
    DSU dsu(N);
    vector<int> B(M+1, 0);
    int taken = 0;
    for(const auto &e : edges){
        if(dsu.unite(e.u, e.v)){
            B[e.idx] = 1;
            if(++taken == N-1) break;
        }
    }
    // Graph is connected, so MST should have N-1 edges.

    // Assign each resident to its nearest vertex, set P_i as max required radius.
    vector<int> P(N+1, 0);
    for(int k=0;k<K;k++){
        long long bestD2 = (1LL<<62);
        int bestV = 1;
        for(int i=1;i<=N;i++){
            long long dx = (long long)x[i] - a[k];
            long long dy = (long long)y[i] - b[k];
            long long d2 = dx*dx + dy*dy;
            if(d2 < bestD2){
                bestD2 = d2;
                bestV = i;
            }
        }
        int r = isqrt_ceil_ll(bestD2);
        if(r > P[bestV]) P[bestV] = r;
    }

    for(int i=1;i<=N;i++){
        if(i>1) cout << ' ';
        cout << P[i];
    }
    cout << "\n";

    for(int j=1;j<=M;j++){
        if(j>1) cout << ' ';
        cout << B[j];
    }
    cout << "\n";

    return 0;
}