#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Global variables for graph and problem data
struct Edge {
    int to;
};
vector<vector<Edge>> adj;
vector<long long> D;
int n;
vector<int> sz_helper;

// Function to query path sum for a single node
long long query_f(int u) {
    cout << "? 1 1 " << u << endl;
    long long res;
    cin >> res;
    return res;
}

// Function to query sum of f(u) for all u
long long query_all(int n) {
    cout << "? 1 " << n;
    for (int i = 1; i <= n; ++i) {
        cout << " " << i;
    }
    cout << endl;
    long long res;
    cin >> res;
    return res;
}

// Function to toggle a node
void toggle(int u) {
    cout << "? 2 " << u << endl;
}

// Calculate a_v given a root
vector<int> calculate_a(int root) {
    vector<int> a(n + 1);
    vector<int> q;
    q.push_back(root);
    vector<bool> visited(n + 1, false);
    visited[root] = true;
    
    a[root] = (int)D[root]; // D[root] is a_root

    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        for(auto& edge : adj[u]){
            int v = edge.to;
            if(!visited[v]){
                visited[v] = true;
                // Since u is parent of v: f(v) = f(u) + a_v => a_v = f(v) - f(u)
                a[v] = (int)(D[v] - D[u]);
                q.push_back(v);
            }
        }
    }
    return a;
}

// DFS for calculating subtree sizes
void dfs_sz(int u, int p) {
    sz_helper[u] = 1;
    for (auto& edge : adj[u]) {
        int v = edge.to;
        if (v != p) {
            dfs_sz(v, u);
            sz_helper[u] += sz_helper[v];
        }
    }
}

// Wrapper to calculate sizes for a given root
vector<int> calculate_sizes(int root) {
    sz_helper.assign(n + 1, 0);
    dfs_sz(root, 0);
    return sz_helper;
}

void solve() {
    cin >> n;
    adj.assign(n + 1, vector<Edge>());
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back({v});
        adj[v].push_back({u});
    }

    // Query D[u] for all u. Cost: N queries.
    D.assign(n + 1, 0);
    long long current_sum_all = 0;
    for (int i = 1; i <= n; ++i) {
        D[i] = query_f(i);
        current_sum_all += D[i];
    }

    // Identify candidates for the root
    // Root must have |f(root)| = |a_root| = 1
    vector<int> c_plus, c_minus;
    for (int i = 1; i <= n; ++i) {
        if (D[i] == 1) c_plus.push_back(i);
        if (D[i] == -1) c_minus.push_back(i);
    }

    vector<int> final_a;
    
    // If only one set of candidates exists, there is no ambiguity in values
    if (c_plus.empty()) {
        final_a = calculate_a(c_minus[0]);
    } else if (c_minus.empty()) {
        final_a = calculate_a(c_plus[0]);
    } else {
        // Ambiguity possible between a 'positive root' hypothesis and 'negative root' hypothesis
        int r_plus = c_plus[0];
        int r_minus = c_minus[0];

        vector<int> a_plus = calculate_a(r_plus);
        vector<int> a_minus = calculate_a(r_minus);

        if (a_plus == a_minus) {
            // Values are the same regardless of hypothesis
            final_a = a_plus;
        } else {
            // Values differ, need to resolve ambiguity.
            // Find a node where the values differ.
            int u_diff = -1;
            for(int i = 1; i <= n; ++i){
                if(a_plus[i] != a_minus[i]){
                    u_diff = i;
                    break;
                }
            }
            
            // Calculate expected change in total sum if we toggle u_diff
            // Change = -2 * a_u * size_of_subtree_at_u
            vector<int> sz_plus = calculate_sizes(r_plus);
            vector<int> sz_minus = calculate_sizes(r_minus);
            
            long long diff_plus = -2LL * a_plus[u_diff] * sz_plus[u_diff];
            // long long diff_minus = -2LL * a_minus[u_diff] * sz_minus[u_diff];

            // Perform toggle and query sum. Cost: 2 queries.
            toggle(u_diff);
            long long new_sum = query_all(n);
            long long actual_diff = new_sum - current_sum_all;

            if (actual_diff == diff_plus) {
                final_a = a_plus;
                // Update the value we just toggled
                final_a[u_diff] *= -1; 
            } else {
                final_a = a_minus;
                final_a[u_diff] *= -1;
            }
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << final_a[i];
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}