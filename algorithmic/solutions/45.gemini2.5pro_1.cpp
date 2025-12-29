#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <queue>
#include <numeric>
#include <random>
#include <chrono>
#include <unordered_map>

using namespace std;

// Globals
int N_nodes, M_edges, K_parts;
double EPS;
vector<vector<int>> adj;
vector<int> p_assignment;
long long max_part_size;

// Buffers for BFS to avoid reallocations
vector<int> q_bfs_nodes;
vector<int> dist_bfs;
vector<bool> visited_bfs;
vector<bool> in_group_bfs;

// BFS to find the farthest node from a starting point within a given set of nodes
int bfs_farthest(int start_node, const vector<int>& nodes) {
    if (nodes.empty()) return -1;
    
    for (int node : nodes) in_group_bfs[node] = true;

    q_bfs_nodes.clear();
    for(int node : nodes) visited_bfs[node] = false;

    q_bfs_nodes.push_back(start_node);
    visited_bfs[start_node] = true;
    dist_bfs[start_node] = 0;
    int head = 0;

    int farthest_node = start_node;
    int max_dist = 0;

    while(head < q_bfs_nodes.size()){
        int u = q_bfs_nodes[head++];
        if(dist_bfs[u] > max_dist) {
            max_dist = dist_bfs[u];
            farthest_node = u;
        }

        for(int v : adj[u]){
            if(in_group_bfs[v] && !visited_bfs[v]){
                visited_bfs[v] = true;
                dist_bfs[v] = dist_bfs[u] + 1;
                q_bfs_nodes.push_back(v);
            }
        }
    }

    for (int node : nodes) in_group_bfs[node] = false;
    return farthest_node;
}

// Bisection of a group of vertices using two-seed BFS
pair<vector<int>, vector<int>> bisect(const vector<int>& vertices, mt19937& g) {
    if (vertices.size() <= 1) {
        if (vertices.empty()) return {{}, {}};
        return {{vertices[0]}, {}};
    }

    uniform_int_distribution<size_t> dist(0, vertices.size() - 1);

    int r = vertices[dist(g)];
    int s1 = bfs_farthest(r, vertices);
    int s2 = bfs_farthest(s1, vertices);

    if (s1 == s2) {
        size_t idx = dist(g);
        s2 = vertices[idx];
        while (vertices.size() > 1 && s1 == s2) {
            idx = (idx + 1) % vertices.size();
            s2 = vertices[idx];
        }
    }
    
    vector<int> part1, part2;
    vector<int> owner(N_nodes + 1, 0); // 0: unassigned, 1: part1, 2: part2
    queue<int> q1, q2;

    part1.push_back(s1); owner[s1] = 1; q1.push(s1);
    if (s1 != s2) {
        part2.push_back(s2); owner[s2] = 2; q2.push(s2);
    }
    
    for (int node : vertices) in_group_bfs[node] = true;

    size_t target_size1 = vertices.size() / 2;

    while (!q1.empty() || !q2.empty()) {
        bool progress = false;
        if (!q1.empty() && part1.size() < target_size1) {
            int u = q1.front(); q1.pop();
            for (int v : adj[u]) {
                if (in_group_bfs[v] && owner[v] == 0) {
                    owner[v] = 1; part1.push_back(v); q1.push(v);
                }
            }
            progress = true;
        }

        if (!q2.empty()) {
            int u = q2.front(); q2.pop();
            for (int v : adj[u]) {
                if (in_group_bfs[v] && owner[v] == 0) {
                    owner[v] = 2; part2.push_back(v); q2.push(v);
                }
            }
            progress = true;
        }
        if (!progress) break;
    }
    
    for (int v : vertices) {
        if (owner[v] == 0) {
            if (part1.size() < target_size1) {
                part1.push_back(v);
            } else {
                part2.push_back(v);
            }
        }
    }
    for (int node : vertices) in_group_bfs[node] = false;

    return {part1, part2};
}

// Local refinement phase to improve the partition
void refine(mt19937& g) {
    vector<long long> part_sizes(K_parts + 1, 0);
    for (int i = 1; i <= N_nodes; ++i) {
        part_sizes[p_assignment[i]]++;
    }
    
    vector<int> nodes(N_nodes);
    iota(nodes.begin(), nodes.end(), 1);
    
    unordered_map<int, int> conn_parts;
    
    for (int iter = 0; iter < 4; ++iter) {
        bool changed = false;
        shuffle(nodes.begin(), nodes.end(), g);

        for (int u : nodes) {
            int old_part = p_assignment[u];
            if (part_sizes[old_part] == 1) continue;

            conn_parts.clear();
            for (int v : adj[u]) {
                conn_parts[p_assignment[v]]++;
            }

            int current_internal_conn = conn_parts[old_part];
            int best_part = old_part;
            int max_conn = -1;

            for (auto const& [part_id, count] : conn_parts) {
                if (part_id == old_part) continue;
                if (part_sizes[part_id] + 1 > max_part_size) continue;
                
                if (count > max_conn) {
                    max_conn = count;
                    best_part = part_id;
                } else if (count == max_conn) {
                    if (part_sizes[part_id] < part_sizes[best_part]) {
                        best_part = part_id;
                    }
                }
            }

            if (max_conn > current_internal_conn) {
                part_sizes[old_part]--;
                part_sizes[best_part]++;
                p_assignment[u] = best_part;
                changed = true;
            }
        }
        if (!changed) break;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    mt19937 g(chrono::high_resolution_clock::now().time_since_epoch().count());

    cin >> N_nodes >> M_edges >> K_parts >> EPS;
    
    adj.resize(N_nodes + 1);
    for (int i = 0; i < M_edges; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for(int i=1; i<=N_nodes; ++i){
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }
    
    q_bfs_nodes.reserve(N_nodes);
    dist_bfs.resize(N_nodes + 1);
    visited_bfs.resize(N_nodes + 1);
    in_group_bfs.resize(N_nodes + 1, false);

    p_assignment.resize(N_nodes + 1);

    queue<pair<vector<int>, vector<int>>> q;
    vector<int> all_nodes(N_nodes);
    iota(all_nodes.begin(), all_nodes.end(), 1);
    vector<int> all_parts(K_parts);
    iota(all_parts.begin(), all_parts.end(), 1);

    q.push({all_nodes, all_parts});

    while (!q.empty()) {
        vector<int> current_vertices = q.front().first;
        vector<int> current_parts = q.front().second;
        q.pop();

        if (current_parts.size() == 1) {
            int part_id = current_parts[0];
            for (int v : current_vertices) {
                p_assignment[v] = part_id;
            }
            continue;
        }
        
        if (current_vertices.empty()){
            size_t mid = current_parts.size() / 2;
            vector<int> p1(current_parts.begin(), current_parts.begin() + mid);
            vector<int> p2(current_parts.begin() + mid, current_parts.end());
            q.push({{}, p1});
            q.push({{}, p2});
            continue;
        }

        auto [g1, g2] = bisect(current_vertices, g);

        size_t mid = current_parts.size() / 2;
        vector<int> p1(current_parts.begin(), current_parts.begin() + mid);
        vector<int> p2(current_parts.begin() + mid, current_parts.end());
        q.push({g1, p1});
        q.push({g2, p2});
    }

    long long ideal_size = (N_nodes + K_parts - 1) / K_parts;
    max_part_size = floor((1 + EPS) * ideal_size);

    refine(g);
    
    for (int i = 1; i <= N_nodes; ++i) {
        cout << p_assignment[i] << (i == N_nodes ? "" : " ");
    }
    cout << "\n";

    return 0;
}