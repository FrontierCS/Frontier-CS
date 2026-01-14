#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>
#include <set>
#include <iomanip>

using namespace std;

const int N_MAX = 1000;
const int L = 32;

int n, m, T;
vector<pair<int, int>> initial_edges;
vector<int> adj[N_MAX + 1], rev_adj[N_MAX + 1];
vector<pair<char, pair<int, int>>> modifications;
bool is_helper[N_MAX + 1];
int helpers[L];
int g[N_MAX + 1];

void apply_modifications() {
    for (const auto& op : modifications) {
        int u = op.second.first;
        int v = op.second.second;
        if (op.first == '-') {
            auto& u_adj = adj[u];
            u_adj.erase(remove(u_adj.begin(), u_adj.end(), v), u_adj.end());
            auto& v_rev_adj = rev_adj[v];
            v_rev_adj.erase(remove(v_rev_adj.begin(), v_rev_adj.end(), u), v_rev_adj.end());
        } else { // '+'
            adj[u].push_back(v);
            rev_adj[v].push_back(u);
        }
    }
}

void compute_grundy_values() {
    for (int i = 0; i < L; ++i) {
        g[helpers[i]] = i;
    }

    vector<int> sorted_nodes;
    vector<int> q_topo;
    vector<int> in_degree(n + 1, 0);

    for (int i = 1; i <= n; ++i) {
        for (int neighbor : adj[i]) {
            in_degree[neighbor]++;
        }
    }
    
    for (int i = 1; i <= n; ++i) {
        if (in_degree[i] == 0) {
            q_topo.push_back(i);
        }
    }
    
    int head = 0;
    while(head < q_topo.size()){
        int u = q_topo[head++];
        sorted_nodes.push_back(u);
        for(int v : adj[u]){
            in_degree[v]--;
            if(in_degree[v] == 0){
                q_topo.push_back(v);
            }
        }
    }
    reverse(sorted_nodes.begin(), sorted_nodes.end());

    for (int u : sorted_nodes) {
        if(is_helper[u]) continue;

        set<int> seen_grundy_values;
        for (int v : adj[u]) {
            seen_grundy_values.insert(g[v]);
        }
        int current_g = 0;
        while (seen_grundy_values.count(current_g)) {
            current_g++;
        }
        g[u] = current_g;
    }
}

void solve_round() {
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    while (candidates.size() > 1) {
        map<int, vector<int>> small_g_counts;
        vector<int> large_g_candidates;
        for (int u : candidates) {
            if (g[u] < L) {
                small_g_counts[g[u]].push_back(u);
            } else {
                large_g_candidates.push_back(u);
            }
        }

        int best_m = -1;

        if (!large_g_candidates.empty() && large_g_candidates.size() <= 5) {
             best_m = g[large_g_candidates[0]];
        } else {
            int min_diff = n + 1;
            for (auto const& [val, users] : small_g_counts) {
                int diff = abs((int)candidates.size() - 2 * (int)users.size());
                if (diff < min_diff) {
                    min_diff = diff;
                    best_m = val;
                }
            }
        }
        
        if (best_m == -1) {
            if (!candidates.empty())
                best_m = g[candidates[0]];
            else // Should not happen
                best_m = 0;
        }

        vector<int> S;
        int m_rem = best_m;
        for (int i = 0; m_rem > 0 && i < L; ++i) {
            if ( (m_rem ^ g[helpers[i]]) < m_rem) {
                 S.push_back(helpers[i]);
                 m_rem ^= g[helpers[i]];
            }
        }
        
        cout << "? " << S.size();
        for (int u : S) {
            cout << " " << u;
        }
        cout << endl;

        string result;
        cin >> result;

        vector<int> next_candidates;
        if (result == "Lose") {
            for (int u : candidates) {
                if (g[u] == best_m) {
                    next_candidates.push_back(u);
                }
            }
        } else {
            for (int u : candidates) {
                if (g[u] != best_m) {
                    next_candidates.push_back(u);
                }
            }
        }
        
        if (next_candidates.empty()) {
            // This case can happen if all candidates have the same g-value,
            // and the interactor responds with "Win", which is not supposed to happen
            // with an adaptive interactor unless it is forced.
            // But if all candidates are same, only one choice, so this branch means we won.
            // Or our logic is flawed. The problem statement guarantees a consistent vertex exists.
            // The only way this could be empty is if the interactor chose a group of size 0.
            // It will always pick the larger group. Thus, this branch is unreachable.
        }
        else {
            candidates = next_candidates;
        }
    }

    cout << "! " << candidates[0] << endl;
    string final_response;
    cin >> final_response;
    if (final_response == "Wrong") {
        exit(0);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m >> T;
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        rev_adj[v].push_back(u);
        initial_edges.push_back({u, v});
    }

    for (int i = 0; i < L; ++i) {
        helpers[i] = n - i;
        is_helper[n - i] = true;
    }

    set<pair<int, int>> edges_to_remove;
    for (int i = 0; i < L; ++i) {
        int u = helpers[i];
        for (int v : adj[u]) {
            edges_to_remove.insert({u, v});
        }
        for (int v : rev_adj[u]) {
            if (is_helper[v]) {
                edges_to_remove.insert({v, u});
            }
        }
    }
    
    for(const auto& edge : edges_to_remove) {
        modifications.push_back({'-', edge});
    }

    for (int i = 1; i < L; ++i) {
        for (int j = 0; j < i; ++j) {
            modifications.push_back({'+', {helpers[i], helpers[j]}});
        }
    }

    cout << modifications.size() << endl;
    cout << fixed << setprecision(15);
    for (const auto& op : modifications) {
        cout << op.first << " " << op.second.first << " " << op.second.second << endl;
    }

    apply_modifications();
    compute_grundy_values();
    
    for (int t = 0; t < T; ++t) {
        solve_round();
    }

    return 0;
}