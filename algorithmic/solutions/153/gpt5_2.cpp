#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU() {}
    DSU(int n): n(n), p(n), r(n,0) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool same(int a,int b){ return find(a)==find(b); }
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
    int u, v, d;
};

static const int N_fixed = 400;
static const int M_fixed = 1995;

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = N_fixed;
    const int M = M_fixed;

    vector<pair<int,int>> coord(N);
    for(int i=0;i<N;i++){
        int x,y;
        if(!(cin>>x>>y)) return 0;
        coord[i]={x,y};
    }

    vector<Edge> edges(M);
    vector<vector<int>> inc(N);
    for(int i=0;i<M;i++){
        int u,v; cin>>u>>v;
        int dx = coord[u].first - coord[v].first;
        int dy = coord[u].second - coord[v].second;
        int d = (int)llround(sqrt((double)dx*dx + (double)dy*dy));
        edges[i] = {u,v,d};
        inc[u].push_back(i);
        inc[v].push_back(i);
    }

    // Precompute MST on d to label edges that are in some MST of given graph
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int a, int b){
        if(edges[a].d != edges[b].d) return edges[a].d < edges[b].d;
        return a < b;
    });
    vector<char> inMST(M, 0);
    {
        DSU dsu_mst(N);
        int used = 0;
        for(int id: idx){
            if(dsu_mst.unite(edges[id].u, edges[id].v)){
                inMST[id] = 1;
                used++;
                if(used == N-1) break;
            }
        }
    }

    vector<char> accepted(M, 0);

    auto connected_after_reject = [&](int currIdx)->bool{
        // Graph: accepted edges (any index) OR edges with index > currIdx
        vector<char> vis(N, 0);
        deque<int> dq;
        vis[0] = 1;
        dq.push_back(0);
        while(!dq.empty()){
            int u = dq.front(); dq.pop_front();
            for(int ei : inc[u]){
                if(ei <= currIdx){
                    if(!accepted[ei]) continue;
                }
                // ei > currIdx is active OR accepted[ei] is true for ei <= currIdx
                int w = edges[ei].u ^ edges[ei].v ^ u;
                if(!vis[w]){
                    vis[w] = 1;
                    dq.push_back(w);
                }
            }
        }
        for(int i=0;i<N;i++) if(!vis[i]) return false;
        return true;
    };

    DSU dsu(N);

    for(int i=0;i<M;i++){
        int li;
        if(!(cin>>li)) return 0;

        int u = edges[i].u, v = edges[i].v;
        bool ans = false;

        if(dsu.same(u, v)){
            ans = false;
        } else {
            // Forced acceptance to maintain possibility of connectivity
            bool forced = !connected_after_reject(i);
            if(forced){
                ans = true;
            } else {
                double p = (double)i / (double)M;
                double tauBase = 1.25 + 1.65 * pow(p, 1.25);
                if(tauBase > 2.9) tauBase = 2.9;
                double r = (double)li / (double)edges[i].d;

                bool take = false;
                if(r <= tauBase) take = true;

                double tauMst = min(2.95, tauBase + 0.15);
                if(!take && inMST[i] && r <= tauMst) take = true;

                if(!take){
                    // Additional heuristic using best d across current components
                    int ca = dsu.find(u), cb = dsu.find(v);
                    int bestd = INT_MAX;
                    for(int j=0;j<M;j++){
                        int a = dsu.find(edges[j].u);
                        int b = dsu.find(edges[j].v);
                        if((a==ca && b==cb) || (a==cb && b==ca)){
                            if(edges[j].d < bestd) bestd = edges[j].d;
                        }
                    }
                    if(bestd < INT_MAX){
                        double tauMin = max(1.1, tauBase - 0.05);
                        if((double)li <= tauMin * (double)bestd) take = true;
                    }
                }

                ans = take;
            }
        }

        if(ans){
            accepted[i] = 1;
            dsu.unite(u, v);
        }
        cout << (ans ? 1 : 0) << '\n' << flush;
    }

    return 0;
}