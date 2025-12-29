#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    DSU(int n=0): n(n), p(n), sz(n,1) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(sz[a]<sz[b]) swap(a,b);
        p[b]=a; sz[a]+=sz[b];
        return true;
    }
};

struct Edge {
    int u, v, w;
    bool operator<(const Edge& other) const { return w < other.w; }
};

struct AdjEdge {
    int v;
    char dir;
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, si, sj;
    if(!(cin >> N >> si >> sj)) return 0;
    vector<string> c(N);
    for(int i=0;i<N;i++) cin >> c[i];

    auto inside = [&](int i,int j){ return 0<=i && i<N && 0<=j && j<N; };
    auto isRoad = [&](int i,int j){ return inside(i,j) && c[i][j] != '#'; };

    // BFS to get reachable component from (si, sj)
    vector<int> reach(N*N, 0);
    queue<pair<int,int>> q;
    if(!isRoad(si,sj)) {
        cout << "\n";
        return 0;
    }
    reach[si*N+sj]=1;
    q.push({si,sj});
    int dr[4]={-1,1,0,0};
    int dc[4]={0,0,-1,1};
    while(!q.empty()){
        auto [i,j]=q.front(); q.pop();
        for(int d=0; d<4; d++){
            int ni=i+dr[d], nj=j+dc[d];
            if(isRoad(ni,nj)){
                int id = ni*N+nj;
                if(!reach[id]){
                    reach[id]=1;
                    q.push({ni,nj});
                }
            }
        }
    }

    // Build edges between adjacent reachable cells with cost w[u]+w[v]
    auto weightOf = [&](int i,int j){ return c[i][j]-'0'; };
    vector<Edge> edges;
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            if(!isRoad(i,j)) continue;
            int u = i*N + j;
            if(!reach[u]) continue;
            if(inside(i, j+1) && isRoad(i, j+1) && reach[i*N + (j+1)]){
                int v = i*N + (j+1);
                int w = weightOf(i,j) + weightOf(i,j+1);
                edges.push_back({u,v,w});
            }
            if(inside(i+1, j) && isRoad(i+1, j) && reach[(i+1)*N + j]){
                int v = (i+1)*N + j;
                int w = weightOf(i,j) + weightOf(i+1,j);
                edges.push_back({u,v,w});
            }
        }
    }

    // Kruskal to get MST over reachable nodes
    DSU dsu(N*N);
    sort(edges.begin(), edges.end());
    vector<vector<AdjEdge>> adj(N*N);
    auto dirFromTo = [&](int u, int v)->char{
        int ui=u/N, uj=u%N, vi=v/N, vj=v%N;
        if(vi==ui){
            if(vj==uj+1) return 'R';
            else return 'L';
        }else{
            if(vi==ui+1) return 'D';
            else return 'U';
        }
    };
    for(const auto& e: edges){
        if(dsu.unite(e.u, e.v)){
            char d1 = dirFromTo(e.u, e.v);
            char d2;
            if(d1=='U') d2='D';
            else if(d1=='D') d2='U';
            else if(d1=='L') d2='R';
            else d2='L';
            adj[e.u].push_back({e.v, d1});
            adj[e.v].push_back({e.u, d2});
        }
    }

    // Iterative DFS on MST to produce route that returns to start
    auto opp = [&](char ch)->char{
        if(ch=='U') return 'D';
        if(ch=='D') return 'U';
        if(ch=='L') return 'R';
        return 'L';
    };

    int start = si*N + sj;
    vector<char> visited(N*N, 0);
    struct Node { int u; int ptr; char inMove; };
    vector<Node> st;
    visited[start]=1;
    st.push_back({start, 0, 'X'});

    // Count reachable nodes to reserve size
    int rc = 0;
    for(int x: reach) if(x) rc++;
    string ans;
    ans.reserve(max(0, 2*rc - 2));

    while(true){
        Node &cur = st.back();
        int u = cur.u;
        bool moved = false;
        while(cur.ptr < (int)adj[u].size()){
            int idx = cur.ptr++;
            int v = adj[u][idx].v;
            if(!visited[v]){
                visited[v]=1;
                char d = adj[u][idx].dir;
                ans.push_back(d);
                st.push_back({v, 0, d});
                moved = true;
                break;
            }
        }
        if(!moved){
            if(st.size()==1) break;
            Node last = st.back();
            st.pop_back();
            ans.push_back(opp(last.inMove));
        }
    }

    cout << ans << '\n';
    return 0;
}