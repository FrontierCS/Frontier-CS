#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

// DSU structure
struct DSU {
    std::vector<int> parent;
    DSU(int n) {
        parent.resize(n + 1);
        std::iota(parent.begin(), parent.end(), 0);
    }
    int find(int i) {
        if (parent[i] == i)
            return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            parent[root_i] = root_j;
        }
    }
};

int n, m;
std::vector<std::pair<int, int>> edges;
std::vector<bool> is_repaired;

// Interaction functions
void block(int road_idx) {
    std::cout << "- " << road_idx << std::endl;
}

void unblock(int road_idx) {
    std::cout << "+ " << road_idx << std::endl;
}

bool query_connectivity() {
    std::cout << "? 1 1" << std::endl;
    int result;
    std::cin >> result;
    return result == 1;
}

// Recursive helper to find one repaired edge from a set
int find_one_repaired_recursive(const std::vector<int>& candidate_edges, int low, int high) {
    if (low == high) {
        return candidate_edges[low];
    }

    int mid = low + (high - low) / 2;
    
    for (int i = low; i <= mid; ++i) {
        block(candidate_edges[i]);
    }

    bool is_conn = query_connectivity();

    for (int i = low; i <= mid; ++i) {
        unblock(candidate_edges[i]);
    }

    if (!is_conn) {
        return find_one_repaired_recursive(candidate_edges, low, mid);
    } else {
        return find_one_repaired_recursive(candidate_edges, mid + 1, high);
    }
}


void solve() {
    std::cin >> n >> m;
    edges.assign(m + 1, {0, 0});
    for (int i = 1; i <= m; ++i) {
        std::cin >> edges[i].first >> edges[i].second;
    }

    is_repaired.assign(m + 1, false);
    
    DSU dsu(n);
    int num_components = n;

    // Boruvka's algorithm to find a spanning forest (tree) of repaired roads
    while (num_components > 1) {
        std::map<int, std::vector<int>> leaving_edges;
        std::vector<int> roots;
        for (int i = 1; i <= n; ++i) {
            if (dsu.parent[i] == i) {
                roots.push_back(i);
            }
        }

        for (int i = 1; i <= m; ++i) {
            if (is_repaired[i]) continue;
            int u = edges[i].first;
            int v = edges[i].second;
            int root_u = dsu.find(u);
            int root_v = dsu.find(v);
            if (root_u != root_v) {
                leaving_edges[root_u].push_back(i);
                leaving_edges[root_v].push_back(i);
            }
        }
        
        std::map<int, int> edge_to_add_for_comp;
        for (int root : roots) {
            if (!leaving_edges[root].empty()) {
                int repaired_edge = find_one_repaired_recursive(leaving_edges[root], 0, leaving_edges[root].size() - 1);
                edge_to_add_for_comp[root] = repaired_edge;
            }
        }
        
        for (auto const& [root, edge_idx] : edge_to_add_for_comp) {
            int u = edges[edge_idx].first;
            int v = edges[edge_idx].second;
            if (dsu.find(u) != dsu.find(v)) {
                dsu.unite(u, v);
                is_repaired[edge_idx] = true;
                num_components--;
            }
        }
    }

    // Now check non-tree edges
    std::vector<int> non_tree_edges;
    std::vector<std::vector<std::pair<int, int>>> adj(n + 1);
    for (int i = 1; i <= m; ++i) {
        if (is_repaired[i]) {
            adj[edges[i].first].push_back({edges[i].second, i});
            adj[edges[i].second].push_back({edges[i].first, i});
        } else {
            non_tree_edges.push_back(i);
        }
    }

    for (int edge_idx : non_tree_edges) {
        block(edge_idx);
    }
    
    std::vector<std::pair<int, int>> parent(n + 1, {0,0}); // {parent_node, edge_idx_to_parent}

    for (int edge_idx : non_tree_edges) {
        unblock(edge_idx);
        
        int u1 = edges[edge_idx].first;
        int v1 = edges[edge_idx].second;

        // Find path in the spanning tree using BFS
        std::vector<int> q;
        q.push_back(u1);
        std::fill(parent.begin(), parent.end(), std::pair<int,int>{0,0});
        parent[u1] = {u1, 0};
        int head = 0;
        bool found = false;
        while(head < q.size()){
            int curr = q[head++];
            if(curr == v1) {
                found = true;
                break;
            }
            for(auto& edge_pair : adj[curr]){
                int neighbor = edge_pair.first;
                int edge_to_neighbor_idx = edge_pair.second;
                if(parent[neighbor].first == 0){
                    parent[neighbor] = {curr, edge_to_neighbor_idx};
                    q.push_back(neighbor);
                }
            }
        }
        
        int edge_on_path_idx = parent[v1].second;

        block(edge_on_path_idx);
        if (query_connectivity()) {
            is_repaired[edge_idx] = true;
        }
        unblock(edge_on_path_idx);
        
        block(edge_idx);
    }

    for(int edge_idx : non_tree_edges) {
        unblock(edge_idx);
    }

    std::cout << "! ";
    for (int i = 1; i <= m; ++i) {
        std::cout << (is_repaired[i] ? 1 : 0) << (i == m ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}