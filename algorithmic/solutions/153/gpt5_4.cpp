#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    int comps;
    DSU() {}
    DSU(int n): n(n), p(n), r(n,0), comps(n) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
        comps--;
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

    vector<int> U(M), V(M), D(M);
    for(int i=0;i<M;i++){
        cin>>U[i]>>V[i];
        long long dx = x[U[i]] - x[V[i]];
        long long dy = y[U[i]] - y[V[i]];
        int d = (int)llround(sqrt((double)(dx*dx + dy*dy)));
        D[i] = d;
    }

    // Precompute MST edges by d (on given graph E)
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int a, int b){
        if(D[a]!=D[b]) return D[a] < D[b];
        if(U[a]!=U[b]) return U[a] < U[b];
        return V[a] < V[b];
    });
    DSU mst_dsu(N);
    vector<char> isMST(M, 0);
    for(int id: idx){
        if(mst_dsu.unite(U[id], V[id])) isMST[id] = 1;
    }

    // Precompute suffix connectivity groups for all i (edges j >= i)
    vector<vector<int>> suf(M+1, vector<int>(N));
    DSU suf_dsu(N);
    for(int v=0; v<N; v++) suf[M][v] = suf_dsu.find(v); // initially all separate
    for(int i=M-1; i>=0; --i){
        suf_dsu.unite(U[i], V[i]);
        for(int v=0; v<N; v++){
            suf[i][v] = suf_dsu.find(v);
        }
    }

    // Online processing
    DSU conn(N);
    int comps = N;
    vector<pair<int,int>> acceptedEdges;
    acceptedEdges.reserve(N-1);

    for(int i=0;i<M;i++){
        int l;
        if(!(cin>>l)) return 0;

        int u = U[i], v = V[i];

        // Build DSU over suffix groups using accepted edges so far
        DSU gdsu(N); // indices correspond to group ids in [0..N-1]
        for(auto &e : acceptedEdges){
            int a = suf[i+1][e.first];
            int b = suf[i+1][e.second];
            if(a!=b) gdsu.unite(a,b);
        }

        // Check if accepted edges already connect all suffix groups
        int baseRoot = gdsu.find(suf[i+1][0]);
        bool connectedByAccepted = true;
        for(int vtx=1; vtx<N; vtx++){
            if(gdsu.find(suf[i+1][vtx]) != baseRoot){
                connectedByAccepted = false;
                break;
            }
        }

        bool take = false;
        // Forced acceptance to maintain possibility
        if(!connectedByAccepted){
            int gu = gdsu.find(suf[i+1][u]);
            int gv = gdsu.find(suf[i+1][v]);
            if(gu != gv){
                // Typically this should also connect different current components
                take = true;
            }
        }

        if(!take){
            // Heuristic acceptance if it connects two current components and is "cheap"
            if(conn.find(u) != conn.find(v)){
                // progress factor
                double p_i = (double)i / (double)M;
                double p_m = (double)(N - comps) / (double)(N - 1);
                double prog = 0.6 * p_i + 0.4 * p_m;
                if(prog < 0) prog = 0;
                if(prog > 1) prog = 1;

                // thresholds
                double base_non = 1.18, final_non = 2.35;
                double base_mst = 1.28, final_mst = 2.50;
                double t;
                if(isMST[i]) t = base_mst + (final_mst - base_mst) * prog;
                else          t = base_non + (final_non - base_non) * prog;

                // slightly adjust by distance magnitude (prefer shorter)
                // scale factor: small d -> more lenient
                double dnorm = max(1, D[i]);
                double adj = 0.0;
                if(dnorm <= 50) adj = 0.12;
                else if (dnorm <= 100) adj = 0.08;
                else if (dnorm <= 200) adj = 0.04;
                else adj = 0.00;
                t += adj * (1.0 - prog);

                if(l <= t * (double)D[i]){
                    take = true;
                }
            }
        }

        if(take){
            // record and unify in connection DSU (if not already)
            acceptedEdges.emplace_back(u, v);
            if(conn.unite(u, v)){
                comps--;
            }
            cout << 1 << '\n';
        }else{
            cout << 0 << '\n';
        }
        cout.flush();
    }

    return 0;
}