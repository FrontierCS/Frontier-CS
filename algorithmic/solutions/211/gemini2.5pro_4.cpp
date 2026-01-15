#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <set>
#include <queue>

// A struct to hold all information about a device.
struct Device {
    std::string id;
    long long x, y;
    char type;
};

// A struct representing a potential communication link (an edge in the graph).
struct Edge {
    int u, v;
    double cost;

    bool operator<(const Edge& other) const {
        return cost < other.cost;
    }
};

// Disjoint Set Union (DSU) data structure with path compression and union by size.
// It's augmented to track whether a component contains at least one robot.
struct DSU {
    std::vector<int> parent;
    std::vector<int> sz;
    std::vector<bool> has_robot;

    DSU(int n, const std::vector<Device>& devices) {
        parent.resize(n);
        std::iota(parent.begin(), parent.end(), 0);
        sz.assign(n, 1);
        has_robot.resize(n);
        for (int i = 0; i < n; ++i) {
            has_robot[i] = (devices[i].type != 'C');
        }
    }

    int find(int i) {
        if (parent[i] == i) return i;
        return parent[i] = find(parent[i]);
    }

    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            if (sz[root_i] < sz[root_j]) std::swap(root_i, root_j);
            parent[root_j] = root_i;
            sz[root_i] += sz[root_j];
            has_robot[root_i] = has_robot[root_i] || has_robot[root_j];
        }
    }
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, k;
    std::cin >> n >> k;

    int total_devices = n + k;
    std::vector<Device> devices(total_devices);
    int first_robot_idx = -1;
    for (int i = 0; i < total_devices; ++i) {
        std::cin >> devices[i].id >> devices[i].x >> devices[i].y >> devices[i].type;
        if (devices[i].type != 'C' && first_robot_idx == -1) {
            first_robot_idx = i;
        }
    }

    std::vector<Edge> edges;
    if (total_devices > 1) {
        edges.reserve((long long)total_devices * (total_devices - 1) / 2);
    }
    for (int i = 0; i < total_devices; ++i) {
        for (int j = i + 1; j < total_devices; ++j) {
            const auto& d1 = devices[i];
            const auto& d2 = devices[j];
            if (d1.type == 'C' && d2.type == 'C') continue;

            long long dx = d1.x - d2.x;
            long long dy = d1.y - d2.y;
            long long dist_sq = dx * dx + dy * dy;

            double cost;
            if (d1.type == 'C' || d2.type == 'C') cost = 1.0 * dist_sq;
            else if (d1.type == 'S' || d2.type == 'S') cost = 0.8 * dist_sq;
            else cost = 1.0 * dist_sq;
            edges.push_back({i, j, cost});
        }
    }

    std::sort(edges.begin(), edges.end());

    DSU dsu(total_devices, devices);
    std::vector<Edge> initial_mst_edges;
    int num_robot_components = n;

    if (n > 1) {
        for (const auto& edge : edges) {
            int root_u = dsu.find(edge.u);
            int root_v = dsu.find(edge.v);
            if (root_u != root_v) {
                bool u_has_robot = dsu.has_robot[root_u];
                bool v_has_robot = dsu.has_robot[root_v];
                dsu.unite(edge.u, edge.v);
                initial_mst_edges.push_back(edge);
                if (u_has_robot && v_has_robot) {
                    num_robot_components--;
                    if (num_robot_components <= 1) break;
                }
            }
        }
    }

    std::set<std::string> used_relays;
    std::vector<std::string> final_links;

    if (n > 1) {
        std::vector<std::vector<int>> adj(total_devices);
        for(const auto& edge : initial_mst_edges) {
            adj[edge.u].push_back(edge.v);
            adj[edge.v].push_back(edge.u);
        }

        std::vector<bool> visited(total_devices, false);
        std::queue<int> q;
        
        q.push(first_robot_idx);
        visited[first_robot_idx] = true;

        while(!q.empty()){
            int u = q.front();
            q.pop();

            if(devices[u].type == 'C') {
                used_relays.insert(devices[u].id);
            }

            for(int v : adj[u]) {
                if(!visited[v]) {
                    visited[v] = true;
                    q.push(v);
                    final_links.push_back(devices[u].id + "-" + devices[v].id);
                }
            }
        }
    }

    if (used_relays.empty()) {
        std::cout << "#\n";
    } else {
        bool first = true;
        for (const auto& id : used_relays) {
            if (!first) std::cout << "#";
            std::cout << id;
            first = false;
        }
        std::cout << "\n";
    }

    if (final_links.empty()) {
        std::cout << "\n";
    } else {
        for (size_t i = 0; i < final_links.size(); ++i) {
            std::cout << final_links[i] << (i == final_links.size() - 1 ? "" : "#");
        }
        std::cout << "\n";
    }

    return 0;
}