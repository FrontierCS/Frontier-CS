#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

int n;
map<vector<int>, int> query_cache;

int make_query(vector<int>& s) {
    if (s.empty()) {
        return 0;
    }
    sort(s.begin(), s.end());
    if (query_cache.count(s)) {
        return query_cache[s];
    }
    cout << "? " << s.size() << endl;
    for (size_t i = 0; i < s.size(); ++i) {
        cout << s[i] << (i == s.size() - 1 ? "" : " ");
    }
    cout << endl;
    int m;
    cin >> m;
    if (m == -1) exit(0);
    query_cache[s] = m;
    return m;
}

int count_edges_between(vector<int>& A, vector<int>& B) {
    if (A.empty() || B.empty()) {
        return 0;
    }
    vector<int> A_union_B;
    A_union_B.reserve(A.size() + B.size());
    A_union_B.insert(A_union_B.end(), A.begin(), A.end());
    A_union_B.insert(A_union_B.end(), B.begin(), B.end());
    
    int edges_A_union_B = make_query(A_union_B);
    int edges_A = make_query(A);
    int edges_B = make_query(B);

    return edges_A_union_B - edges_A - edges_B;
}

int find_one_neighbor_in_U(vector<int>& L, vector<int>& U) {
    if (U.empty() || count_edges_between(L, U) == 0) {
        return -1;
    }
    
    while (U.size() > 1) {
        int mid = U.size() / 2;
        vector<int> U1(U.begin(), U.begin() + mid);
        if (count_edges_between(L, U1) > 0) {
            U = U1;
        } else {
            vector<int> U2(U.begin() + mid, U.end());
            U = U2;
        }
    }
    return U[0];
}

vector<int> get_path(int start_node, int start_layer_idx, const vector<vector<int>>& layers) {
    vector<int> path;
    path.push_back(start_node);
    int curr_node = start_node;
    for (int i = start_layer_idx; i > 0; --i) {
        vector<int> prev_layer = layers[i-1];
        vector<int> curr_node_vec = {curr_node};
        int parent = find_one_neighbor_in_U(curr_node_vec, prev_layer);
        curr_node = parent;
        path.push_back(curr_node);
    }
    reverse(path.begin(), path.end());
    return path;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;

    vector<int> color(n + 1, -1);
    vector<vector<int>> layers;
    vector<int> p0, p1;

    color[1] = 0;
    p0.push_back(1);
    layers.push_back({1});

    vector<int> l1;
    for (int i = 2; i <= n; ++i) {
        vector<int> q = {1,i};
        if (make_query(q) == 1) {
            l1.push_back(i);
        }
    }
    for (int v : l1) {
        color[v] = 1;
        p1.push_back(v);
    }
    layers.push_back(l1);

    int current_layer_idx = 1;
    while (true) {
        vector<int>& current_layer = layers[current_layer_idx];
        if (current_layer.empty()) break;

        vector<int> temp_layer = current_layer;
        int edges_in_layer = make_query(temp_layer);
        if (edges_in_layer > 0) {
            int u = -1, v = -1;
            
            for(int node : current_layer) {
                vector<int> sub_layer;
                for(int other_node : current_layer) if(other_node != node) sub_layer.push_back(other_node);
                if (edges_in_layer > make_query(sub_layer)) {
                    u = node;
                    break;
                }
            }

            vector<int> potential_neighbors;
            for(int node : current_layer) if(node != u) potential_neighbors.push_back(node);
            vector<int> u_vec = {u};
            v = find_one_neighbor_in_U(u_vec, potential_neighbors);
            
            vector<int> path_u = get_path(u, current_layer_idx, layers);
            vector<int> path_v = get_path(v, current_layer_idx, layers);
            
            int lca_idx = 0;
            while(lca_idx + 1 < (int)path_u.size() && lca_idx + 1 < (int)path_v.size() && path_u[lca_idx+1] == path_v[lca_idx+1]){
                lca_idx++;
            }

            vector<int> cycle;
            for(size_t i = path_u.size() - 1; i > (size_t)lca_idx; --i) cycle.push_back(path_u[i]);
            cycle.push_back(path_u[lca_idx]);
            for(size_t i = lca_idx + 1; i < path_v.size(); ++i) cycle.push_back(path_v[i]);
            
            cout << "N " << cycle.size() << endl;
            for (size_t i = 0; i < cycle.size(); ++i) {
                cout << cycle[i] << (i == cycle.size() - 1 ? "" : " ");
            }
            cout << endl;
            return 0;
        }

        vector<int> uncolored;
        for (int i = 1; i <= n; ++i) {
            if (color[i] == -1) {
                uncolored.push_back(i);
            }
        }

        if (uncolored.empty()) break;
        
        vector<int> next_layer;
        while(true) {
            int neighbor_node = find_one_neighbor_in_U(current_layer, uncolored);
            if(neighbor_node == -1) break;
            next_layer.push_back(neighbor_node);
            uncolored.erase(remove(uncolored.begin(), uncolored.end(), neighbor_node), uncolored.end());
        }
        
        int next_color = (layers.size()) % 2;
        for (int node : next_layer) {
            color[node] = next_color;
            if (next_color == 0) p0.push_back(node);
            else p1.push_back(node);
        }
        
        layers.push_back(next_layer);
        current_layer_idx++;
    }

    cout << "Y " << p0.size() << endl;
    sort(p0.begin(), p0.end());
    for (size_t i = 0; i < p0.size(); ++i) {
        cout << p0[i] << (i == p0.size() - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}