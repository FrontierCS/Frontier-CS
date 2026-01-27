#include <bits/stdc++.h>
using namespace std;

// This is a heuristic construction that tries to realize all edges using a 1D word S,
// and then replicates S on all rows so vertical adjacencies are same-color only.
// It builds S by creating, for each connected component, an Eulerian-like trail on the
// "edge graph" (edges are nodes; adjacency if they share an endpoint). If components > 1,
// it separates them by long runs of the same vertex and attempts to avoid cross-component
// non-edges by ensuring boundaries are equal colors (same-color adjacency).
// If it cannot, it falls back to a trivial K=N map with constant rows (may be invalid for some graphs).

static vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    vector<vector<int>> adj(N+1);
    vector<int> deg(N+1, 0);
    for (int i = 0; i < M; ++i) {
        adj[A[i]].push_back(B[i]);
        adj[B[i]].push_back(A[i]);
        deg[A[i]]++; deg[B[i]]++;
    }

    // Build components
    vector<int> comp_id(N+1, -1);
    int compcnt = 0;
    for (int u = 1; u <= N; ++u) if (comp_id[u] == -1) {
        queue<int> q;
        comp_id[u] = compcnt;
        q.push(u);
        while(!q.empty()){
            int x = q.front(); q.pop();
            for(int v: adj[x]){
                if(comp_id[v]==-1){
                    comp_id[v]=compcnt;
                    q.push(v);
                }
            }
        }
        compcnt++;
    }

    // For each component, build a sequence over its vertices whose adjacent distinct pairs
    // are exactly the edges in that component. We attempt to create a trail over edges.
    // We use Hierholzer-like traversal on the vertex graph to get an Euler trail by doubling edges if needed.
    // To ensure existence, we duplicate edges to make all degrees even (construct multigraph with each edge twice),
    // then Euler cycle exists in each connected component with at least one edge. From the Euler cycle sequence of vertices,
    // adjacent pairs are edges of the multigraph, i.e., original edges, no non-edges.
    // For isolated vertices (deg=0), just a single occurrence of that vertex in its own component.

    vector<vector<int>> comp_vertices(compcnt);
    for(int u=1; u<=N; ++u) comp_vertices[comp_id[u]].push_back(u);

    vector<vector<int>> sequences; // one sequence per component
    for(int c=0; c<compcnt; ++c){
        // collect edges in this component
        vector<pair<int,int>> edges;
        unordered_map<long long,int> mult; // count occurrences
        auto key = [&](int x,int y)->long long{
            if(x>y) swap(x,y);
            return (long long)x<<20 | y;
        };
        for(int u: comp_vertices[c]){
            for(int v: adj[u]){
                if(u < v && comp_id[v]==c){
                    edges.emplace_back(u,v);
                    mult[key(u,v)] = 2; // duplicate edge to make degrees even
                }
            }
        }
        if(edges.empty()){
            // isolated vertices in this component (there may be multiple). Build sequence listing them with repeats to avoid cross pairs.
            // Single vertex per component suffice.
            sequences.push_back({comp_vertices[c][0]});
            continue;
        }
        // Build multigraph adjacency with duplicated edges
        unordered_map<long long,int> rem = mult;
        unordered_map<int, vector<int>> g;
        for(auto &e: edges){
            int u=e.first,v=e.second;
            g[u].push_back(v);
            g[u].push_back(v);
            g[v].push_back(u);
            g[v].push_back(u);
        }
        // Hierholzer
        vector<int> seq;
        // find starting vertex with non-zero degree
        int start = edges[0].first;
        // iterative stack
        unordered_map<long long,int> used; used.reserve(rem.size()*2);
        vector<int> st; st.push_back(start);
        vector<int> path;
        // For adjacency iteration, we need to remove used edges counts; we'll use rem map.
        while(!st.empty()){
            int v = st.back();
            // find neighbor with remaining edge
            bool advanced=false;
            auto &nbrs = g[v];
            while(!nbrs.empty()){
                int u = nbrs.back(); nbrs.pop_back();
                long long k = key(v,u);
                auto it = rem.find(k);
                if(it!=rem.end() && it->second>0){
                    it->second--;
                    st.push_back(u);
                    advanced=true;
                    break;
                }
            }
            if(!advanced){
                path.push_back(v);
                st.pop_back();
            }
        }
        if(path.size()<2){
            sequences.push_back({start});
        }else{
            // path is Eulerian circuit; convert to sequence of vertices
            reverse(path.begin(), path.end());
            // path vertices; adjacent distinct pairs are edges
            sequences.push_back(path);
        }
    }

    // Build global sequence S by concatenating component sequences with separators of repeated last symbol to avoid cross-component non-edges.
    // We will put between components a very long run of the last symbol of previous, then same symbol again (no change), and then we need to switch to the first of next component.
    // This creates a boundary pair (prev_last, next_first). To avoid non-edge at the boundary, we force prev_last == next_first by rotating the next sequence if possible.
    // For components with at least one edge (sequence length >=2), we can rotate cycle to start at any vertex; for paths, we can choose start equal to some vertex; but not guaranteed to match previous.
    // As a heuristic, we try to reorder components and rotate their sequences to make boundaries either same vertex or an existing edge; if not possible, we will fall back.

    // Preprocess: For sequences length >=2 (Eulerian), it's a cycle (first == last). We can rotate freely without changing set of adjacent pairs.
    // For sequences length ==1, it's an isolated vertex.
    int C = sequences.size();
    vector<int> usedComp(C,0);
    vector<int> order;
    // Greedy: start with a component having length>=2 if exists
    int startComp = 0;
    for(int i=0;i<C;i++){
        if((int)sequences[i].size()>=2){ startComp=i; break; }
    }
    // simple order as is
    for(int i=0;i<C;i++) order.push_back(i);

    // Try to rotate to align boundaries
    auto rotate_to_start = [&](vector<int> &vec, int val)->bool{
        int n=vec.size();
        for(int i=0;i<n;i++){
            if(vec[i]==val){
                rotate(vec.begin(), vec.begin()+i, vec.end());
                return true;
            }
        }
        return false;
    };

    vector<int> S;
    bool ok = true;
    for(int idx=0; idx<C; ++idx){
        int ci = order[idx];
        auto seq = sequences[ci];
        if(S.empty()){
            // Append seq
            for(int x: seq) S.push_back(x);
        }else{
            int prev = S.back();
            // Try to rotate seq so that first equals prev (safe boundary)
            bool aligned=false;
            if(seq.size()>=2){
                // For Eulerian cycle, ensure it's cyclic: first == last; our constructed path might have first==last. If not, we can make it cyclic by appending first at end if edge exists? We'll keep as is.
                // Try to find prev in seq and rotate.
                if(rotate_to_start(seq, prev)){
                    aligned=true;
                }
            }else{
                // single vertex
                if(seq[0]==prev) aligned=true;
            }
            if(!aligned){
                // Try if (prev, seq[0]) is an existing edge; if yes, boundary is valid
                bool isEdge=false;
                for(int v: adj[prev]) if(v==seq[0]) { isEdge=true; break; }
                if(!isEdge){
                    ok=false;
                    break;
                }
            }
            // Append with no separator
            for(int x: seq) S.push_back(x);
        }
    }

    if(!ok){
        // Fallback: trivial N x N constant rows (may be invalid, but we must return something)
        int K = max(1, N);
        vector<vector<int>> Cmap(K, vector<int>(K, 1));
        for(int i=0;i<K;i++){
            for(int j=0;j<K;j++){
                Cmap[i][j] = i%N + 1;
            }
        }
        return Cmap;
    }

    // Ensure all colors appear at least once; if not, append them with runs that do not create new adjacencies:
    vector<int> seen(N+1,0);
    for(int x: S) seen[x]=1;
    for(int c=1;c<=N;c++){
        if(!seen[c]){
            // Append c with a preceding same c to avoid boundary pair, then a same c after.
            // Boundary between S.back() and c: to avoid non-edge, if S.back()==c it's fine; else check if (S.back(), c) is an edge; if not, we cannot append safely.
            if(!S.empty()){
                int prev=S.back();
                if(prev!=c){
                    bool isEdge=false;
                    for(int v: adj[prev]) if(v==c){ isEdge=true; break; }
                    if(!isEdge){
                        // Insert c earlier not possible; give up to fallback
                        int K = max(1, N);
                        vector<vector<int>> Cmap(K, vector<int>(K, 1));
                        for(int i=0;i<K;i++){
                            for(int j=0;j<K;j++){
                                Cmap[i][j] = i%N + 1;
                            }
                        }
                        return Cmap;
                    }
                }
            }
            S.push_back(c);
        }
    }

    int K = (int)S.size();
    if(K>240) K = min(240, K);
    // Build KxK grid: all rows equal to S[0..K-1], truncated/padded
    vector<vector<int>> Cmap(K, vector<int>(K, S[0]));
    for(int i=0;i<K;i++){
        for(int j=0;j<K;j++){
            Cmap[i][j] = S[j%S.size()];
        }
    }
    return Cmap;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if(!(cin>>T)) return 0;
    while(T--){
        int N,M; cin>>N>>M;
        vector<int> A(M), B(M);
        for(int i=0;i<M;i++){ cin>>A[i]>>B[i]; }
        auto C = create_map(N,M,A,B);
        int P = (int)C.size();
        cout<<P<<"\n";
        for(int i=0;i<P;i++){
            cout<<C[i].size()<<(i+1==P?'\n':' ');
        }
        for(int i=0;i<P;i++){
            for(int j=0;j<(int)C[i].size();j++){
                if(j) cout<<" ";
                cout<<C[i][j];
            }
            cout<<"\n";
        }
    }
    return 0;
}