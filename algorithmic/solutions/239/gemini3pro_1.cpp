#include <iostream>
#include <vector>
#include <tuple>
#include <cmath>
#include <algorithm>

using namespace std;

struct Edge {
    int u, c, v;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    if (n <= 3) {
        cout << 0 << "\n";
        return 0;
    }

    long long min_edges = -1;
    int best_n1 = 1, best_n2 = 1;

    for (int n1 = 1; n1 <= n; ++n1) {
        // Optimization: For N=4096, n1 won't be extremely large in optimal solution.
        if (n1 > 200 && n > 400) break;
        
        for (int n2 = 1; n2 <= n; ++n2) {
             long long current_prod = (long long)n1 * n2;
             
             long long cost = 0;
             int step = n1 * n2;

             // Level 1: 2 to n1-1
             for (int k = 2; k < n1; ++k) {
                 if (k <= n) cost += (n - k + 1);
             }
             
             // Level 2: k*n1
             for (int k = 1; k < n2; ++k) {
                 int len = k * n1;
                 if (len > n) break;
                 if (len == 1) continue; 
                 cost += (n - len + 1);
             }
             
             // Level 3: k*step
             for (int k = 1; ; ++k) {
                 long long len = (long long)k * step;
                 if (len > n) break;
                 if (len == 1) continue;
                 cost += (n - len + 1);
             }
             
             if (min_edges == -1 || cost < min_edges) {
                 min_edges = cost;
                 best_n1 = n1;
                 best_n2 = n2;
             }
             
             if (current_prod > n) break; 
        }
    }

    vector<Edge> result;
    int n1 = best_n1;
    int n2 = best_n2;
    int step = n1 * n2;
    
    // Level 1: 2 to n1-1
    for (int k = 2; k < n1; ++k) {
        if (k > n) break;
        for (int u = 0; u <= n - k; ++u) {
            result.push_back({u, u + k - 1, u + k});
        }
    }
    
    // Level 2: k*n1
    for (int k = 1; k < n2; ++k) {
        int len = k * n1;
        if (len > n) break;
        if (len == 1) continue;
        
        if (k == 1) {
            for (int u = 0; u <= n - len; ++u) {
                result.push_back({u, u + len - 1, u + len});
            }
        } else {
            int prev_len = (k - 1) * n1;
            for (int u = 0; u <= n - len; ++u) {
                result.push_back({u, u + prev_len, u + len});
            }
        }
    }
    
    // Level 3: k*step
    for (int k = 1; ; ++k) {
        long long len_long = (long long)k * step;
        if (len_long > n) break;
        int len = (int)len_long;
        if (len == 1) continue;
        
        if (k == 1) {
            if (n2 == 1) {
                 for (int u = 0; u <= n - len; ++u) {
                    result.push_back({u, u + len - 1, u + len});
                }
            } else {
                 int part1 = (n2 - 1) * n1;
                 for (int u = 0; u <= n - len; ++u) {
                    result.push_back({u, u + part1, u + len});
                }
            }
        } else {
            int prev_len = (k - 1) * step;
            for (int u = 0; u <= n - len; ++u) {
                result.push_back({u, u + prev_len, u + len});
            }
        }
    }

    cout << result.size() << "\n";
    for (const auto& edge : result) {
        cout << edge.u << " " << edge.c << " " << edge.v << "\n";
    }

    return 0;
}