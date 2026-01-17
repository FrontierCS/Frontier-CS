#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to ask a query
int ask(int u, int v) {
    std::cout << "? " << u << " " << v << std::endl;
    int d;
    std::cin >> d;
    return d;
}

// Function to report the answer
void answer(int u) {
    std::cout << "! " << u << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    int current_node = 1;

    for (int iter = 0; iter < 10; ++iter) {
        // Phase 1: Find a long path starting from current_node (r)
        std::vector<int> d_r(n + 1);
        int f = -1;
        int max_dist = -1;

        for (int i = 1; i <= n; ++i) {
            if (i == current_node) {
                d_r[i] = 0;
            } else {
                d_r[i] = ask(current_node, i);
            }
            if (d_r[i] > max_dist) {
                max_dist = d_r[i];
                f = i;
            }
        }

        // Phase 2: Get distances from the other end of the path (f)
        std::vector<int> d_f(n + 1);
        int path_len = d_r[f];

        for (int i = 1; i <= n; ++i) {
            if (i == f) {
                d_f[i] = 0;
            } else {
                d_f[i] = ask(f, i);
            }
        }

        // Phase 3: Partition nodes into branches and find balance point
        std::vector<std::vector<int>> branches(path_len + 1);
        for (int i = 1; i <= n; ++i) {
            int projection_dist_num = d_r[i] - d_f[i] + path_len;
            // This value must be non-negative and even in a tree
            if (projection_dist_num >= 0 && projection_dist_num % 2 == 0) {
                int projection_dist = projection_dist_num / 2;
                if (projection_dist >= 0 && projection_dist <= path_len) {
                    branches[projection_dist].push_back(i);
                }
            }
        }

        long long current_sum = 0;
        int balance_dist = -1;
        for (int j = 0; j <= path_len; ++j) {
            current_sum += branches[j].size();
            if (current_sum * 2 >= n) {
                balance_dist = j;
                break;
            }
        }
        
        // Identify the candidate node on the path
        int candidate = -1;
        for(int node : branches[balance_dist]) {
            if (d_r[node] + d_f[node] == path_len) {
                candidate = node;
                break;
            }
        }
        
        if (candidate == -1) {
            // This case should not be reached in a valid tree, but as a robust fallback:
            candidate = branches[balance_dist][0];
        }

        // Phase 4: Check if the candidate is the centroid
        int branch_size = branches[balance_dist].size();
        
        long long sum_before = current_sum - branch_size;

        if ((n - sum_before - branch_size) <= n / 2 && (branch_size - 1) <= n / 2) {
             answer(candidate);
             return 0;
        }

        // If not, update current_node and repeat the process
        current_node = candidate;
    }
    
    // Fallback in case of unexpected behavior or too many iterations
    answer(current_node);

    return 0;
}