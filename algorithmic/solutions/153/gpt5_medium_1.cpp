#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, rnk;
    int comps;
    DSU() {}
    DSU(int n): n(n), p(n), rnk(n,0), comps(n) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(rnk[a]<rnk[b]) swap(a,b);
        p[b]=a;
        if(rnk[a]==rnk[b]) rnk[a]++;
        comps--;
        return true;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int DEFAULT_N = 400;
    const int DEFAULT_M = 1995;

    int N = DEFAULT_N, M = DEFAULT_M;

    vector<int> xs, ys;
    xs.reserve(DEFAULT_N);
    ys.reserve(DEFAULT_N);

    // Read first two integers to determine format
    long long a, b;
    if(!(cin >> a >> b)) return 0;
    if (b > 800) {
        // Assume it's N M
        N = (int)a;
        M = (int)b;
        xs.resize(N);
        ys.resize(N);
        for(int i=0;i<N;i++){
            int xi, yi; cin >> xi >> yi;
            xs[i]=xi; ys[i]=yi;
        }
    } else {
        // Assume it's x0 y0
        xs.resize(N);
        ys.resize(N);
        xs[0] = (int)a; ys[0]=(int)b;
        for(int i=1;i<N;i++){
            int xi, yi; cin >> xi >> yi;
            xs[i]=xi; ys[i]=yi;
        }
    }

    vector<pair<int,int>> edges(M);
    for(int i=0;i<M;i++){
        int u,v; cin >> u >> v;
        edges[i]={u,v};
    }

    auto rounded_dist = [&](int u, int v)->int{
        long long dx = xs[u]-xs[v];
        long long dy = ys[u]-ys[v];
        double d = sqrt((double)dx*dx + (double)dy*dy);
        return (int)llround(d);
    };

    vector<int> base_d(M);
    for(int i=0;i<M;i++){
        base_d[i] = rounded_dist(edges[i].first, edges[i].second);
        if (base_d[i] <= 0) base_d[i] = 1;
    }

    DSU dsu(N);

    for(int i=0;i<M;i++){
        long long li;
        if(!(cin >> li)) return 0;

        int u = edges[i].first;
        int v = edges[i].second;
        int fu = dsu.find(u), fv = dsu.find(v);
        int decision = 0;

        if(fu == fv){
            decision = 0;
        } else {
            // Feasibility check: simulate with future edges only
            DSU tmp = dsu;
            int merges_future = 0;
            for(int t=i+1;t<M;t++){
                merges_future += tmp.unite(edges[t].first, edges[t].second) ? 1 : 0;
            }
            int needed = dsu.comps - 1;
            if (merges_future < needed) {
                // Must accept to ensure connectivity
                decision = 1;
                dsu.unite(u, v);
            } else {
                // Heuristic threshold based on slack
                int slack = merges_future - needed;
                double low = 1.3;
                double high = 1.8;
                int s = max(0, min(10, slack));
                double thr = low + (high - low) * (10 - s) / 10.0; // slack big -> closer to low
                double limit = thr * (double)base_d[i];
                if ((double)li <= limit) {
                    decision = 1;
                    dsu.unite(u, v);
                } else {
                    decision = 0;
                }
            }
        }

        cout << decision << '\n' << flush;
    }

    return 0;
}