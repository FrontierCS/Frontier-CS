#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <cstdlib>

using namespace std;

int N;
map<vector<int>, int> memo;

// Helper function to query the number of edges in a set of vertices
int query(vector<int> v) {
    if (v.empty() || v.size() == 1) return 0;
    sort(v.begin(), v.end());
    if (memo.count(v)) return memo[v];
    
    cout << "? " << v.size() << "\n";
    for (int i = 0; i < v.size(); ++i) {
        cout << v[i] << (i == v.size() - 1 ? "" : " ");
    }
    cout << endl; // Flush here
    
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return memo[v] = res;
}

// Returns number of edges between two disjoint sets A and B
// Uses inclusion-exclusion: E(A, B) = E(A U B) - E(A) - E(B)
int get_edges(vector<int>& A, vector<int>& B) {
    if (A.empty() || B.empty()) return 0;
    vector<int> uni = A;
    uni.insert(uni.end(), B.begin(), B.end());
    return query(uni) - query(A) - query(B);
}

// Divide and Conquer to find all vertices in U that are connected to L.
// known_edges is the pre-calculated number of edges between U and L.
vector<int> find_next_layer(vector<int>& U, vector<int>& L, int known_edges) {
    if (known_edges == 0) return {};
    if (U.size() == 1) return U;
    
    int mid = U.size() / 2;
    vector<int> left_part(U.begin(), U.begin() + mid);
    vector<int> right_part(U.begin() + mid, U.end());
    
    // We only need to query one side, the other is derived
    int left_edges = get_edges(left_part, L);
    int right_edges = known_edges - left_edges;
    
    vector<int> res;
    if (left_edges > 0) {
        vector<int> l_res = find_next_layer(left_part, L, left_edges);
        res.insert(res.end(), l_res.begin(), l_res.end());
    }
    if (right_edges > 0) {
        vector<int> r_res = find_next_layer(right_part, L, right_edges);
        res.insert(res.end(), r_res.begin(), r_res.end());
    }
    return res;
}

// Find a single parent in L for vertex u (where we know u is connected to L)
int find_parent(int u, vector<int>& L) {
    int low = 0, high = L.size() - 1;
    // Binary search for the neighbor
    while (low < high) {
        int mid = low + (high - low) / 2;
        vector<int> left_subset;
        for (int i = low; i <= mid; ++i) left_subset.push_back(L[i]);
        
        vector<int> u_vec = {u};
        if (get_edges(u_vec, left_subset) > 0) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return L[low];
}

// Find an edge (u, v) within S where query(S) > 0
pair<int, int> find_bad_edge(vector<int>& S) {
    if (S.size() == 2) return {S[0], S[1]};
    
    int mid = S.size() / 2;
    vector<int> A(S.begin(), S.begin() + mid);
    vector<int> B(S.begin() + mid, S.end());
    
    if (query(A) > 0) return find_bad_edge(A);
    if (query(B) > 0) return find_bad_edge(B);
    
    // Edge is between A and B
    // Find u in A connected to B
    int u = -1;
    {
        int low = 0, high = A.size() - 1;
        while (low < high) {
            int m = low + (high - low) / 2;
            vector<int> subA;
            for(int i=low; i<=m; ++i) subA.push_back(A[i]);
            if (get_edges(subA, B) > 0) high = m;
            else low = m + 1;
        }
        u = A[low];
    }
    
    // Find v in B connected to u
    int v = -1;
    {
        int low = 0, high = B.size() - 1;
        while (low < high) {
            int m = low + (high - low) / 2;
            vector<int> subB;
            for(int i=low; i<=m; ++i) subB.push_back(B[i]);
            vector<int> U_vec = {u};
            if (get_edges(U_vec, subB) > 0) high = m;
            else low = m + 1;
        }
        v = B[low];
    }
    return {u, v};
}

int main() {
    ios_base::sync_with_stdio(false);
    
    if (!(cin >> N)) return 0;
    
    vector<int> U;
    for (int i = 2; i <= N; ++i) U.push_back(i);
    
    vector<vector<int>> layers;
    layers.push_back({1});
    
    vector<int> parent(N + 1, 0);
    
    // BFS to build layers
    while (!U.empty()) {
        vector<int>& L = layers.back();
        int total = get_edges(U, L);
        if (total == 0) break; 
        
        vector<int> next_L = find_next_layer(U, L, total);
        
        vector<int> new_U;
        vector<bool> removed(N + 1, false);
        for(int x : next_L) removed[x] = true;
        for(int x : U) if (!removed[x]) new_U.push_back(x);
        U = new_U;
        
        for(int v : next_L) {
            parent[v] = find_parent(v, L);
        }
        
        layers.push_back(next_L);
    }
    
    // Check for internal edges in each layer
    for(auto& layer : layers) {
        if (query(layer) > 0) {
            // Not bipartite, odd cycle found
            pair<int, int> edge = find_bad_edge(layer);
            int u = edge.first;
            int v = edge.second;
            
            // Reconstruct paths to root
            vector<int> path_u, path_v;
            int cur = u;
            while(cur != 0) { path_u.push_back(cur); cur = parent[cur]; }
            cur = v;
            while(cur != 0) { path_v.push_back(cur); cur = parent[cur]; }
            
            // Find LCA
            int lca = -1;
            int idx_u = path_u.size() - 1;
            int idx_v = path_v.size() - 1;
            while(idx_u >= 0 && idx_v >= 0 && path_u[idx_u] == path_v[idx_v]) {
                lca = path_u[idx_u];
                idx_u--;
                idx_v--;
            }
            
            vector<int> cycle;
            // From u to lca
            for(int i=0; i<=idx_u + 1; ++i) cycle.push_back(path_u[i]);
            // From neighbor of lca (on v's path) to v
            for(int i=idx_v; i>=0; --i) cycle.push_back(path_v[i]);
            
            cout << "N " << cycle.size() << endl;
            for(int i=0; i<cycle.size(); ++i) cout << cycle[i] << (i == cycle.size()-1 ? "" : " ");
            cout << endl;
            return 0;
        }
    }
    
    // If no odd cycle, graph is bipartite
    vector<int> partA;
    for(int i=0; i<layers.size(); ++i) {
        if (i % 2 == 0) {
            partA.insert(partA.end(), layers[i].begin(), layers[i].end());
        }
    }
    cout << "Y " << partA.size() << endl;
    for(int i=0; i<partA.size(); ++i) cout << partA[i] << (i == partA.size()-1 ? "" : " ");
    cout << endl;
    
    return 0;
}