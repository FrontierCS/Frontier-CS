#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Global variables for graph data and partitioning state
int n_nodes, n_edges, k_parts;
double epsilon;
vector<vector<int>> adj_list;
vector<int> node_partition;
int max_partition_size;

// A single, reusable random number generator
mt19937& get_rng() {
    static mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    return rng;
}

// The core recursive bisection logic for initial partitioning
void recursive_bisection(vector<int>& nodes, int k_rem, int part_offset) {
    if (k_rem == 1) {
        for (int node : nodes) {
            node_partition[node] = part_offset + 1;
        }
        return;
    }

    if (nodes.empty()) {
        return;
    }

    // Partition the current set of nodes into two halves, A and B.
    // We use BFS starting from random nodes to find a good cut.
    // This tends to keep connected components together.
    vector<int> part_A, part_B;
    
    // Flags to manage the partitioning process
    vector<bool> is_in_subgraph(n_nodes + 1, false);
    for (int node : nodes) {
        is_in_subgraph[node] = true;
    }
    vector<bool> visited_bfs(n_nodes + 1, false);
    vector<bool> is_in_A(n_nodes + 1, false);
    
    size_t target_A_size = nodes.size() / 2;

    // Handle disconnected components by trying multiple start nodes
    for (int start_node : nodes) {
        if (part_A.size() >= target_A_size) break;
        if (!visited_bfs[start_node]) {
            vector<int> q;
            q.push_back(start_node);
            visited_bfs[start_node] = true;

            int head = 0;
            while(head < q.size() && part_A.size() < target_A_size) {
                int u = q[head++];
                part_A.push_back(u);
                is_in_A[u] = true;

                for (int v : adj_list[u]) {
                    if (is_in_subgraph[v] && !visited_bfs[v]) {
                        visited_bfs[v] = true;
                        q.push_back(v);
                    }
                }
            }
        }
    }
    
    // Assign all remaining nodes to part B
    for (int node : nodes) {
        if (!is_in_A[node]) {
            part_B.push_back(node);
        }
    }

    // Recurse on the two new subproblems
    recursive_bisection(part_A, k_rem / 2, part_offset);
    recursive_bisection(part_B, k_rem / 2, part_offset + k_rem / 2);
}

// Wrapper for the initial partitioning step
void perform_initial_partition() {
    vector<int> all_nodes(n_nodes);
    iota(all_nodes.begin(), all_nodes.end(), 1);
    shuffle(all_nodes.begin(), all_nodes.end(), get_rng());
    recursive_bisection(all_nodes, k_parts, 0);
}

// Greedy local search refinement for the final k-way partition
void refine_partition() {
    vector<int> part_sizes(k_parts + 1, 0);
    for (int i = 1; i <= n_nodes; ++i) {
        part_sizes[node_partition[i]]++;
    }

    vector<int> nodes(n_nodes);
    iota(nodes.begin(), nodes.end(), 1);
    
    // Heuristic weight for the communication volume proxy. Average degree is a common choice.
    const double CV_WEIGHT = (n_nodes > 0) ? (2.0 * n_edges / n_nodes) : 1.0;

    const int MAX_ITERATIONS = 5;
    bool changed_in_last_pass = true;

    // Temporary storage for gain calculation, pre-allocated to be fast
    vector<int> d_counts(k_parts + 1);
    vector<bool> n_counts(k_parts + 1);

    for (int iter = 0; iter < MAX_ITERATIONS && changed_in_last_pass; ++iter) {
        changed_in_last_pass = false;
        shuffle(nodes.begin(), nodes.end(), get_rng());
        
        for (int u : nodes) {
            int old_part = node_partition[u];
            if (part_sizes[old_part] == 1) continue;

            fill(d_counts.begin(), d_counts.end(), 0);
            fill(n_counts.begin(), n_counts.end(), false);
            for (int v : adj_list[u]) {
                d_counts[node_partition[v]]++;
                n_counts[node_partition[v]] = true;
            }

            int best_part = -1;
            double max_gain = 1e-9; // Only move for strictly positive gain to avoid cycles

            double current_ec_term = d_counts[old_part];
            double current_cv_term = n_counts[old_part] ? 1.0 : 0.0;
            
            for (int new_part = 1; new_part <= k_parts; ++new_part) {
                if (new_part == old_part) continue;

                if (part_sizes[new_part] + 1 <= max_partition_size) {
                    double new_ec_term = d_counts[new_part];
                    double new_cv_term = n_counts[new_part] ? 1.0 : 0.0;
                    
                    // Gain = -delta_EC - C * delta_F(v)
                    // We want to maximize this gain.
                    double gain = (new_ec_term - current_ec_term) + CV_WEIGHT * (new_cv_term - current_cv_term);
                    
                    if (gain > max_gain) {
                        max_gain = gain;
                        best_part = new_part;
                    }
                }
            }

            if (best_part != -1) {
                part_sizes[old_part]--;
                part_sizes[best_part]++;
                node_partition[u] = best_part;
                changed_in_last_pass = true;
            }
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int m_in;
    cin >> n_nodes >> m_in >> k_parts >> epsilon;

    adj_list.resize(n_nodes + 1);
    vector<pair<int, int>> edges;
    edges.reserve(m_in);
    for (int i = 0; i < m_in; ++i) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
            if (u > v) swap(u, v);
            edges.push_back({u, v});
        }
    }

    // Simplify graph: remove parallel edges
    sort(edges.begin(), edges.end());
    edges.erase(unique(edges.begin(), edges.end()), edges.end());
    
    n_edges = edges.size();
    for(const auto& edge : edges) {
        adj_list[edge.first].push_back(edge.second);
        adj_list[edge.second].push_back(edge.first);
    }
    edges.clear();
    edges.shrink_to_fit();

    // Calculate balance constraint
    double ideal_size = ceil((double)n_nodes / k_parts);
    max_partition_size = floor((1 + epsilon) * ideal_size);

    node_partition.resize(n_nodes + 1);

    // Step 1: Initial partition using recursive bisection
    perform_initial_partition();

    // Step 2: Refine the partition using a greedy local search heuristic
    refine_partition();

    // Output the final partition
    for (int i = 1; i <= n_nodes; ++i) {
        cout << node_partition[i] << (i == n_nodes ? "" : " ");
    }
    cout << endl;

    return 0;
}