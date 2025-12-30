#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <queue>
#include <deque>

using namespace std;

const int MAXN = 2005;

int n;
bool C[MAXN][MAXN];
vector<int> adj[MAXN];
bool visited_comp[MAXN];
vector<vector<int>> components;
vector<int> current_component;
bool component_membership[MAXN];

void find_components_dfs(int u) {
    visited_comp[u] = true;
    current_component.push_back(u);
    for (int v : adj[u]) {
        if (!visited_comp[v]) {
            find_components_dfs(v);
        }
    }
}

void build_adj(int k) {
    for (int i = 1; i <= n; ++i) {
        adj[i].clear();
    }
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            if (C[i][j] == k) {
                adj[i].push_back(j);
                adj[j].push_back(i);
            }
        }
    }
    for (int i = 1; i <= n; ++i) {
        sort(adj[i].begin(), adj[i].end());
    }
}

vector<int> get_spanning_path(const vector<int>& component_nodes, int start_node) {
    if (component_nodes.empty()) return {};
    
    deque<int> path;
    path.push_back(start_node);
    
    fill(component_membership + 1, component_membership + n + 1, false);
    for (int node : component_nodes) component_membership[node] = true;

    vector<bool> visited_path(n + 1, false);
    visited_path[start_node] = true;
    int visited_count = 1;

    while (visited_count < component_nodes.size()) {
        bool extended = false;
        
        int head = path.front();
        for (int v : adj[head]) {
            if (component_membership[v] && !visited_path[v]) {
                path.push_front(v);
                visited_path[v] = true;
                visited_count++;
                extended = true;
                break;
            }
        }
        if (extended) continue;

        int tail = path.back();
        for (int v : adj[tail]) {
            if (component_membership[v] && !visited_path[v]) {
                path.push_back(v);
                visited_path[v] = true;
                visited_count++;
                extended = true;
                break;
            }
        }

        if (!extended) break; 
    }
    
    if (path.size() == component_nodes.size()) {
        return vector<int>(path.begin(), path.end());
    }
    return {};
}

void update_best(vector<int>& best_p, const vector<int>& p) {
    if (p.empty()) return;
    if (best_p.empty() || p < best_p) {
        best_p = p;
    }
}

void solve() {
    for (int i = 1; i <= n; ++i) {
        string row;
        cin >> row;
        for (int j = 1; j <= n; ++j) {
            C[i][j] = row[j - 1] - '0';
        }
    }

    vector<int> best_p;

    for (int k = 0; k < 2; ++k) {
        build_adj(k);

        fill(visited_comp + 1, visited_comp + n + 1, false);
        components.clear();
        for (int i = 1; i <= n; ++i) {
            if (!visited_comp[i]) {
                current_component.clear();
                find_components_dfs(i);
                sort(current_component.begin(), current_component.end());
                components.push_back(current_component);
            }
        }

        if (components.size() > 2) continue;

        if (components.size() == 1) {
            for (int start_node : components[0]) {
                vector<int> p = get_spanning_path(components[0], start_node);
                update_best(best_p, p);
                if (!p.empty()) {
                    reverse(p.begin(), p.end());
                    update_best(best_p, p);
                }
            }
        } else if (components.size() == 2) {
            vector<int> p1_options[components[0].size() * 2];
            int p1_idx = 0;
            for(int start_node : components[0]) {
                vector<int> p = get_spanning_path(components[0], start_node);
                if (!p.empty()) {
                    p1_options[p1_idx++] = p;
                    reverse(p.begin(), p.end());
                    p1_options[p1_idx++] = p;
                }
            }
            vector<int> p2_options[components[1].size() * 2];
            int p2_idx = 0;
            for(int start_node : components[1]) {
                vector<int> p = get_spanning_path(components[1], start_node);
                if (!p.empty()) {
                    p2_options[p2_idx++] = p;
                    reverse(p.begin(), p.end());
                    p2_options[p2_idx++] = p;
                }
            }
            
            for (int i = 0; i < p1_idx; ++i) {
                const auto& p1 = p1_options[i];
                for (int j = 0; j < p2_idx; ++j) {
                    const auto& p2 = p2_options[j];
                    if (C[p1.back()][p2.front()] != k) {
                        vector<int> candidate_p = p1;
                        candidate_p.insert(candidate_p.end(), p2.begin(), p2.end());
                        update_best(best_p, candidate_p);
                    }
                }
            }
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

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    while (cin >> n) {
        solve();
    }
    return 0;
}