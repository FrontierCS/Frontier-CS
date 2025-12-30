#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, r;
    DSU(int n=0): n(n), p(n), r(n,0) { iota(p.begin(), p.end(), 0); }
    int find(int x){ return p[x]==x? x : p[x]=find(p[x]); }
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
    int N, si, sj;
    if(!(cin >> N >> si >> sj)) return 0;
    vector<string> grid(N);
    for(int i=0;i<N;i++) cin >> grid[i];

    auto inb = [&](int i,int j){ return 0<=i && i<N && 0<=j && j<N; };

    vector<int> id(N*N, -1);
    vector<int> ri, rj, w;
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            if(grid[i][j] != '#'){
                int idx = (int)ri.size();
                id[i*N + j] = idx;
                ri.push_back(i);
                rj.push_back(j);
                w.push_back(grid[i][j]-'0');
            }
        }
    }
    int R = (int)ri.size();
    if(R==0){
        cout << "\n";
        return 0;
    }
    int root = id[si*N + sj];

    struct Edge{ int u,v,c; };
    vector<Edge> edges;
    edges.reserve(2*R);
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            int u = id[i*N + j];
            if(u<0) continue;
            if(i+1<N){
                int v = id[(i+1)*N + j];
                if(v>=0) edges.push_back({u,v,w[u]+w[v]});
            }
            if(j+1<N){
                int v = id[i*N + (j+1)];
                if(v>=0) edges.push_back({u,v,w[u]+w[v]});
            }
        }
    }
    sort(edges.begin(), edges.end(), [](const Edge& a, const Edge& b){
        if(a.c!=b.c) return a.c<b.c;
        if(a.u!=b.u) return a.u<b.u;
        return a.v<b.v;
    });

    vector<vector<int>> adj(R);
    DSU dsu(R);
    int added = 0;
    for(const auto& e: edges){
        if(dsu.unite(e.u, e.v)){
            adj[e.u].push_back(e.v);
            adj[e.v].push_back(e.u);
            if(++added == R-1) break;
        }
    }

    auto dir = [&](int u, int v)->char{
        int di = ri[v]-ri[u];
        int dj = rj[v]-rj[u];
        if(di==1 && dj==0) return 'D';
        if(di==-1 && dj==0) return 'U';
        if(di==0 && dj==1) return 'R';
        if(di==0 && dj==-1) return 'L';
        return 'U'; // should not happen
    };
    auto inv = [&](char c)->char{
        if(c=='U') return 'D';
        if(c=='D') return 'U';
        if(c=='L') return 'R';
        return 'L';
    };

    vector<int> idx(R,0), parent(R,-1);
    vector<char> parentDir(R,'?');
    vector<char> ans;
    ans.reserve(max(0, 2*(R-1)));

    vector<char> vis(R, 0);
    vis[root]=1;
    vector<int> st;
    st.push_back(root);

    while(!st.empty()){
        int u = st.back();
        if(idx[u] < (int)adj[u].size()){
            int v = adj[u][ idx[u]++ ];
            if(v == parent[u]) continue;
            if(!vis[v]){
                char d = dir(u, v);
                ans.push_back(d);
                vis[v]=1;
                parent[v]=u;
                parentDir[v]=d;
                st.push_back(v);
            }
        }else{
            st.pop_back();
            if(!st.empty()){
                ans.push_back(inv(parentDir[u]));
            }
        }
    }

    string out(ans.begin(), ans.end());
    cout << out << '\n';
    return 0;
}