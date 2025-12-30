#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

long long query(int u, int v) {
    if (u == v) return 0;
    cout << "? " << u << " " << v << endl;
    long long dist;
    cin >> dist;
    return dist;
}

map<pair<int, int>, long long> memo;
long long get_dist(int u, int v) {
    if (u == v) return 0;
    if (u > v) swap(u, v);
    if (memo.count({u, v})) {
        return memo[{u, v}];
    }
    return memo[{u, v}] = query(u, v);
}

struct Edge {
    int u, v;
    long long w;
};

void solve() {
    int n;
    cin >> n;
    memo.clear();

    if (n == 1) {
        cout << "!" << endl;
        return;
    }

    vector<long long> dist1(n + 1);
    for (int i = 2; i <= n; ++i) {
        dist1[i] = get_dist(1, i);
    }

    int u = 2;
    if (n > 2) {
        for (int i = 3; i <= n; ++i) {
            if (dist1[i] > dist1[u]) {
                u = i;
            }
        }
    } else {
        u = 2;
    }
    
    if (n>1 && dist1[u] == 0) u=1; // case n=2, dist(1,2)=0 not possible, but just in case
    
    if (u == 1) { // all nodes at same distance from 1, could be a star graph
        if (n>2) u=2;
    }


    vector<long long> dist_u(n + 1);
    for (int i = 1; i <= n; ++i) {
        if (i == u) continue;
        dist_u[i] = get_dist(u, i);
    }

    int v = 1;
    if (v == u) v = 2;
    for (int i = 1; i <= n; ++i) {
        if (i == u) continue;
        if (dist_u[i] > dist_u[v]) {
            v = i;
        }
    }

    long long D = dist_u[v];
    vector<long long> dist_v(n + 1);
    for (int i = 1; i <= n; ++i) {
        if (i == v) continue;
        dist_v[i] = get_dist(v, i);
    }

    vector<pair<long long, int>> diameter_nodes;
    vector<int> non_diameter_nodes;

    for (int i = 1; i <= n; ++i) {
        if (dist_u[i] + dist_v[i] == D) {
            diameter_nodes.push_back({dist_u[i], i});
        } else {
            non_diameter_nodes.push_back(i);
        }
    }

    sort(diameter_nodes.begin(), diameter_nodes.end());

    vector<Edge> edges;
    for (size_t i = 0; i < diameter_nodes.size() - 1; ++i) {
        edges.push_back({diameter_nodes[i].second, diameter_nodes[i+1].second, diameter_nodes[i+1].first - diameter_nodes[i].first});
    }

    map<int, vector<int>> subproblems;
    for (int node : non_diameter_nodes) {
        long long dist_on_diam = (dist_u[node] - dist_v[node] + D) / 2;
        auto it = lower_bound(diameter_nodes.begin(), diameter_nodes.end(), make_pair(dist_on_diam, 0));
        int p_node = it->second;
        subproblems[p_node].push_back(node);
    }

    for (auto const& [p_node, s_nodes] : subproblems) {
        if (s_nodes.empty()) continue;
        
        vector<pair<long long, int>> sorted_s_nodes;
        for (int node : s_nodes) {
            long long d_p_node = (dist_u[node] + dist_v[node] - D) / 2;
            sorted_s_nodes.push_back({d_p_node, node});
        }
        sort(sorted_s_nodes.begin(), sorted_s_nodes.end());

        vector<pair<long long, int>> component;
        component.push_back({0, p_node});

        for (auto const& [d_w, w] : sorted_s_nodes) {
            int low = 0, high = component.size() - 1;
            int parent_idx = 0;
            
            while(low <= high) {
                int mid_idx = low + (high - low) / 2;
                long long d_z = component[mid_idx].first;
                int z = component[mid_idx].second;
                
                if (get_dist(w, z) == d_w - d_z) {
                    parent_idx = mid_idx;
                    low = mid_idx + 1;
                } else {
                    high = mid_idx - 1;
                }
            }
            
            int parent_node = component[parent_idx].second;
            long long parent_dist = component[parent_idx].first;
            edges.push_back({w, parent_node, d_w - parent_dist});
            
            auto insert_it = lower_bound(component.begin(), component.end(), make_pair(d_w, w));
            component.insert(insert_it, {d_w, w});
        }
    }

    cout << "! ";
    for (size_t i = 0; i < edges.size(); ++i) {
        cout << edges[i].u << " " << edges[i].v << " " << edges[i].w << (i == edges.size() - 1 ? "" : " ");
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}