#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <string>

using namespace std;

// This function attempts to find a valid permutation using a greedy strategy.
// It starts by building a path with k-colored edges, then switches to (1-k)-colored edges if necessary.
// The 'reverse_lex' flag controls the search order for lexicographical minimality/maximality.
vector<int> find_permutation(int n, const vector<vector<int>>& C, int k, bool reverse_lex) {
    for (int i = 0; i < n; ++i) {
        int start_node = reverse_lex ? (n - i) : (i + 1);
        
        vector<int> p;
        p.push_back(start_node);
        vector<bool> visited(n + 1, false);
        visited[start_node] = true;
        int current_node = start_node;

        // Phase 1: Greedily extend path with k-colored edges.
        while (p.size() < n) {
            int next_node = -1;
            if (reverse_lex) {
                for (int v = n; v >= 1; --v) {
                    if (!visited[v] && C[current_node][v] == k) {
                        next_node = v;
                        break;
                    }
                }
            } else {
                for (int v = 1; v <= n; ++v) {
                    if (!visited[v] && C[current_node][v] == k) {
                        next_node = v;
                        break;
                    }
                }
            }

            if (next_node != -1) {
                p.push_back(next_node);
                visited[next_node] = true;
                current_node = next_node;
            } else {
                break; // No more k-edges available.
            }
        }

        bool path_is_monochromatic = (p.size() == n);
        
        // Phase 2: If path is not complete, switch to (1-k)-colored edges.
        if (!path_is_monochromatic) {
            while (p.size() < n) {
                int next_node = -1;
                if (reverse_lex) {
                    for (int v = n; v >= 1; --v) {
                        if (!visited[v] && C[current_node][v] == (1 - k)) {
                            next_node = v;
                            break;
                        }
                    }
                } else {
                    for (int v = 1; v <= n; ++v) {
                        if (!visited[v] && C[current_node][v] == (1 - k)) {
                            next_node = v;
                            break;
                        }
                    }
                }

                if (next_node != -1) {
                    p.push_back(next_node);
                    visited[next_node] = true;
                    current_node = next_node;
                } else {
                    break; // Stuck, cannot complete the path.
                }
            }
        }
        
        if (p.size() == n) {
            if (path_is_monochromatic) {
                // If the path is monochromatic, any closing edge makes it a valid solution.
                return p;
            } else {
                // If the path has one color change, the closing edge must match the second color.
                if (C[p.back()][p.front()] == (1 - k)) {
                    return p;
                }
            }
        }
    }
    return {}; // No solution found for this configuration.
}

bool solve() {
    int n;
    if (!(cin >> n)) {
        return false;
    }

    vector<vector<int>> C(n + 1, vector<int>(n + 1));
    for (int i = 1; i <= n; ++i) {
        string row;
        cin >> row;
        for (int j = 1; j <= n; ++j) {
            C[i][j] = row[j - 1] - '0';
        }
    }
    
    // The lexicographical requirement in the problem is ambiguous.
    // Based on sample outputs, a reverse lexicographical search order seems to be preferred.
    // Trying k=1 first, then k=0, matches sample 1. This order is adopted.
    vector<int> p = find_permutation(n, C, 1, true);
    if (p.empty()) {
        p = find_permutation(n, C, 0, true);
    }
    
    // As a fallback, try standard lexicographical order.
    if (p.empty()) {
        p = find_permutation(n, C, 0, false);
        if (p.empty()) {
            p = find_permutation(n, C, 1, false);
        }
    }

    if (p.empty()) {
        cout << -1 << endl;
    } else {
        for (int i = 0; i < n; ++i) {
            cout << p[i] << (i == n - 1 ? "" : " ");
        }
        cout << endl;
    }

    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    while (solve()) {}
    return 0;
}