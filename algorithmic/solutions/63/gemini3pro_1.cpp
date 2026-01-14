#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <numeric>
#include <queue>
#include <map>

using namespace std;

// Globals
int N, M;
struct Edge {
    int u, v, id;
};
vector<Edge> edges;
vector<vector<pair<int, int>>> adj; // u -> {v, edge_index}

// Helper to flush and read
int query(const vector<int>& dirs) {
    cout << "0";
    for (int d : dirs) {
        cout << " " << d;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void answer(int A, int B) {
    cout << "1 " << A << " " << B << endl;
    exit(0);
}

// Global random engine
mt19937 rng(1337);

// BFS distances
vector<int> get_dists(int root) {
    vector<int> d(N, -1);
    d[root] = 0;
    queue<int> q;
    q.push(root);
    while(!q.empty()){
        int u = q.front();
        q.pop();
        for(auto& p : adj[u]){
            int v = p.first;
            if(d[v] == -1){
                d[v] = d[u] + 1;
                q.push(v);
            }
        }
    }
    return d;
}

// Function to orient a subset of nodes to be Strongly Connected (as much as possible)
void orient_SC(const vector<int>& nodes, vector<int>& final_dirs) {
    if (nodes.empty()) return;
    
    vector<bool> in_set(N, false);
    for(int u : nodes) in_set[u] = true;

    vector<bool> visited(N, false);
    
    for(int start_node : nodes) {
        if(visited[start_node]) continue;

        vector<int> comp;
        queue<int> q;
        q.push(start_node);
        visited[start_node] = true;
        comp.push_back(start_node);
        
        while(!q.empty()){
            int u = q.front();
            q.pop();
            for(auto& p : adj[u]){
                int v = p.first;
                if(in_set[v] && !visited[v]){
                    visited[v] = true;
                    q.push(v);
                    comp.push_back(v);
                }
            }
        }

        // BFS to determine levels for tree/back edges
        queue<int> bfs_q;
        bfs_q.push(comp[0]);
        map<int, int> level;
        for(int u : comp) level[u] = -1;
        level[comp[0]] = 0;
        
        while(!bfs_q.empty()){
            int u = bfs_q.front();
            bfs_q.pop();
            for(auto& p : adj[u]){
                int v = p.first;
                int id = p.second;
                if(in_set[v]){
                    if(level[v] == -1){
                        // Tree edge u -> v
                        level[v] = level[u] + 1;
                        bfs_q.push(v);
                        if(edges[id].u == u) final_dirs[id] = 0;
                        else final_dirs[id] = 1;
                    } else {
                        // Non-tree edge, orient back up: deeper -> shallower
                        if(level[v] < level[u]){
                             if(edges[id].u == u) final_dirs[id] = 0;
                             else final_dirs[id] = 1;
                        } 
                        else if(level[v] == level[u]){
                             if(u < v) {
                                 if(edges[id].u == u) final_dirs[id] = 0;
                                 else final_dirs[id] = 1;
                             }
                        }
                    }
                }
            }
        }
    }
}

// Function to set directions between two disjoint sets S1 -> S2
void orient_cross(const vector<int>& S1, const vector<int>& S2, vector<int>& final_dirs) {
    vector<bool> in1(N, false);
    for(int u : S1) in1[u] = true;
    vector<bool> in2(N, false);
    for(int u : S2) in2[u] = true;

    for(int i=0; i<M; ++i){
        int u = edges[i].u;
        int v = edges[i].v;
        if(in1[u] && in2[v]) final_dirs[i] = 0; // u->v
        else if(in1[v] && in2[u]) final_dirs[i] = 1; // v->u
    }
}

int main(){
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if(!(cin >> N >> M)) return 0;
    
    adj.resize(N);
    edges.resize(M);
    for(int i=0; i<M; ++i){
        cin >> edges[i].u >> edges[i].v;
        edges[i].id = i;
        adj[edges[i].u].push_back({edges[i].v, i});
        adj[edges[i].v].push_back({edges[i].u, i});
    }

    // Step 1: Find a split (A in U, B in V)
    vector<int> U, V;
    bool found_split = false;
    int queries_spent = 0;

    while(queries_spent < 350 && !found_split) {
        int r = uniform_int_distribution<int>(0, N-1)(rng);
        vector<int> dist = get_dists(r);
        
        int attempts = 0;
        while(attempts < 8 && !found_split) {
            attempts++;
            int x = uniform_int_distribution<int>(0, N-1)(rng);
            int k = dist[x];
            if(k == 0) continue; 
            
            vector<int> S_low, S_high;
            for(int i=0; i<N; ++i) {
                if(dist[i] < k) S_low.push_back(i);
                else S_high.push_back(i);
            }
            if(S_low.empty() || S_high.empty()) continue;

            vector<int> dirs(M, 0);
            
            // Check 1: Orient S_low -> S_high
            // If result 0, then A in S_high, B in S_low (blocked path)
            orient_SC(S_low, dirs);
            orient_SC(S_high, dirs);
            orient_cross(S_low, S_high, dirs);
            
            int res = query(dirs);
            queries_spent++;
            if(res == 0) {
                U = S_high;
                V = S_low;
                found_split = true;
                break;
            }

            // Check 2: Orient S_high -> S_low
            // If result 0, then A in S_low, B in S_high (blocked path)
            fill(dirs.begin(), dirs.end(), 0);
            orient_SC(S_low, dirs);
            orient_SC(S_high, dirs);
            orient_cross(S_high, S_low, dirs);
            
            res = query(dirs);
            queries_spent++;
            if(res == 0) {
                U = S_low;
                V = S_high;
                found_split = true;
                break;
            }
        }
    }

    if(!found_split) answer(0, 1);

    // Step 2: Binary Search for A in U
    // Check if A in U1. Need result 0 if A in U1.
    // Config: V -> U1, U2 -> U1, U2 -> V
    while(U.size() > 1) {
        int mid = U.size() / 2;
        vector<int> U1, U2;
        for(int i=0; i<mid; ++i) U1.push_back(U[i]);
        for(int i=mid; i<(int)U.size(); ++i) U2.push_back(U[i]);

        vector<int> dirs(M, 0);
        orient_SC(U1, dirs);
        orient_SC(U2, dirs);
        orient_SC(V, dirs);
        
        orient_cross(V, U1, dirs);
        orient_cross(U2, U1, dirs);
        orient_cross(U2, V, dirs);
        
        int res = query(dirs);
        if(res == 0) U = U1;
        else U = U2;
    }
    int final_A = U[0];

    // Step 3: Binary Search for B in V
    // Check if B in V1. Need result 0 if B in V1.
    // Config: V1 -> A, A -> V2, V1 -> V2
    vector<int> UnitA = {final_A};
    while(V.size() > 1) {
        int mid = V.size() / 2;
        vector<int> V1, V2;
        for(int i=0; i<mid; ++i) V1.push_back(V[i]);
        for(int i=mid; i<(int)V.size(); ++i) V2.push_back(V[i]);

        vector<int> dirs(M, 0);
        orient_SC(V1, dirs);
        orient_SC(V2, dirs);
        
        orient_cross(V1, UnitA, dirs);
        orient_cross(UnitA, V2, dirs);
        orient_cross(V1, V2, dirs);
        
        int res = query(dirs);
        if(res == 0) V = V1;
        else V = V2;
    }
    int final_B = V[0];

    answer(final_A, final_B);

    return 0;
}