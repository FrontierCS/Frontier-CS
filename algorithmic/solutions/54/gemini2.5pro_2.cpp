#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

int n;
map<pair<int, int>, int> memo;

int ask(int u, int v) {
    if (u == v) return 0;
    if (u > v) swap(u, v);
    if (memo.count({u, v})) return memo[{u, v}];
    cout << "? " << u << " " << v << endl;
    int d;
    cin >> d;
    if (d == -1) exit(0); // Should not happen with correct interaction
    return memo[{u, v}] = d;
}

void answer(int c) {
    cout << "! " << c << endl;
}

// Get distances from u to a subset of nodes
vector<int> get_dists_subset(int u, const vector<int>& nodes) {
    vector<int> dists(n + 1, -1);
    for (int v : nodes) {
        dists[v] = ask(u, v);
    }
    return dists;
}

// Find farthest node from u in a subset
int find_farthest(int u, const vector<int>& nodes, const vector<int>& dists_u) {
    int farthest_node = -1;
    int max_dist = -1;
    for (int v : nodes) {
        if (dists_u[v] > max_dist) {
            max_dist = dists_u[v];
            farthest_node = v;
        }
    }
    return farthest_node;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;
    
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    int attachment_node = -1;
    long long outer_weight = 0;

    while (candidates.size() > 1) {
        // Find diameter of the graph induced by `candidates`
        int start_node = candidates[0];
        auto dists_start = get_dists_subset(start_node, candidates);
        int l1 = find_farthest(start_node, candidates, dists_start);

        auto dists_l1 = get_dists_subset(l1, candidates);
        int l2 = find_farthest(l1, candidates, dists_l1);
        
        auto dists_l2 = get_dists_subset(l2, candidates);
        int diameter = dists_l1[l2];

        if (diameter == 0) { // All nodes are the same or disconnected, implies single node
             break;
        }
        
        // Project outer component onto the new diameter
        int current_attachment_on_diameter = -1;
        if (attachment_node != -1) {
            int d_l1_p = ask(attachment_node, l1);
            int d_l2_p = ask(attachment_node, l2);
            int proj_dist_p = (d_l1_p - d_l2_p + diameter) / 2;
            
            for (int u : candidates) {
                if (dists_l1[u] + dists_l2[u] == diameter && dists_l1[u] == proj_dist_p) {
                    current_attachment_on_diameter = u;
                    break;
                }
            }
        }

        // Partition candidate nodes based on their projection on the diameter
        map<int, vector<int>> projections;
        vector<int> proj_dists_keys;
        map<int, int> diameter_nodes; // dist from l1 -> node_id

        for (int u : candidates) {
            if (dists_l1[u] + dists_l2[u] == diameter) {
                diameter_nodes[dists_l1[u]] = u;
            }
            int proj_dist = (dists_l1[u] - dists_l2[u] + diameter) / 2;
            if (projections.find(proj_dist) == projections.end()) {
                proj_dists_keys.push_back(proj_dist);
            }
            projections[proj_dist].push_back(u);
        }
        sort(proj_dists_keys.begin(), proj_dists_keys.end());
        
        // Calculate component sizes, including the outer weighted component
        map<int, long long> component_sizes;
        for (auto const& [dist, p_group] : projections) {
            component_sizes[dist] = p_group.size();
        }

        if (current_attachment_on_diameter != -1) {
             int attach_proj_dist = dists_l1[current_attachment_on_diameter];
             component_sizes[attach_proj_dist] += outer_weight;
        }

        // Find the median component
        long long total_nodes = candidates.size() + outer_weight;
        long long left_sum = 0;
        int median_proj_dist = -1;

        for (int p_dist : proj_dists_keys) {
            long long s = component_sizes[p_dist];
            if (left_sum * 2 < total_nodes && (left_sum + s) * 2 >= total_nodes) {
                median_proj_dist = p_dist;
                break;
            }
            left_sum += s;
        }
        if (median_proj_dist == -1) {
             median_proj_dist = proj_dists_keys.back();
        }

        // Recurse on the median component
        outer_weight = total_nodes - projections[median_proj_dist].size();
        attachment_node = diameter_nodes[median_proj_dist];
        candidates = projections[median_proj_dist];
    }
    
    answer(candidates[0]);

    return 0;
}