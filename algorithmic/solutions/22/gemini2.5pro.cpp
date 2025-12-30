#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <set>
#include <tuple>

using namespace std;

vector<int> adj[100005];
vector<int> tree_adj[100005];
int parent[100005];

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    for (int i = 2; i <= n; ++i) {
        cin >> parent[i];
        tree_adj[parent[i]].push_back(i);
        tree_adj[i].push_back(parent[i]);
    }
    
    for(int i=1; i<=n; ++i) {
        adj[i] = tree_adj[i];
    }

    vector<int> leaves;
    // Root degree is guaranteed to be >= 2.
    // For any other node i, its degree in the tree is 1 + #children.
    // So, tree_adj[i].size() == 1 implies it has a parent and 0 children, i.e., it's a leaf.
    for (int i = 2; i <= n; ++i) {
        if (tree_adj[i].size() == 1) {
            leaves.push_back(i);
        }
    }
    // Handle edge case of a star graph where all non-root nodes are leaves
    if (n > 1 && tree_adj[1].size() > 0 && leaves.empty()) {
        bool is_star = true;
        for(int i = 2; i <= n; ++i) {
            if (parent[i] != 1) {
                is_star = false;
                break;
            }
        }
        if(is_star) {
            for(int i = 2; i <= n; ++i) leaves.push_back(i);
        }
    }
    sort(leaves.begin(), leaves.end());

    int k = leaves.size();
    if (k > 1) {
        for (int i = 0; i < k; ++i) {
            int u = leaves[i];
            int v = leaves[(i + 1) % k];
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }
    
    if (n <= 4) {
        cout << 1 << endl;
        cout << n;
        for (int i = 1; i <= n; ++i) {
            cout << " " << i;
        }
        cout << endl;
        return 0;
    }

    map<pair<int, int>, int> next_in_ccw;

    for (int i = 1; i <= n; ++i) {
        if (adj[i].empty()) continue;

        int lowest_neighbor = n + 1;
        for (int neighbor : adj[i]) {
            lowest_neighbor = min(lowest_neighbor, neighbor);
        }
        
        vector<int> ccw_ordered_neighbors;
        ccw_ordered_neighbors.push_back(lowest_neighbor);
        vector<int> others;
        for (int neighbor : adj[i]) {
            if (neighbor != lowest_neighbor) {
                others.push_back(neighbor);
            }
        }
        sort(others.begin(), others.end());
        for (int neighbor : others) {
            ccw_ordered_neighbors.push_back(neighbor);
        }
        
        for (size_t j = 0; j < ccw_ordered_neighbors.size(); ++j) {
            next_in_ccw[{i, ccw_ordered_neighbors[j]}] = ccw_ordered_neighbors[(j + 1) % ccw_ordered_neighbors.size()];
        }
    }

    set<pair<int, int>> visited_directed_edges;
    vector<vector<int>> faces;
    int outer_face_idx = -1;

    for (int i = 1; i <= n; ++i) {
        for (int neighbor : adj[i]) {
            if (visited_directed_edges.count({i, neighbor})) continue;
            
            vector<int> current_face;
            int curr_v = i;
            int prev_v = neighbor;

            while (!visited_directed_edges.count({curr_v, prev_v})) {
                visited_directed_edges.insert({curr_v, prev_v});
                current_face.push_back(curr_v);
                
                int next_v = next_in_ccw.at({curr_v, prev_v});
                prev_v = curr_v;
                curr_v = next_v;
            }
            faces.push_back(current_face);

            bool is_outer = false;
            if(k > 1) {
                int u_last_leaf = leaves[k-1];
                int v_first_leaf = leaves[0];
                if (u_last_leaf > v_first_leaf) swap(u_last_leaf, v_first_leaf);
                for (size_t j = 0; j < current_face.size(); ++j) {
                    int u = current_face[j];
                    int v = current_face[(j + 1) % current_face.size()];
                    if (u > v) swap(u, v);
                    if (u == u_last_leaf && v == v_first_leaf) {
                        is_outer = true;
                        break;
                    }
                }
            }
            if(is_outer) outer_face_idx = faces.size() - 1;
        }
    }

    vector<tuple<int, int, int>> triangles;
    for (size_t i = 0; i < faces.size(); ++i) {
        if ((int)i == outer_face_idx) continue;
        const auto& face = faces[i];
        if (face.size() < 3) continue;
        int v0 = face[0];
        for (size_t j = 1; j < face.size() - 1; ++j) {
            int v1 = face[j];
            int v2 = face[j + 1];
            vector<int> t = {v0, v1, v2};
            sort(t.begin(), t.end());
            triangles.emplace_back(t[0], t[1], t[2]);
        }
    }
    
    sort(triangles.begin(), triangles.end());
    triangles.erase(unique(triangles.begin(), triangles.end()), triangles.end());

    int K = triangles.size();
    map<tuple<int, int, int>, int> tri_to_idx;
    for (int i = 0; i < K; ++i) {
        tri_to_idx[triangles[i]] = i + 1;
    }

    map<pair<int, int>, vector<int>> edge_to_tri_idx;
    for (int i = 0; i < K; ++i) {
        auto [u, v, w] = triangles[i];
        vector<int> t_nodes = {u, v, w};
        for(int j=0; j<3; ++j) {
            for(int l=j+1; l<3; ++l) {
                int n1 = t_nodes[j], n2 = t_nodes[l];
                if (n1 > n2) swap(n1, n2);
                edge_to_tri_idx[{n1, n2}].push_back(i + 1);
            }
        }
    }

    vector<pair<int, int>> new_edges;
    for (auto const& [edge, tri_indices] : edge_to_tri_idx) {
        if (tri_indices.size() == 2) {
            new_edges.push_back({tri_indices[0], tri_indices[1]});
        }
    }
    
    cout << K << endl;
    for (int i = 0; i < K; ++i) {
        cout << 3 << " " << get<0>(triangles[i]) << " " << get<1>(triangles[i]) << " " << get<2>(triangles[i]) << endl;
    }

    for (const auto& edge : new_edges) {
        cout << edge.first << " " << edge.second << endl;
    }

    return 0;
}