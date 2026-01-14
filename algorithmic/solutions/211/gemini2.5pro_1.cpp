#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <map>
#include <iomanip>

struct Device {
    std::string id;
    long long x, y;
    char type;
    int index;
};

struct Edge {
    int u, v;
    double cost;
    bool operator<(const Edge& other) const {
        return cost < other.cost;
    }
};

struct DSU {
    std::vector<int> parent;
    std::vector<bool> has_robot;
    DSU(int n, const std::vector<Device>& devices) {
        parent.resize(n);
        has_robot.resize(n);
        for (int i = 0; i < n; ++i) {
            parent[i] = i;
            if (devices[i].type == 'R' || devices[i].type == 'S') {
                has_robot[i] = true;
            } else {
                has_robot[i] = false;
            }
        }
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
            // A small optimization for DSU, not strictly necessary for correctness
            if (root_i < root_j) std::swap(root_i, root_j);
            parent[root_j] = root_i;
            has_robot[root_i] = has_robot[root_i] || has_robot[root_j];
        }
    }
};

long long dist_sq(const Device& a, const Device& b) {
    return (a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y);
}

double calculate_cost(const Device& a, const Device& b, long long d_sq) {
    if ((a.type == 'R' || a.type == 'S') && (b.type == 'R' || b.type == 'S')) {
        if (a.type == 'S' || b.type == 'S') {
            return 0.8 * d_sq;
        } else {
            return 1.0 * d_sq;
        }
    } else {
        return 1.0 * d_sq;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, k;
    std::cin >> n >> k;

    int total_devices = n + k;
    std::vector<Device> devices(total_devices);
    for (int i = 0; i < total_devices; ++i) {
        std::cin >> devices[i].id >> devices[i].x >> devices[i].y >> devices[i].type;
        devices[i].index = i;
    }

    std::vector<Edge> edges;
    for (int i = 0; i < total_devices; ++i) {
        for (int j = i + 1; j < total_devices; ++j) {
            if (devices[i].type == 'C' && devices[j].type == 'C') {
                continue;
            }
            long long d_sq = dist_sq(devices[i], devices[j]);
            double cost = calculate_cost(devices[i], devices[j], d_sq);
            edges.push_back({i, j, cost});
        }
    }

    std::sort(edges.begin(), edges.end());

    DSU dsu(total_devices, devices);
    int robot_components = n;
    std::vector<Edge> result_edges;

    if (n > 0) {
        for (const auto& edge : edges) {
            if (robot_components == 1) {
                break;
            }
            int root_u = dsu.find(edge.u);
            int root_v = dsu.find(edge.v);
            if (root_u != root_v) {
                bool u_has_robot = dsu.has_robot[root_u];
                bool v_has_robot = dsu.has_robot[root_v];

                if (u_has_robot && v_has_robot) {
                    robot_components--;
                }
                dsu.unite(edge.u, edge.v);
                result_edges.push_back(edge);
            }
        }
    }


    std::vector<bool> used_device(total_devices, false);
    for (const auto& edge : result_edges) {
        used_device[edge.u] = true;
        used_device[edge.v] = true;
    }

    std::vector<std::string> used_relays;
    for (int i = 0; i < total_devices; ++i) {
        if (devices[i].type == 'C' && used_device[i]) {
            used_relays.push_back(devices[i].id);
        }
    }
    
    std::sort(used_relays.begin(), used_relays.end());

    if (used_relays.empty()) {
        std::cout << "#\n";
    } else {
        for (size_t i = 0; i < used_relays.size(); ++i) {
            std::cout << used_relays[i] << (i == used_relays.size() - 1 ? "" : "#");
        }
        std::cout << "\n";
    }

    if (result_edges.empty()) {
        // Output nothing for edges if no robots to connect or N=1
    } else {
        for (size_t i = 0; i < result_edges.size(); ++i) {
            std::string id1 = devices[result_edges[i].u].id;
            std::string id2 = devices[result_edges[i].v].id;
            if (id1 > id2) std::swap(id1, id2);
            std::cout << id1 << "-" << id2
                      << (i == result_edges.size() - 1 ? "" : "#");
        }
        std::cout << "\n";
    }

    return 0;
}