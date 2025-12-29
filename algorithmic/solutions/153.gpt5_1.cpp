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

struct Edge {
    int idx;
    int u, v;
    int d; // rounded Euclidean distance
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 400;
    const int M = 1995;

    vector<int> x(N), y(N);
    for(int i=0;i<N;i++){
        if(!(cin >> x[i] >> y[i])) return 0;
    }

    vector<Edge> edges(M);
    for(int i=0;i<M;i++){
        int u, v;
        cin >> u >> v;
        edges[i].idx = i;
        edges[i].u = u;
        edges[i].v = v;
        long long dx = x[u] - x[v];
        long long dy = y[u] - y[v];
        double dist = sqrt((double)dx*dx + (double)dy*dy);
        edges[i].d = (int)llround(dist);
    }

    // Build initial MST using d as weights
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if(edges[a].d != edges[b].d) return edges[a].d < edges[b].d;
        return edges[a].idx < edges[b].idx;
    });

    vector<char> inTree(M, 0), accepted(M, 0);
    vector<vector<pair<int,int>>> treeAdj(N); // (neighbor, edgeId)

    DSU dsu(N);
    int added = 0;
    for(int id : order){
        if(dsu.unite(edges[id].u, edges[id].v)){
            inTree[id] = 1;
            treeAdj[edges[id].u].push_back({edges[id].v, id});
            treeAdj[edges[id].v].push_back({edges[id].u, id});
            added++;
            if(added == N-1) break;
        }
    }

    auto removeEdgeFromTree = [&](int eid){
        int a = edges[eid].u, b = edges[eid].v;
        auto &va = treeAdj[a];
        for(size_t i=0;i<va.size();i++){
            if(va[i].second == eid){
                va[i] = va.back();
                va.pop_back();
                break;
            }
        }
        auto &vb = treeAdj[b];
        for(size_t i=0;i<vb.size();i++){
            if(vb[i].second == eid){
                vb[i] = vb.back();
                vb.pop_back();
                break;
            }
        }
    };

    auto addEdgeToTree = [&](int eid){
        int a = edges[eid].u, b = edges[eid].v;
        treeAdj[a].push_back({b, eid});
        treeAdj[b].push_back({a, eid});
    };

    auto getPathEdges = [&](int s, int t){
        vector<int> prevV(N, -1), prevE(N, -1);
        queue<int> q;
        q.push(s);
        prevV[s] = s;
        while(!q.empty()){
            int u = q.front(); q.pop();
            if(u == t) break;
            for(auto &pr : treeAdj[u]){
                int v = pr.first, eid = pr.second;
                if(prevV[v] == -1){
                    prevV[v] = u;
                    prevE[v] = eid;
                    q.push(v);
                }
            }
        }
        vector<int> path;
        if(prevV[t] == -1) return path; // should not happen
        int cur = t;
        while(cur != s){
            int e = prevE[cur];
            path.push_back(e);
            cur = prevV[cur];
        }
        return path; // from t to s (reverse order), order doesn't matter for our use
    };

    const double ALPHA = 1.0; // accept if l_i < ALPHA * 2*d(best_future_edge_on_path)

    for(int i=0;i<M;i++){
        int l;
        if(!(cin >> l)) return 0;

        bool take = false;

        if(inTree[i]){
            // Must accept to keep plan
            take = true;
            accepted[i] = 1;
        }else{
            // Consider swapping into the tree if beneficial
            int u = edges[i].u, v = edges[i].v;
            vector<int> path = getPathEdges(u, v);
            int bestEdge = -1;
            long long bestScore = -1;
            for(int eid : path){
                if(edges[eid].idx >= i){ // not yet processed (future edge)
                    long long score = 2LL * edges[eid].d;
                    if(score > bestScore){
                        bestScore = score;
                        bestEdge = eid;
                    }
                }
            }
            if(bestEdge != -1){
                // Accept if reduces expected total cost
                if((double)l < ALPHA * (double)bestScore){
                    take = true;
                    accepted[i] = 1;
                    // Update tree: remove bestEdge, add current i
                    inTree[bestEdge] = 0;
                    removeEdgeFromTree(bestEdge);
                    inTree[i] = 1;
                    addEdgeToTree(i);
                }
            }
        }

        cout << (take ? 1 : 0) << endl;
        cout.flush();
    }

    return 0;
}