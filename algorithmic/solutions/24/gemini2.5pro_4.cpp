#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

int n;
vector<vector<int>> C;
vector<int> p;
vector<bool> visited;

// Checks if the permutation stored in global 'p' is almost monochromatic.
bool check_solution() {
    if (p.size() != n) return false;
    vector<int> c(n);
    for (int i = 0; i < n - 1; ++i) {
        c[i] = C[p[i] - 1][p[i+1] - 1];
    }
    c[n - 1] = C[p[n - 1] - 1][p[0] - 1];

    int changes = 0;
    for (int i = 0; i < n - 1; ++i) {
        if (c[i] != c[i+1]) {
            changes++;
        }
    }
    return changes <= 1;
}

// Greedily constructs a path and checks if it forms a valid cycle.
bool solve_greedy(int start_node, int start_mode, bool can_switch) {
    p.assign(1, start_node);
    visited.assign(n + 1, false);
    visited[start_node] = true;

    int current_node = start_node;
    int current_mode = start_mode;
    bool switched = false;

    for (int i = 1; i < n; ++i) {
        int next_node = -1;
        
        // Try to find the smallest-indexed next node in the current mode.
        for (int v = 1; v <= n; ++v) {
            if (!visited[v] && C[current_node - 1][v - 1] == current_mode) {
                next_node = v;
                break;
            }
        }

        // If stuck, try to switch mode if allowed.
        if (next_node == -1 && can_switch && !switched) {
            switched = true;
            current_mode = 1 - current_mode;
            for (int v = 1; v <= n; ++v) {
                if (!visited[v] && C[current_node - 1][v - 1] == current_mode) {
                    next_node = v;
                    break;
                }
            }
        }
        
        if (next_node == -1) {
            p.clear();
            return false;
        }

        p.push_back(next_node);
        visited[next_node] = true;
        current_node = next_node;
    }

    return check_solution();
}


void run_test_case() {
    C.assign(n, vector<int>(n));
    for (int i = 0; i < n; ++i) {
        string row;
        cin >> row;
        for (int j = 0; j < n; ++j) {
            C[i][j] = row[j] - '0';
        }
    }

    vector<int> best_p;

    for (int start_node = 1; start_node <= n; ++start_node) {
        vector<int> best_p_for_start;
        
        // Try monochromatic 0
        if (solve_greedy(start_node, 0, false)) {
            if (best_p_for_start.empty() || p < best_p_for_start) best_p_for_start = p;
        }
        // Try monochromatic 1
        if (solve_greedy(start_node, 1, false)) {
            if (best_p_for_start.empty() || p < best_p_for_start) best_p_for_start = p;
        }
        // Try 0 -> 1 switch
        if (solve_greedy(start_node, 0, true)) {
            if (best_p_for_start.empty() || p < best_p_for_start) best_p_for_start = p;
        }
        // Try 1 -> 0 switch
        if (solve_greedy(start_node, 1, true)) {
            if (best_p_for_start.empty() || p < best_p_for_start) best_p_for_start = p;
        }

        if (!best_p_for_start.empty()) {
            best_p = best_p_for_start;
            break; 
        }
    }

    if (!best_p.empty()) {
        for (int i = 0; i < n; ++i) {
            cout << best_p[i] << (i == n - 1 ? "" : " ");
        }
        cout << endl;
    } else {
        cout << -1 << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    while (cin >> n) {
        run_test_case();
    }
    return 0;
}