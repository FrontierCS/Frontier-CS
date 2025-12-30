#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <queue>
#include <random>
#include <chrono>
#include <utility>

using namespace std;

// Global variables
int n_nodes, m_edges, k_parts;
double balance_eps;
vector<vector<int>> adj;
vector<int> partition_map;

// RNG for shuffling
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// BFS on the induced subgraph to find the farthest node from a starting point
int induced_bfs(int start_node, const vector<bool>& in_current_nodes) {
    queue<pair<int, int>> q;
    q.push({start_node, 0});
    vector<int> dist(n_nodes + 1, -1);
    dist[start_node] = 0;
    int farthest_node = start_node;
    int max_dist = 0;

    while (!q.empty()) {
        pair<int, int> curr = q.front();
        q.pop();
        int u = curr.first;
        int d = curr.second;

        if (d > max_dist) {
            max_dist = d;
            farthest_node = u;
        }

        for (int v : adj[u]) {
            if (in_current_nodes[v] && dist[v] == -1) {
                dist[v] = d + 1;
                q.push({v, d + 1});
            }
        }
    }
    return farthest_node;
}

vector<int>::iterator bisect(vector<int>::iterator begin, vector<int>::iterator end) {
    int num_nodes = distance(begin, end);
    if (num_nodes <= 1) {
        return begin + num_nodes;
    }

    vector<bool> in_current_nodes(n_nodes + 1, false);
    for (auto it = begin; it != end; ++it) {
        in_current_nodes[*it] = true;
    }

    // --- Seed selection ---
    int s1 = *begin;
    s1 = induced_bfs(s1, in_current_nodes);
    int s2 = induced_bfs(s1, in_current_nodes);
    
    // --- Initial Partition using BFS growth ---
    vector<int> sub_part(n_nodes + 1, 0); // 0: not in set, 1: part 1, 2: part 2
    queue<int> q1;

    if (s1 != s2) {
        q1.push(s1); sub_part[s1] = 1;
        sub_part[s2] = 2;
    } else {
        q1.push(s1); sub_part[s1] = 1;
        for(auto it = begin; it != end; ++it) {
            if (*it != s1) {
                s2 = *it;
                sub_part[s2] = 2;
                break;
            }
        }
    }
    
    int c1 = 1, c2 = 1;
    if (s1 == s2) c2 = 0;

    int target1_size = num_nodes / 2;

    while (!q1.empty() && c1 < target1_size) {
        int u = q1.front(); q1.pop();
        for (int v : adj[u]) {
            if (in_current_nodes[v] && sub_part[v] == 0) {
                sub_part[v] = 1;
                q1.push(v);
                c1++;
                if (c1 == target1_size) break;
            }
        }
        if (c1 == target1_size) break;
    }
    
    for (auto it = begin; it != end; ++it) {
        if (sub_part[*it] == 0) {
            sub_part[*it] = 2;
            c2++;
        }
    }

    // --- Refinement ---
    vector<int> current_nodes_vec(begin, end);
    for (int pass = 0; pass < 2; ++pass) {
        bool changed = false;
        shuffle(current_nodes_vec.begin(), current_nodes_vec.end(), rng);
        for (int u : current_nodes_vec) {
            int internal_cost = 0, external_cost = 0;
            for (int v : adj[u]) {
                if (in_current_nodes[v]) {
                    if (sub_part[v] == sub_part[u]) internal_cost++;
                    else if(sub_part[v] != 0) external_cost++;
                }
            }
            int gain = external_cost - internal_cost;

            if (gain > 0) {
                if (sub_part[u] == 1) { c1--; c2++; } else { c2--; c1++; }
                sub_part[u] = 3 - sub_part[u];
                changed = true;
            }
        }
        if (!changed) break;
    }

    // --- Rebalancing ---
    int surplus1 = c1 - num_nodes / 2;
    if (surplus1 > 0) {
        vector<pair<int, int>> gains;
        for (auto it = begin; it != end; ++it) {
            if (sub_part[*it] == 1) {
                int u = *it;
                int internal_cost = 0, external_cost = 0;
                for (int v : adj[u]) {
                    if(in_current_nodes[v]) {
                        if (sub_part[v] == 1) internal_cost++;
                        else if (sub_part[v] == 2) external_cost++;
                    }
                }
                gains.push_back({external_cost - internal_cost, u});
            }
        }
        partial_sort(gains.begin(), gains.begin() + surplus1, gains.end(), greater<pair<int,int>>());
        for (int i = 0; i < surplus1; ++i) {
            sub_part[gains[i].second] = 2;
        }
    }

    int surplus2 = c2 - (num_nodes - num_nodes / 2);
    if (surplus2 > 0) {
        vector<pair<int, int>> gains;
        for (auto it = begin; it != end; ++it) {
            if (sub_part[*it] == 2) {
                int u = *it;
                int internal_cost = 0, external_cost = 0;
                for (int v : adj[u]) {
                    if(in_current_nodes[v]) {
                        if (sub_part[v] == 2) internal_cost++;
                        else if (sub_part[v] == 1) external_cost++;
                    }
                }
                gains.push_back({external_cost - internal_cost, u});
            }
        }
        partial_sort(gains.begin(), gains.begin() + surplus2, gains.end(), greater<pair<int,int>>());
        for (int i = 0; i < surplus2; ++i) {
            sub_part[gains[i].second] = 1;
        }
    }

    return partition(begin, end, [&](int node) {
        return sub_part[node] == 1;
    });
}

void recursive_partition(vector<int>::iterator begin, vector<int>::iterator end, int k, int part_id_offset) {
    if (k == 1) {
        for (auto it = begin; it != end; ++it) {
            partition_map[*it] = part_id_offset + 1;
        }
        return;
    }
    if (begin == end) return;

    auto mid = bisect(begin, end);

    recursive_partition(begin, mid, k / 2, part_id_offset);
    recursive_partition(mid, end, k / 2, part_id_offset + k / 2);
}

void solve() {
    vector<int> all_nodes(n_nodes);
    iota(all_nodes.begin(), all_nodes.end(), 1);

    partition_map.resize(n_nodes + 1);
    recursive_partition(all_nodes.begin(), all_nodes.end(), k_parts, 0);

    for (int i = 1; i <= n_nodes; ++i) {
        cout << partition_map[i] << (i == n_nodes ? "" : " ");
    }
    cout << "\n";
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n_nodes >> m_edges >> k_parts >> balance_eps;

    adj.resize(n_nodes + 1);
    vector<pair<int, int>> edge_list;
    edge_list.reserve(m_edges);

    for (int i = 0; i < m_edges; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        if (u > v) swap(u, v);
        edge_list.push_back({u, v});
    }

    sort(edge_list.begin(), edge_list.end());
    edge_list.erase(unique(edge_list.begin(), edge_list.end()), edge_list.end());

    for (const auto& edge : edge_list) {
        adj[edge.first].push_back(edge.second);
        adj[edge.second].push_back(edge.first);
    }

    solve();

    return 0;
}