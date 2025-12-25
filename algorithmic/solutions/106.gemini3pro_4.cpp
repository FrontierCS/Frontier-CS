#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

int N;

// Function to perform a query
// Returns the number of edges in the induced subgraph of vertices in s
int query(const vector<int>& s) {
    if (s.size() <= 1) return 0;
    cout << "? " << s.size() << "\n";
    for (size_t i = 0; i < s.size(); ++i) {
        cout << s[i] << (i == s.size() - 1 ? "" : " ");
    }
    cout << "\n";
    cout.flush();
    int m;
    cin >> m;
    if (m == -1) exit(0);
    return m;
}

// Global variables for BFS and tree construction
vector<vector<int>> layers;
int parent[605];
int depth_node[605];
vector<int> current_layer_nodes;
map<pair<int, int>, int> memo_layer;

// Precompute edge counts for segments of the current layer to speed up parent finding
void build_layer_memo(int l, int r) {
    if (r - l <= 1) {
        memo_layer[{l, r}] = 0;
        return;
    }
    vector<int> sub;
    for(int i=l; i<r; ++i) sub.push_back(current_layer_nodes[i]);
    memo_layer[{l, r}] = query(sub);
    
    int mid = l + (r - l) / 2;
    build_layer_memo(l, mid);
    build_layer_memo(mid, r);
}

int get_layer_memo(int l, int r) {
    if (r - l <= 1) return 0;
    return memo_layer[{l, r}];
}

// Find a parent for node v in current_layer_nodes[l...r-1]
int find_parent(int v, int l, int r) {
    if (r - l == 1) return current_layer_nodes[l];
    int mid = l + (r - l) / 2;
    
    // Check edges between v and left half
    // Edges( {v} U Left ) - Edges(Left)
    vector<int> q_set;
    q_set.push_back(v);
    for(int i=l; i<mid; ++i) q_set.push_back(current_layer_nodes[i]);
    
    int e_combined = query(q_set);
    int e_left = get_layer_memo(l, mid);
    
    if (e_combined - e_left > 0) {
        return find_parent(v, l, mid);
    } else {
        return find_parent(v, mid, r);
    }
}

vector<int> next_layer_nodes;
int e_current_layer_total;

// Recursively find nodes in 'candidates' that are connected to 'current_layer_nodes'
// k is the number of edges between candidates and current_layer_nodes
void solve_next_layer(vector<int>& candidates, int k) {
    if (k == 0) return;
    if (candidates.size() == 1) {
        next_layer_nodes.push_back(candidates[0]);
        return;
    }
    
    int mid = candidates.size() / 2;
    vector<int> left_part(candidates.begin(), candidates.begin() + mid);
    vector<int> right_part(candidates.begin() + mid, candidates.end());
    
    int e_left = query(left_part);
    
    vector<int> union_set = left_part;
    union_set.insert(union_set.end(), current_layer_nodes.begin(), current_layer_nodes.end());
    int e_union = query(union_set);
    
    // Calculate edges between left_part and current_layer_nodes
    int k_left = e_union - e_left - e_current_layer_total;
    int k_right = k - k_left;
    
    solve_next_layer(left_part, k_left);
    solve_next_layer(right_part, k_right);
}

// Find a node in candidates connected to target
int find_connector(vector<int> candidates, const vector<int>& target, int e_target) {
    if (candidates.size() == 1) return candidates[0];
    int mid = candidates.size() / 2;
    vector<int> c1(candidates.begin(), candidates.begin() + mid);
    vector<int> c2(candidates.begin() + mid, candidates.end());
    
    int e_c1 = query(c1);
    
    vector<int> u = c1;
    u.insert(u.end(), target.begin(), target.end());
    int e_u = query(u);
    
    // Check if there are edges between c1 and target
    if (e_u - e_c1 - e_target > 0) return find_connector(c1, target, e_target);
    else return find_connector(c2, target, e_target);
}

// Find two connected nodes within a set s known to have internal edges
pair<int, int> find_internal_edge(vector<int> s) {
    if (s.size() < 2) return {-1, -1};
    int mid = s.size() / 2;
    vector<int> s1(s.begin(), s.begin() + mid);
    vector<int> s2(s.begin() + mid, s.end());
    
    int e1 = query(s1);
    if (e1 > 0) return find_internal_edge(s1);
    
    int e2 = query(s2);
    if (e2 > 0) return find_internal_edge(s2);
    
    // Edge is between s1 and s2
    int u = find_connector(s1, s2, e2);
    int v = find_connector(s2, {u}, 0);
    return {u, v};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N)) return 0;

    vector<int> unvisited;
    for (int i = 2; i <= N; ++i) unvisited.push_back(i);
    
    layers.push_back({1});
    depth_node[1] = 0;
    parent[1] = 0;
    
    // BFS Construction
    while (!unvisited.empty()) {
        vector<int>& cur = layers.back();
        if (cur.empty()) break;
        
        current_layer_nodes = cur;
        memo_layer.clear();
        build_layer_memo(0, cur.size());
        e_current_layer_total = get_layer_memo(0, cur.size());
        
        int e_unvisited = query(unvisited);
        vector<int> uni = unvisited;
        uni.insert(uni.end(), cur.begin(), cur.end());
        int e_uni = query(uni);
        int k_total = e_uni - e_unvisited - e_current_layer_total;
        
        next_layer_nodes.clear();
        if (k_total > 0) {
            solve_next_layer(unvisited, k_total);
        }
        
        if (next_layer_nodes.empty()) break;
        
        vector<int> new_unvisited;
        vector<bool> is_next(N + 1, false);
        for (int v : next_layer_nodes) is_next[v] = true;
        
        for (int v : unvisited) {
            if (!is_next[v]) new_unvisited.push_back(v);
        }
        unvisited = new_unvisited;
        
        for (int v : next_layer_nodes) {
            int p = find_parent(v, 0, cur.size());
            parent[v] = p;
            depth_node[v] = layers.size();
        }
        
        layers.push_back(next_layer_nodes);
    }
    
    // Check for odd cycle
    for (const auto& layer : layers) {
        if (layer.empty()) continue;
        int e = query(layer);
        if (e > 0) {
            pair<int, int> edge = find_internal_edge(layer);
            int u = edge.first;
            int v = edge.second;
            
            vector<int> path_u, path_v;
            int curr = u;
            while (curr != 0) {
                path_u.push_back(curr);
                curr = parent[curr];
            }
            curr = v;
            while (curr != 0) {
                path_v.push_back(curr);
                curr = parent[curr];
            }
            
            reverse(path_u.begin(), path_u.end());
            reverse(path_v.begin(), path_v.end());
            
            int lca = -1;
            size_t idx = 0;
            while(idx < path_u.size() && idx < path_v.size() && path_u[idx] == path_v[idx]) {
                lca = path_u[idx];
                idx++;
            }
            
            vector<int> cycle;
            int temp = u;
            while(temp != lca) {
                cycle.push_back(temp);
                temp = parent[temp];
            }
            cycle.push_back(lca);
            
            vector<int> v_side;
            temp = v;
            while(temp != lca) {
                v_side.push_back(temp);
                temp = parent[temp];
            }
            reverse(v_side.begin(), v_side.end());
            cycle.insert(cycle.end(), v_side.begin(), v_side.end());
            
            cout << "N " << cycle.size() << "\n";
            for(size_t i=0; i<cycle.size(); ++i) cout << cycle[i] << (i==cycle.size()-1?"":" ");
            cout << "\n";
            cout.flush();
            return 0;
        }
    }
    
    // Output Bipartition
    vector<int> part1;
    for (size_t i = 0; i < layers.size(); i += 2) {
        for (int v : layers[i]) part1.push_back(v);
    }
    cout << "Y " << part1.size() << "\n";
    for(size_t i=0; i<part1.size(); ++i) cout << part1[i] << (i==part1.size()-1?"":" ");
    cout << "\n";
    cout.flush();
    
    return 0;
}