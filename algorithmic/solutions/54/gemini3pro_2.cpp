#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <cmath>
#include <random>
#include <set>

using namespace std;

// Wrapper for query interaction
int query(int u, int v) {
    cout << "? " << u << " " << v << endl;
    int d;
    cin >> d;
    return d;
}

int n;
vector<int> depth;
vector<vector<int>> levels;
// Cache or just counts? The problem doesn't allow adaptive queries so cache is valid but 
// we mostly query new pairs. We'll implement direct queries.

int get_dist(int u, int v) {
    if (u == v) return 0;
    return query(u, v);
}

// Calculate LCA depth using distance query and depths from root (node 1)
int get_lca_depth(int u, int v) {
    if (u == v) return depth[u];
    // Formula: dist(u, v) = depth[u] + depth[v] - 2 * depth[LCA(u, v)]
    // => 2 * depth[LCA] = depth[u] + depth[v] - dist(u, v)
    int d = get_dist(u, v);
    return (depth[u] + depth[v] - d) / 2;
}

mt19937 rng(1337);

// Estimate if the ancestor of R at target_depth has subtree size >= n/2
// Uses random sampling.
bool is_heavy(int R, int target_depth, int samples_count = 35) {
    int count = 0;
    for (int i = 0; i < samples_count; ++i) {
        int u = uniform_int_distribution<int>(1, n)(rng);
        // Check if u is in the subtree of the node defined by (R, target_depth)
        // Condition: LCA(u, R) depth >= target_depth
        int lca_d = get_lca_depth(u, R);
        if (lca_d >= target_depth) {
            count++;
        }
    }
    // Threshold n/2.
    // Use slightly loose threshold to account for variance, but centroid property is >= n/2.
    // 0.45 allows catching it even if slightly unlucky.
    return (double)count / samples_count >= 0.45;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    depth.resize(n + 1);
    levels.resize(n + 1);
    depth[1] = 0;
    levels[0].push_back(1);

    // 1. Get depths of all nodes relative to node 1 (arbitrary root)
    // This costs N-1 queries.
    for (int i = 2; i <= n; ++i) {
        depth[i] = get_dist(1, i);
        levels[depth[i]].push_back(i);
    }

    int curr_R = uniform_int_distribution<int>(1, n)(rng); 
    int curr_depth = 0; // Current known heavy ancestor depth

    while (true) {
        // 2. Binary search on path 1...curr_R for the deepest heavy node
        // We know the heavy path starts at 1 (depth 0). 
        // We search in range [curr_depth, depth[curr_R]].
        int L = curr_depth;
        int H = depth[curr_R];
        int ans = curr_depth;

        while (L <= H) {
            int mid = L + (H - L) / 2;
            if (mid == 0) { 
                ans = max(ans, mid);
                L = mid + 1;
                continue;
            }
            if (is_heavy(curr_R, mid, 40)) {
                ans = mid;
                L = mid + 1;
            } else {
                H = mid - 1;
            }
        }

        curr_depth = ans;
        // Now 'curr_depth' is the depth of the deepest heavy node on the path to curr_R.
        // Let this node be U (we don't know its ID yet, only that it's ancestor of curr_R at curr_depth).

        // 3. Verify if U is the centroid or if the heavy path branches off towards another child.
        // We sample nodes and check which child of U they belong to.
        // A child of U is defined by an ancestor at depth 'curr_depth + 1'.
        
        vector<int> samples;
        int S = 60; // Number of samples for child checking
        for(int i=0; i<S; ++i) {
            samples.push_back(uniform_int_distribution<int>(1, n)(rng));
        }

        // Filter samples that are in the subtree of U
        vector<int> in_subtree;
        for(int u : samples) {
            if (get_lca_depth(u, curr_R) >= curr_depth) {
                in_subtree.push_back(u);
            }
        }

        // Identify heavy child cluster
        int heavy_child_R = -1;
        vector<bool> visited(in_subtree.size(), false);
        
        for(int i=0; i<(int)in_subtree.size(); ++i) {
            if (visited[i]) continue;
            int count = 0;
            vector<int> cluster;
            
            // The pivot for this cluster is in_subtree[i].
            // Check how many samples share the same child with pivot.
            // They share child if LCA(u, v) depth >= curr_depth + 1.
            for(int j=i; j<(int)in_subtree.size(); ++j) {
                if (visited[j]) continue;
                if (get_lca_depth(in_subtree[i], in_subtree[j]) >= curr_depth + 1) {
                    count++;
                    cluster.push_back(in_subtree[j]);
                }
            }
            
            // Mark clustered elements
            for(size_t k=0; k<cluster.size(); ++k) {
                for(size_t j=i; j<in_subtree.size(); ++j) {
                     if(!visited[j] && in_subtree[j] == cluster[k]) visited[j] = true;
                }
            }

            // Check if this cluster is heavy enough
            if ((double)count / S >= 0.45) { 
                heavy_child_R = cluster[0]; // Pick any node from heavy cluster as new R
                break;
            }
        }

        if (heavy_child_R != -1) {
            // Found a heavy child off the current path (or extending it).
            // Update direction and continue.
            curr_R = heavy_child_R;
            curr_depth = curr_depth + 1;
        } else {
            // No heavy child found. U is the centroid.
            // 4. Find the actual ID of U.
            // U is the ancestor of curr_R at 'curr_depth'.
            int final_id = -1;
            for (int v : levels[curr_depth]) {
                if (get_dist(v, curr_R) == depth[curr_R] - curr_depth) {
                    final_id = v;
                    break;
                }
            }
            cout << "! " << final_id << endl;
            break;
        }
    }

    return 0;
}