#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

// Global N to be accessible if needed, though passed around.
int N;

// Cache for query results to avoid duplicates
map<vector<int>, int> cache_q;

// Function to perform query
int query(vector<int> s) {
    if (s.empty()) return 0;
    if (s.size() == 1) return 0; // Single vertex has 0 edges
    sort(s.begin(), s.end());
    if (cache_q.count(s)) return cache_q[s];

    cout << "? " << s.size() << endl;
    for (size_t i = 0; i < s.size(); ++i) {
        cout << s[i] << (i == s.size() - 1 ? "" : " ");
    }
    cout << endl;

    int m;
    cin >> m;
    if (m == -1) exit(0); // Error or limit exceeded
    return cache_q[s] = m;
}

// Recursive function to find vertices in B connected to A
// q_A is the number of edges within A (passed to save a query)
// cross_total is the known number of edges between A and B
vector<int> get_connected(const vector<int>& A, const vector<int>& B, int q_A, int cross_total) {
    if (cross_total == 0) return {};
    if (B.empty()) return {};
    
    // Base case: if B has 1 element and cross > 0, it must be connected
    if (B.size() == 1) {
        return {B[0]};
    }

    int mid = B.size() / 2;
    vector<int> B_left(B.begin(), B.begin() + mid);
    vector<int> B_right(B.begin() + mid, B.end());

    // Calculate cross(A, B_left)
    // cross(A, B_left) = Q(A U B_left) - Q(A) - Q(B_left)
    
    vector<int> Union_left = A;
    Union_left.insert(Union_left.end(), B_left.begin(), B_left.end());
    
    int q_union = query(Union_left);
    int q_b_left = query(B_left);
    
    int cross_left = q_union - q_A - q_b_left;
    
    vector<int> res_left = get_connected(A, B_left, q_A, cross_left);
    
    int cross_right = cross_total - cross_left;
    // We can avoid querying Q(A U B_right) because we know total cross edges
    // However, we still need Q(B_right) inside the recursive call to split further cross edges
    // But inside the recursive call, it will calculate cross_left_sub using Q.
    // So we just pass cross_right.
    
    vector<int> res_right = get_connected(A, B_right, q_A, cross_right);
    
    res_left.insert(res_left.end(), res_right.begin(), res_right.end());
    return res_left;
}

// Helper to find a parent for node u in layer PrevL
int find_parent(int u, const vector<int>& PrevL) {
    vector<int> current_candidates = PrevL;
    
    while (current_candidates.size() > 1) {
        int mid = current_candidates.size() / 2;
        vector<int> left_part(current_candidates.begin(), current_candidates.begin() + mid);
        
        // Check if u is connected to left_part
        // cross(u, left_part) = Q(left_part + u) - Q(left_part)
        // Q(u) is 0.
        
        vector<int> union_set = left_part;
        union_set.push_back(u);
        
        int q_union = query(union_set);
        int q_s = query(left_part);
        
        if (q_union - q_s > 0) {
            current_candidates = left_part;
        } else {
            vector<int> right_part(current_candidates.begin() + mid, current_candidates.end());
            current_candidates = right_part;
        }
    }
    return current_candidates[0];
}

// Helper to find edge within a layer
pair<int, int> find_internal_edge(const vector<int>& Layer) {
    vector<int> candidates = Layer;
    
    while (true) {
        // Should catch cases where Q(Layer) > 0 before calling this, so loop terminates.
        int mid = candidates.size() / 2;
        vector<int> L(candidates.begin(), candidates.begin() + mid);
        vector<int> R(candidates.begin() + mid, candidates.end());
        
        int q_L = query(L);
        if (q_L > 0) {
            candidates = L;
            continue;
        }
        int q_R = query(R);
        if (q_R > 0) {
            candidates = R;
            continue;
        }
        
        // Edge crosses L and R.
        // Find u in L connected to R.
        int u = -1;
        vector<int> search_u = L;
        while(search_u.size() > 1) {
            int m_u = search_u.size()/2;
            vector<int> sub_u(search_u.begin(), search_u.begin() + m_u);
            
            vector<int> joint = sub_u;
            joint.insert(joint.end(), R.begin(), R.end());
            int q_joint = query(joint);
            int q_sub = query(sub_u);
            // q_R is 0
            if (q_joint - q_sub > 0) {
                search_u = sub_u;
            } else {
                search_u = vector<int>(search_u.begin() + m_u, search_u.end());
            }
        }
        u = search_u[0];
        
        // Find v in R connected to u
        int v = -1;
        vector<int> search_v = R;
        while(search_v.size() > 1) {
            int m_v = search_v.size()/2;
            vector<int> sub_v(search_v.begin(), search_v.begin() + m_v);
            
            vector<int> joint = sub_v;
            joint.push_back(u);
            int q_joint = query(joint);
            int q_sub = query(sub_v);
            
            if (q_joint - q_sub > 0) {
                search_v = sub_v;
            } else {
                search_v = vector<int>(search_v.begin() + m_v, search_v.end());
            }
        }
        v = search_v[0];
        return {u, v};
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    
    cin >> N;
    
    vector<int> unvisited;
    for (int i = 2; i <= N; ++i) unvisited.push_back(i);
    
    vector<vector<int>> layers;
    layers.push_back({1});
    
    int current_layer_idx = 0;
    
    // Build BFS layers
    while(!unvisited.empty()) {
        vector<int>& curr = layers[current_layer_idx];
        int q_curr = query(curr); 
        
        vector<int> joint = curr;
        joint.insert(joint.end(), unvisited.begin(), unvisited.end());
        int q_joint = query(joint);
        int q_unvisited = query(unvisited);
        
        int cross = q_joint - q_curr - q_unvisited;
        
        if (cross == 0) {
            // This implies the graph is disconnected or unvisited is empty.
            // Since problem guarantees connected graph, this only happens if unvisited is empty
            // (checked by while loop condition) or logic error.
            break;
        }
        
        vector<int> next_layer = get_connected(curr, unvisited, q_curr, cross);
        
        // Efficiently remove found nodes from unvisited
        sort(next_layer.begin(), next_layer.end());
        vector<int> new_unvisited;
        int ptr = 0;
        for (int x : unvisited) {
            if (ptr < (int)next_layer.size() && next_layer[ptr] == x) {
                ptr++;
            } else {
                new_unvisited.push_back(x);
            }
        }
        unvisited = new_unvisited;
        
        layers.push_back(next_layer);
        current_layer_idx++;
    }
    
    // Check for internal edges in each layer to detect odd cycles
    for (int i = 0; i < (int)layers.size(); ++i) {
        int q = query(layers[i]);
        if (q > 0) {
            // Not bipartite
            pair<int, int> edge = find_internal_edge(layers[i]);
            int u = edge.first;
            int v = edge.second;
            
            // Trace back to root
            vector<int> path_u, path_v;
            path_u.push_back(u);
            path_v.push_back(v);
            
            int curr_u = u;
            for (int k = i - 1; k >= 0; --k) {
                int p = find_parent(curr_u, layers[k]);
                path_u.push_back(p);
                curr_u = p;
            }
            
            int curr_v = v;
            for (int k = i - 1; k >= 0; --k) {
                int p = find_parent(curr_v, layers[k]);
                path_v.push_back(p);
                curr_v = p;
            }
            
            // Find LCA
            reverse(path_u.begin(), path_u.end());
            reverse(path_v.begin(), path_v.end());
            
            int lca_idx = 0;
            while(lca_idx < (int)path_u.size() && lca_idx < (int)path_v.size() && path_u[lca_idx] == path_v[lca_idx]) {
                lca_idx++;
            }
            lca_idx--; // Index of LCA
            
            cout << "N " << (path_u.size() - lca_idx) + (path_v.size() - lca_idx - 1) << endl;
            // Print path from u up to LCA
            // Actually path_u is root...u. We want u...root -> LCA -> ...v -> u
            // Or u...LCA...v...u
            
            // Output cycle vertices:
            // Path from u to LCA (exclusive of LCA? No, include LCA)
            // path_u[lca_idx...end] is LCA...u. Reverse to get u...LCA
            for (int k = path_u.size() - 1; k >= lca_idx; --k) {
                cout << path_u[k] << " ";
            }
            // Path from LCA to v (exclusive of LCA since printed)
            // path_v[lca_idx...end] is LCA...v.
            for (int k = lca_idx + 1; k < (int)path_v.size(); ++k) {
                cout << path_v[k] << " ";
            }
            cout << endl;
            return 0;
        }
    }
    
    // If no internal edges, graph is bipartite
    vector<int> partition;
    for (int i = 0; i < (int)layers.size(); i += 2) {
        for (int x : layers[i]) partition.push_back(x);
    }
    
    cout << "Y " << partition.size() << endl;
    for (size_t i = 0; i < partition.size(); ++i) {
        cout << partition[i] << (i == partition.size() - 1 ? "" : " ");
    }
    cout << endl;
    
    return 0;
}