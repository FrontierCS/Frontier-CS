#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <set>
#include <map>

void setup_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

struct Node {
    int id;
    long long x, y;
    char type;
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
    std::vector<int> sz;
    std::vector<bool> has_robot_in_comp;

    DSU(int n, int num_robots) {
        parent.resize(n);
        sz.assign(n, 1);
        has_robot_in_comp.assign(n, false);
        for (int i = 0; i < n; ++i) {
            parent[i] = i;
        }
        for (int i = 0; i < num_robots; ++i) {
            has_robot_in_comp[i] = true;
        }
    }

    int find(int i) {
        if (parent[i] == i) {
            return i;
        }
        return parent[i] = find(parent[i]);
    }

    bool unite(int i, int j, int& robot_sets) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            bool i_had_robot = has_robot_in_comp[root_i];
            bool j_had_robot = has_robot_in_comp[root_j];

            if (sz[root_i] < sz[root_j]) {
                std::swap(root_i, root_j);
            }
            parent[root_j] = root_i;
            sz[root_i] += sz[root_j];
            has_robot_in_comp[root_i] = has_robot_in_comp[root_i] || has_robot_in_comp[root_j];

            if (i_had_robot && j_had_robot) {
                robot_sets--;
            }
            return true;
        }
        return false;
    }
};

long long distSq(const Node& a, const Node& b) {
    return (a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y);
}

int main() {
    setup_io();

    int N_in, K_in;
    std::cin >> N_in >> K_in;
    int total_nodes = N_in + K_in;

    std::vector<Node> robots;
    std::vector<Node> relays;

    for (int i = 0; i < total_nodes; ++i) {
        Node current_node;
        std::cin >> current_node.id >> current_node.x >> current_node.y >> current_node.type;
        if (current_node.type == 'C') {
            relays.push_back(current_node);
        } else {
            robots.push_back(current_node);
        }
    }

    int N = robots.size();
    int K = relays.size();

    std::vector<Node> nodes;
    nodes.insert(nodes.end(), robots.begin(), robots.end());
    nodes.insert(nodes.end(), relays.begin(), relays.end());

    std::vector<Edge> edges;
    for (int i = 0; i < N + K; ++i) {
        for (int j = i + 1; j < N + K; ++j) {
            if (nodes[i].type == 'C' && nodes[j].type == 'C') {
                continue;
            }
            
            long long d_sq = distSq(nodes[i], nodes[j]);
            double cost = static_cast<double>(d_sq);

            if (nodes[i].type != 'C' && nodes[j].type != 'C') {
                if (nodes[i].type == 'S' || nodes[j].type == 'S') {
                    cost *= 0.8;
                }
            }
            edges.push_back({i, j, cost});
        }
    }

    std::sort(edges.begin(), edges.end());

    DSU dsu(N + K, N);
    int robot_sets = N;
    
    std::vector<Edge> result_edges;

    if (N > 0) {
        for (const auto& edge : edges) {
            if (robot_sets == 1) {
                break;
            }
            if (dsu.unite(edge.u, edge.v, robot_sets)) {
                result_edges.push_back(edge);
            }
        }
    }
    
    std::set<int> used_relays;
    std::vector<std::pair<int, int>> links;

    for (const auto& edge : result_edges) {
        if (nodes[edge.u].type == 'C') used_relays.insert(nodes[edge.u].id);
        if (nodes[edge.v].type == 'C') used_relays.insert(nodes[edge.v].id);
        
        int u_id = nodes[edge.u].id;
        int v_id = nodes[edge.v].id;
        if (u_id > v_id) std::swap(u_id, v_id);
        links.push_back({u_id, v_id});
    }

    if (used_relays.empty()) {
        std::cout << "#\n";
    } else {
        bool first = true;
        for (int id : used_relays) {
            if (!first) std::cout << "#";
            std::cout << id;
            first = false;
        }
        std::cout << "\n";
    }

    if (links.empty()) {
        std::cout << "#\n";
    } else {
        bool first = true;
        for (const auto& p : links) {
            if (!first) std::cout << "#";
            std::cout << p.first << "-" << p.second;
            first = false;
        }
        std::cout << "\n";
    }

    return 0;
}