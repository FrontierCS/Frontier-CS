#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <utility>

// Using 1-based indexing for nodes to match problem statement
int n, ty;
std::vector<int> par;
std::vector<std::pair<int, int>> val_pairs;
std::vector<int> v; // Sorted nodes by val descending

// Function to make a query to the black box
int query(const std::vector<int>& vec) {
    if (vec.empty()) {
        return 0;
    }
    std::cout << "? " << vec.size();
    for (int node : vec) {
        std::cout << " " << node;
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    return result;
}

// Function to count ancestors of u among v[1]...v[m]
int count_ancestors(int u, int m) {
    if (m == 0) {
        return 0;
    }
    std::vector<int> q_vec;
    q_vec.reserve(m + 1);
    q_vec.push_back(u);
    for (int i = 1; i <= m; ++i) {
        q_vec.push_back(v[i]);
    }
    int q_res = query(q_vec);
    // q_res = 1 + |{v_j | j in [1,m], v_j is not related to u}|
    // Number of related nodes (ancestors) = m - (q_res - 1)
    return m - (q_res - 1);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> ty;

    par.resize(n + 1);

    // Step 1: Compute val for all nodes
    for (int i = 1; i <= n; ++i) {
        std::vector<int> q_vec;
        q_vec.reserve(n);
        q_vec.push_back(i);
        for (int j = 1; j <= n; ++j) {
            if (i == j) continue;
            q_vec.push_back(j);
        }
        int q_res = query(q_vec);
        // val(i) = sz(i) + depth(i) = n - |unrelated_to_i| = n - (q_res - 1)
        int val = n - q_res + 1;
        val_pairs.push_back({val, i});
    }

    // Step 2: Sort nodes by val descending
    std::sort(val_pairs.rbegin(), val_pairs.rend());

    v.resize(n + 1);
    for (int i = 0; i < n; ++i) {
        v[i + 1] = val_pairs[i].second;
    }

    // Step 3: Root is the first in sorted list
    par[v[1]] = 0;

    // Step 4: Find parent for each other node
    for (int i = 2; i <= n; ++i) {
        int u = v[i];
        
        // A. Find total number of ancestors k for u in {v_1, ..., v_{i-1}}
        int k = count_ancestors(u, i - 1);
        
        // B. Binary search for parent index. Parent is v_p_idx where p_idx is
        // the smallest index m such that {v_1...v_m} contains all k ancestors.
        int low = 1, high = i - 1;
        int p_idx = i - 1; // Default to a valid index
        
        while (low <= high) {
            int mid = low + (high - low) / 2;
            if (mid == 0) { 
                low = 1;
                continue;
            }
            if (count_ancestors(u, mid) < k) {
                low = mid + 1;
            } else { // count_ancestors(u, mid) == k
                p_idx = mid;
                high = mid - 1;
            }
        }
        par[u] = v[p_idx];
    }

    // Step 5: Print the answer
    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << par[i];
    }
    std::cout << std::endl;

    return 0;
}