#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

int n;
map<vector<int>, int> memo;

// Function to query the number of edges in a subset s
int query(vector<int> s) {
    if (s.size() <= 1) return 0;
    sort(s.begin(), s.end());
    if (memo.count(s)) return memo[s];

    cout << "? " << s.size() << "\n";
    for (int i = 0; i < s.size(); ++i) {
        cout << s[i] << (i == s.size() - 1 ? "" : " ");
    }
    cout << endl;

    int ans;
    cin >> ans;
    if (ans == -1) exit(0);
    return memo[s] = ans;
}

vector<int> current_layer;
int e_current_layer;

// Recursive function to identify vertices in 'candidates' that are connected to 'current_layer'
void find_next_layer(vector<int>& candidates, int edges_cross, vector<int>& next_layer) {
    if (edges_cross == 0) return;
    if (candidates.size() == 1) {
        next_layer.push_back(candidates[0]);
        return;
    }

    int mid = candidates.size() / 2;
    vector<int> left_part(candidates.begin(), candidates.begin() + mid);
    vector<int> right_part(candidates.begin() + mid, candidates.end());

    int e_left = query(left_part);
    
    vector<int> U = current_layer;
    U.insert(U.end(), left_part.begin(), left_part.end());
    int e_union = query(U);
    
    // Calculate number of edges between current_layer and left_part
    int cross_left = e_union - e_current_layer - e_left;
    int cross_right = edges_cross - cross_left;
    
    find_next_layer(left_part, cross_left, next_layer);
    find_next_layer(right_part, cross_right, next_layer);
}

// Find an edge (u, v) within a set s known to have edges
pair<int, int> find_edge_in_set(vector<int>& s) {
    if (s.size() == 2) return {s[0], s[1]};
    
    int mid = s.size() / 2;
    vector<int> A(s.begin(), s.begin() + mid);
    vector<int> B(s.begin() + mid, s.end());
    
    int e_A = query(A);
    if (e_A > 0) return find_edge_in_set(A);
    
    int e_B = query(B);
    if (e_B > 0) return find_edge_in_set(B);
    
    // Edge crosses A and B
    int u = -1;
    {
        vector<int> cand = A;
        while (cand.size() > 1) {
            int m = cand.size() / 2;
            vector<int> subA(cand.begin(), cand.begin() + m);
            vector<int> subB(cand.begin() + m, cand.end());
            
            vector<int> test = subA;
            test.insert(test.end(), B.begin(), B.end());
            // Edges between subA and B?
            if (query(test) > 0) {
                cand = subA;
            } else {
                cand = subB;
            }
        }
        u = cand[0];
    }
    
    int v = -1;
    {
        vector<int> cand = B;
        while (cand.size() > 1) {
            int m = cand.size() / 2;
            vector<int> subA(cand.begin(), cand.begin() + m);
            vector<int> subB(cand.begin() + m, cand.end());
            
            vector<int> test = subA;
            test.push_back(u);
            // Edges between {u} and subA?
            if (query(test) > 0) {
                cand = subA;
            } else {
                cand = subB;
            }
        }
        v = cand[0];
    }
    return {u, v};
}

// Find a neighbor of u in potential_parents
int find_parent(int u, const vector<int>& potential_parents) {
    vector<int> cand = potential_parents;
    while (cand.size() > 1) {
        int mid = cand.size() / 2;
        vector<int> left(cand.begin(), cand.begin() + mid);
        vector<int> right(cand.begin() + mid, cand.end());
        
        vector<int> test = left;
        test.push_back(u);
        int e_test = query(test);
        int e_left = query(left);
        
        if (e_test - e_left > 0) {
            cand = left;
        } else {
            cand = right;
        }
    }
    return cand[0];
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    vector<vector<int>> layers;
    vector<int> L0;
    L0.push_back(1);
    layers.push_back(L0);

    vector<int> U;
    for (int i = 2; i <= n; ++i) U.push_back(i);

    // Build BFS layers
    while (!U.empty()) {
        current_layer = layers.back();
        e_current_layer = query(current_layer);
        
        int e_U = query(U);
        vector<int> combined = current_layer;
        combined.insert(combined.end(), U.begin(), U.end());
        int e_combined = query(combined);
        
        int edges_cross = e_combined - e_current_layer - e_U;
        
        vector<int> next_layer;
        find_next_layer(U, edges_cross, next_layer);
        
        layers.push_back(next_layer);
        
        vector<bool> is_next(n + 1, false);
        for (int x : next_layer) is_next[x] = true;
        
        vector<int> new_U;
        for (int x : U) {
            if (!is_next[x]) new_U.push_back(x);
        }
        U = new_U;
    }

    // Check for edges within same layer (odd cycle detection)
    for (int i = 0; i < layers.size(); ++i) {
        int e_layer = query(layers[i]);
        if (e_layer > 0) {
            pair<int, int> edge = find_edge_in_set(layers[i]);
            int u = edge.first;
            int v = edge.second;
            
            vector<int> path_u, path_v;
            path_u.push_back(u);
            path_v.push_back(v);
            
            int curr_u = u;
            int curr_v = v;
            for (int d = i; d > 0; --d) {
                int p_u = find_parent(curr_u, layers[d-1]);
                path_u.push_back(p_u);
                curr_u = p_u;
                
                int p_v = find_parent(curr_v, layers[d-1]);
                path_v.push_back(p_v);
                curr_v = p_v;
            }
            reverse(path_u.begin(), path_u.end());
            reverse(path_v.begin(), path_v.end());
            
            int lca_idx = 0;
            while (lca_idx + 1 < path_u.size() && lca_idx + 1 < path_v.size() && 
                   path_u[lca_idx+1] == path_v[lca_idx+1]) {
                lca_idx++;
            }
            
            cout << "N ";
            vector<int> cycle;
            for (int k = path_u.size() - 1; k > lca_idx; --k) {
                cycle.push_back(path_u[k]);
            }
            cycle.push_back(path_u[lca_idx]);
            for (int k = lca_idx + 1; k < path_v.size(); ++k) {
                cycle.push_back(path_v[k]);
            }
            
            cout << cycle.size() << endl;
            for (int k = 0; k < cycle.size(); ++k) {
                cout << cycle[k] << (k == cycle.size() - 1 ? "" : " ");
            }
            cout << endl;
            return 0;
        }
    }

    // Graph is bipartite
    cout << "Y ";
    vector<int> part1;
    for (int i = 0; i < layers.size(); i += 2) {
        for (int x : layers[i]) part1.push_back(x);
    }
    cout << part1.size() << endl;
    for (int i = 0; i < part1.size(); ++i) {
        cout << part1[i] << (i == part1.size() - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}