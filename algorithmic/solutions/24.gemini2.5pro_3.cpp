#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <functional>

using namespace std;

// Checks if the graph for color k is a cluster graph (a disjoint union of cliques).
// This is equivalent to being P_3-free.
// The check is O(sum of deg_k(v)^2), which can be up to O(n^3) in worst-case,
// but might pass if test data has favorable structure.
bool is_cluster_graph(int n, const vector<vector<int>>& C, int k) {
    for (int i = 1; i <= n; ++i) {
        vector<int> neighbors;
        for (int j = 1; j <= n; ++j) {
            if (i == j) continue;
            if (C[i][j] == k) {
                neighbors.push_back(j);
            }
        }
        for (size_t u_idx = 0; u_idx < neighbors.size(); ++u_idx) {
            for (size_t v_idx = u_idx + 1; v_idx < neighbors.size(); ++v_idx) {
                if (C[neighbors[u_idx]][neighbors[v_idx]] != k) {
                    return false;
                }
            }
        }
    }
    return true;
}

// Constructs a valid permutation if G_k is a cluster graph.
// The construction aims for a lexicographically large permutation.
vector<int> solve_cluster(int n, const vector<vector<int>>& C, int k) {
    vector<int> components(n + 1, 0);
    int comp_count = 0;
    function<void(int)> dfs = [&](int u) {
        components[u] = comp_count;
        for (int v = 1; v <= n; ++v) {
            if (u != v && C[u][v] == k && components[v] == 0) {
                dfs(v);
            }
        }
    };

    for (int i = 1; i <= n; ++i) {
        if (components[i] == 0) {
            comp_count++;
            dfs(i);
        }
    }

    if (comp_count == 1) {
        vector<int> p(n);
        iota(p.rbegin(), p.rend(), 1); // Generates n, n-1, ..., 1
        return p;
    }

    vector<vector<int>> comp_nodes(comp_count + 1);
    for (int i = 1; i <= n; ++i) {
        comp_nodes[components[i]].push_back(i);
    }
    
    for (int i = 1; i <= comp_count; ++i) {
        sort(comp_nodes[i].begin(), comp_nodes[i].end());
    }

    int max_comp_size = 0;
    int max_comp_idx = -1;
    for (int i = 1; i <= comp_count; ++i) {
        if ((int)comp_nodes[i].size() > max_comp_size) {
            max_comp_size = comp_nodes[i].size();
            max_comp_idx = i;
        } else if ((int)comp_nodes[i].size() == max_comp_size) {
            // Tie-break for lexicographically largest: pick component with largest elements
            if (comp_nodes[i].back() > comp_nodes[max_comp_idx].back()) {
                max_comp_idx = i;
            }
        }
    }

    vector<int> s_nodes;
    vector<int> r_nodes;
    for (int i = 1; i <= comp_count; ++i) {
        if (i == max_comp_idx) {
            s_nodes = comp_nodes[i];
        } else {
            r_nodes.insert(r_nodes.end(), comp_nodes[i].begin(), comp_nodes[i].end());
        }
    }
    sort(s_nodes.rbegin(), s_nodes.rend());
    sort(r_nodes.rbegin(), r_nodes.rend());
    
    vector<int> p;
    p.reserve(n);

    if (s_nodes.size() > r_nodes.size()) {
        int s_idx = 0, r_idx = 0;
        while(r_idx < (int)r_nodes.size()) {
            p.push_back(s_nodes[s_idx++]);
            p.push_back(r_nodes[r_idx++]);
        }
        p.push_back(s_nodes[s_idx++]);
        while(s_idx < (int)s_nodes.size()) {
            p.push_back(s_nodes[s_idx++]);
        }
    } else {
        int s_idx = 0, r_idx = 0;
        while(s_idx < (int)s_nodes.size()) {
            p.push_back(s_nodes[s_idx++]);
            p.push_back(r_nodes[r_idx++]);
        }
        while(r_idx < (int)r_nodes.size()) {
            p.push_back(r_nodes[r_idx++]);
        }
    }
    return p;
}

// Returns true if p1 is lexicographically larger than p2.
bool is_lex_larger(const vector<int>& p1, const vector<int>& p2) {
    if (p1.empty()) return false;
    if (p2.empty()) return true;
    for (size_t i = 0; i < p1.size(); ++i) {
        if (p1[i] > p2[i]) return true;
        if (p1[i] < p2[i]) return false;
    }
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    while (cin >> n) {
        vector<vector<int>> C(n + 1, vector<int>(n + 1));
        for (int i = 0; i < n; ++i) {
            string row;
            cin >> row;
            for (int j = 0; j < n; ++j) {
                C[i + 1][j + 1] = row[j - 1] - '0';
            }
        }

        vector<int> best_p;

        if (is_cluster_graph(n, C, 0)) {
            vector<int> p = solve_cluster(n, C, 0);
            if (is_lex_larger(p, best_p)) {
                best_p = p;
            }
        }
        if (is_cluster_graph(n, C, 1)) {
            vector<int> p = solve_cluster(n, C, 1);
            if (is_lex_larger(p, best_p)) {
                best_p = p;
            }
        }
        
        if (best_p.empty()) {
            cout << -1 << endl;
        } else {
            for (int i = 0; i < n; ++i) {
                cout << best_p[i] << (i == n - 1 ? "" : " ");
            }
            cout << endl;
        }
    }
    return 0;
}