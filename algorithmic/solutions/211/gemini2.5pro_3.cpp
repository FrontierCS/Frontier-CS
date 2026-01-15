#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <cmath>
#include <iomanip>
#include <map>
#include <algorithm>
#include <limits>

using namespace std;

// Structure to hold device information
struct Device {
    string id;
    long long x, y;
    char type;
    int internal_id;
};

// Calculate the square of Euclidean distance
long long dist_sq(const Device& a, const Device& b) {
    return (a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y);
}

// Calculate communication cost, multiplied by 10 to use integers
long long get_cost(const Device& a, const Device& b) {
    long long d_sq = dist_sq(a, b);
    if (a.type == 'C' || b.type == 'C') {
        return 10 * d_sq;
    }
    if ((a.type == 'R' && b.type == 'R')) {
        return 10 * d_sq;
    }
    // R-S or S-S
    return 8 * d_sq;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, k;
    cin >> n >> k;

    vector<Device> robots(n);
    vector<Device> relays(k);
    
    int robot_count = 0;
    int relay_count = 0;
    for (int i = 0; i < n + k; ++i) {
        string id;
        long long x, y;
        char type;
        cin >> id >> x >> y >> type;
        if (type == 'R' || type == 'S') {
            robots[robot_count] = {id, x, y, type, robot_count};
            robot_count++;
        } else {
            relays[relay_count] = {id, x, y, type, relay_count};
            relay_count++;
        }
    }

    if (n <= 1) {
        cout << "#" << endl;
        cout << "#" << endl;
        return 0;
    }

    // Modified Prim's algorithm for Steiner Tree
    vector<long long> dist(n, numeric_limits<long long>::max());
    vector<bool> in_tree(n, false);
    vector<int> parent_robot(n, -1);
    vector<int> parent_relay(n, -1);

    vector<long long> min_cost_to_relay(k, numeric_limits<long long>::max());
    vector<int> relay_connector(k, -1);
    
    dist[0] = 0;

    for (int count = 0; count < n; ++count) {
        int u = -1;
        long long min_dist = numeric_limits<long long>::max();

        // Find the robot not in the tree with the minimum connection cost
        for (int i = 0; i < n; ++i) {
            if (!in_tree[i] && dist[i] < min_dist) {
                min_dist = dist[i];
                u = i;
            }
        }

        if (u == -1) break; // Should not happen in a connected graph

        in_tree[u] = true;

        // Update distances for robots not in the tree considering direct connections from u
        for (int v = 0; v < n; ++v) {
            if (!in_tree[v]) {
                long long cost_uv = get_cost(robots[u], robots[v]);
                if (cost_uv < dist[v]) {
                    dist[v] = cost_uv;
                    parent_robot[v] = u;
                    parent_relay[v] = -1;
                }
            }
        }
        
        // Update distances for robots not in the tree considering paths through relays
        for (int i = 0; i < k; ++i) {
            long long cost_ur = get_cost(robots[u], relays[i]);
            // Check if robot u offers a cheaper connection to this relay
            if (cost_ur < min_cost_to_relay[i]) {
                min_cost_to_relay[i] = cost_ur;
                relay_connector[i] = u;

                // If relay connection is cheaper, it might provide cheaper paths to other robots
                for (int v = 0; v < n; ++v) {
                    if (!in_tree[v]) {
                        long long path_cost = min_cost_to_relay[i] + get_cost(relays[i], robots[v]);
                        if (path_cost < dist[v]) {
                            dist[v] = path_cost;
                            parent_robot[v] = -1;
                            parent_relay[v] = i;
                        }
                    }
                }
            }
        }
    }

    // Reconstruct the solution from parent pointers
    vector<pair<int, int>> mst_edges;
    vector<bool> used_relays(k, false);

    for (int i = 0; i < n; ++i) {
        if (parent_robot[i] != -1) {
            mst_edges.push_back({i, parent_robot[i]});
        } else if (parent_relay[i] != -1) {
            int relay_idx = parent_relay[i];
            mst_edges.push_back({i, n + relay_idx});
            used_relays[relay_idx] = true;
        }
    }

    for (int i = 0; i < k; ++i) {
        if (used_relays[i]) {
            mst_edges.push_back({n + i, relay_connector[i]});
        }
    }
    
    // Format output
    stringstream selected_relays_ss;
    bool first_relay = true;
    for (int i = 0; i < k; ++i) {
        if (used_relays[i]) {
            if (!first_relay) {
                selected_relays_ss << "#";
            }
            selected_relays_ss << relays[i].id;
            first_relay = false;
        }
    }
    if (first_relay) {
        selected_relays_ss << "#";
    }

    stringstream links_ss;
    bool first_link = true;
    for (const auto& edge : mst_edges) {
        if (!first_link) {
            links_ss << "#";
        }
        string id1 = (edge.first < n) ? robots[edge.first].id : relays[edge.first - n].id;
        string id2 = (edge.second < n) ? robots[edge.second].id : relays[edge.second - n].id;
        links_ss << id1 << "-" << id2;
        first_link = false;
    }
    if (first_link) {
        links_ss << "#";
    }

    cout << selected_relays_ss.str() << endl;
    cout << links_ss.str() << endl;

    return 0;
}