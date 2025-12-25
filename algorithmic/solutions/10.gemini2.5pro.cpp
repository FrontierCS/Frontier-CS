#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <tuple>
#include <set>

using namespace std;

int n;
vector<tuple<int, int, int>> edges;
map<pair<int, int>, long long> memo;

long long do_query(int u, int v) {
    if (u == v) return 0;
    if (u > v) swap(u, v);
    if (memo.count({u, v})) {
        return memo[{u, v}];
    }
    cout << "? " << u << " " << v << endl;
    long long dist;
    cin >> dist;
    return memo[{u, v}] = dist;
}

void solve(const vector<int>& V) {
    if (V.size() <= 1) {
        return;
    }
    if (V.size() == 2) {
        long long w = do_query(V[0], V[1]);
        edges.emplace_back(V[0], V[1], w);
        return;
    }

    int start_node = V[0];
    int end1 = -1;
    long long max_dist = -1;

    for (int v : V) {
        if (v == start_node) continue;
        long long d = do_query(start_node, v);
        if (d > max_dist) {
            max_dist = d;
            end1 = v;
        }
    }
    if (end1 == -1) {
        end1 = V[0];
        for(int v : V) {
            if (v != end1) {
                end1 = v;
                break;
            }
        }
    }


    map<int, long long> dists_e1;
    int end2 = -1;
    max_dist = -1;
    for (int v : V) {
        dists_e1[v] = do_query(end1, v);
        if (dists_e1[v] > max_dist) {
            max_dist = dists_e1[v];
            end2 = v;
        }
    }

    long long diameter_dist = dists_e1[end2];
    map<int, long long> dists_e2;
    for (int v : V) {
        dists_e2[v] = do_query(end2, v);
    }
    
    vector<int> path_nodes_vec;
    set<int> path_nodes_set;
    map<long long, int> dist_to_node;
    
    for (int v : V) {
        if (dists_e1[v] + dists_e2[v] == diameter_dist) {
            path_nodes_vec.push_back(v);
            path_nodes_set.insert(v);
            dist_to_node[dists_e1[v]] = v;
        }
    }

    sort(path_nodes_vec.begin(), path_nodes_vec.end(), [&](int a, int b) {
        return dists_e1[a] < dists_e1[b];
    });

    for (size_t i = 0; i < path_nodes_vec.size() - 1; ++i) {
        int u = path_nodes_vec[i];
        int v = path_nodes_vec[i + 1];
        long long w = dists_e1[v] - dists_e1[u];
        edges.emplace_back(u, v, w);
    }

    map<int, vector<int>> child_groups;
    
    for (int v : V) {
        if (path_nodes_set.find(v) == path_nodes_set.end()) {
            long long dist_on_path = (diameter_dist + dists_e1[v] - dists_e2[v]) / 2;
            int p_node = dist_to_node[dist_on_path];
            child_groups[p_node].push_back(v);
        }
    }
    
    for (auto const& [p_node, children] : child_groups) {
        if (children.empty()) continue;

        vector<vector<int>> components;
        vector<int> remaining_children = children;
        
        while (!remaining_children.empty()) {
            int rep = remaining_children.back();
            remaining_children.pop_back();

            vector<int> current_comp = {rep};
            vector<int> next_remaining;

            long long d_p_rep = (dists_e1[rep] + dists_e2[rep] - diameter_dist) / 2;

            for (int other : remaining_children) {
                long long d_p_other = (dists_e1[other] + dists_e2[other] - diameter_dist) / 2;
                if (do_query(rep, other) < d_p_rep + d_p_other) {
                    current_comp.push_back(other);
                } else {
                    next_remaining.push_back(other);
                }
            }
            components.push_back(current_comp);
            remaining_children = next_remaining;
        }

        for (const auto& comp : components) {
            int attach_node = -1;
            long long min_dist_to_p = -1;
            
            for (int node : comp) {
                long long d_p_node = (dists_e1[node] + dists_e2[node] - diameter_dist) / 2;
                if (attach_node == -1 || d_p_node < min_dist_to_p) {
                    min_dist_to_p = d_p_node;
                    attach_node = node;
                }
            }
            edges.emplace_back(p_node, attach_node, min_dist_to_p);
            solve(comp);
        }
    }
}

void do_test_case() {
    cin >> n;
    edges.clear();
    memo.clear();

    if (n == 1) {
        cout << "!" << endl;
        return;
    }
    
    vector<int> initial_V(n);
    iota(initial_V.begin(), initial_V.end(), 1);

    solve(initial_V);

    cout << "! ";
    for (size_t i = 0; i < edges.size(); ++i) {
        cout << get<0>(edges[i]) << " " << get<1>(edges[i]) << " " << get<2>(edges[i]) << (i == edges.size() - 1 ? "" : " ");
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int t;
    cin >> t;
    while (t--) {
        do_test_case();
    }

    return 0;
}