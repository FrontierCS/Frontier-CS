#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <functional>

using namespace std;

map<pair<int, int>, int> dist_cache;
int n;

// Function to query distance, with caching to avoid repeated queries
int ask(int u, int v) {
    if (u == v) return 0;
    if (u > v) swap(u, v);
    if (dist_cache.count({u, v})) {
        return dist_cache[{u, v}];
    }
    cout << "? " << u << " " << v << endl;
    int d;
    cin >> d;
    if (d == -1) exit(0); // Exit on error from interactor
    dist_cache[{u, v}] = d;
    return d;
}

// Function to submit the final answer
void answer(int x) {
    cout << "! " << x << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;

    // Step 1: Find the endpoints of a diameter of the tree.
    // This takes 2*(n-1) queries in total.
    int u1 = 1;
    int max_d1 = -1;
    int a = -1;
    // Find node 'a' farthest from an arbitrary node (1).
    for (int i = 1; i <= n; ++i) {
        if (i == u1) continue;
        int d = ask(u1, i);
        if (d > max_d1) {
            max_d1 = d;
            a = i;
        }
    }
    if (a == -1) a = (n > 1 ? 2 : 1);

    vector<int> da(n + 1);
    int max_da = -1;
    int b = -1;
    // Find node 'b' farthest from 'a'. The path a-b is a diameter.
    for (int i = 1; i <= n; ++i) {
        if (i == a) continue;
        da[i] = ask(a, i);
        if (da[i] > max_da) {
            max_da = da[i];
            b = i;
        }
    }
    if (b == -1) b = (a == 1 ? 2 : 1);

    // Get distances from 'b' to all other nodes.
    vector<int> db(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        if (i == b) continue;
        db[i] = ask(b, i);
    }
    int D = da[b];

    // Step 2: Project all nodes onto the diameter and group them.
    vector<int> count(D + 1, 0);
    vector<vector<int>> C(D + 1);
    
    for (int i = 1; i <= n; ++i) {
        int d_ap = (da[i] - db[i] + D) / 2;
        if (d_ap >= 0 && d_ap <= D) {
            count[d_ap]++;
            C[d_ap].push_back(i);
        }
    }

    // Step 3: Find the "balance point" on the diameter.
    // This is a node 'u' on the diameter that splits the remaining nodes
    // into two groups (towards 'a' and towards 'b'), each of size at most n/2.
    vector<long long> S_a(D + 2, 0);
    for (int i = 0; i <= D; ++i) {
        S_a[i + 1] = S_a[i] + count[i];
    }
    
    int best_i = -1;
    for (int i = 0; i <= D; ++i) {
        long long s_a_val = S_a[i];
        long long s_b_val = S_a[D + 1] - S_a[i + 1];
        if (s_a_val <= n / 2 && s_b_val <= n / 2) {
            best_i = i;
            break;
        }
    }
    
    int u = -1;
    for (int node : C[best_i]) {
        if (da[node] + db[node] == D) {
            u = node;
            break;
        }
    }

    // Step 4: Check if 'u' is the centroid.
    // If the total size of off-path subtrees at 'u' is at most n/2,
    // then no single off-path subtree can be larger than n/2.
    // In this case, 'u' must be the centroid.
    if (count[best_i] - 1 <= n / 2) {
        answer(u);
        return 0;
    }

    // Step 5: If 'u' is not the centroid, the centroid lies in a large
    // off-path component. We must find the weighted centroid in this component.
    vector<int> V_prime = C[best_i];
    int k = V_prime.size();
    
    // Reconstruct the tree structure for the nodes in C[best_i].
    // This takes O(k^2) queries.
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < k; ++i) {
        for (int j = i + 1; j < k; ++j) {
            if (ask(V_prime[i], V_prime[j]) == 1) {
                adj[V_prime[i]].push_back(V_prime[j]);
                adj[V_prime[j]].push_back(V_prime[i]);
            }
        }
    }

    // The induced graph on C[best_i] is a tree rooted at 'u'.
    // Calculate subtree sizes for this tree.
    vector<int> subtree_size(n + 1, 0);
    function<void(int, int)> dfs_size = [&](int curr, int p) {
        subtree_size[curr] = 1;
        for (int neighbor : adj[curr]) {
            if (neighbor != p) {
                dfs_size(neighbor, curr);
                subtree_size[curr] += subtree_size[neighbor];
            }
        }
    };

    dfs_size(u, 0);

    // Find the weighted centroid by walking down the heavy path from 'u'.
    int curr_centroid = u;
    int parent_comp_size = n - k;

    while (true) {
        int max_comp_size = parent_comp_size;
        int heavy_child = -1;

        for (int neighbor : adj[curr_centroid]) {
            // A neighbor is a child if its subtree is smaller (T' is rooted at u)
            if (subtree_size[curr_centroid] > subtree_size[neighbor]) {
                if (subtree_size[neighbor] > max_comp_size) {
                    max_comp_size = subtree_size[neighbor];
                    heavy_child = neighbor;
                }
            }
        }

        if (max_comp_size <= n / 2) {
            break; // Found the centroid
        }
        
        // Move to the heavy child and update parent component size
        parent_comp_size += subtree_size[curr_centroid] - subtree_size[heavy_child];
        curr_centroid = heavy_child;
    }

    answer(curr_centroid);

    return 0;
}