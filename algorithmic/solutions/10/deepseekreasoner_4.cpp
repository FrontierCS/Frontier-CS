#include <iostream>
#include <vector>
#include <stack>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <utility>
#include <cassert>

using namespace std;

const int MAXN = 100005;

int parent[MAXN];
long long edge_weight[MAXN];
unordered_map<long long, long long> dist_cache; // key = u*(MAXN+1)+v

long long query(int u, int v) {
    if (u == v) return 0;
    if (u > v) swap(u, v);
    long long key = 1LL * u * (MAXN + 1) + v;
    auto it = dist_cache.find(key);
    if (it != dist_cache.end()) return it->second;
    cout << "? " << u << " " << v << endl;
    cout.flush();
    long long d;
    cin >> d;
    dist_cache[key] = d;
    return d;
}

struct Component {
    vector<int> nodes;
    int root;
    vector<long long> dists; // distance from root to each node in 'nodes'
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        // reset
        dist_cache.clear();
        for (int i = 1; i <= n; ++i) parent[i] = -1;

        // initial distances from node 1
        vector<long long> dist1(n + 1, 0);
        for (int i = 2; i <= n; ++i) {
            dist1[i] = query(1, i);
        }

        // initial component: whole tree rooted at 1
        vector<int> all_nodes(n);
        vector<long long> all_dists(n);
        for (int i = 0; i < n; ++i) {
            all_nodes[i] = i + 1;
            all_dists[i] = dist1[i + 1];
        }
        Component init{all_nodes, 1, all_dists};
        stack<Component> st;
        st.push(init);

        while (!st.empty()) {
            Component comp = st.top();
            st.pop();
            if (comp.nodes.size() <= 1) continue;

            // map node -> its distance from comp.root
            unordered_map<int, long long> dist_map;
            for (size_t i = 0; i < comp.nodes.size(); ++i) {
                dist_map[comp.nodes[i]] = comp.dists[i];
            }

            // find farthest node from root (except root itself)
            int x = -1;
            long long max_dist = -1;
            for (int u : comp.nodes) {
                if (u == comp.root) continue;
                if (dist_map[u] > max_dist) {
                    max_dist = dist_map[u];
                    x = u;
                }
            }
            if (x == -1) continue;

            // query distances from x to all nodes in this component
            unordered_map<int, long long> dist_x;
            for (int u : comp.nodes) {
                if (u == x) {
                    dist_x[u] = 0;
                    continue;
                }
                dist_x[u] = query(x, u);
            }
            long long d_root_x = dist_map[x];

            // nodes on the path between root and x
            vector<int> path;
            for (int u : comp.nodes) {
                if (dist_map[u] + dist_x[u] == d_root_x) {
                    path.push_back(u);
                }
            }
            sort(path.begin(), path.end(), [&](int a, int b) {
                return dist_map[a] < dist_map[b];
            });
            unordered_set<int> path_set(path.begin(), path.end());

            // map distance from root -> node on path (unique)
            unordered_map<long long, int> dist_to_node;
            for (int u : path) {
                dist_to_node[dist_map[u]] = u;
            }

            // add edges along the path
            for (size_t i = 1; i < path.size(); ++i) {
                int a = path[i - 1];
                int b = path[i];
                if (parent[b] == -1) {
                    parent[b] = a;
                    edge_weight[b] = dist_map[b] - dist_map[a];
                }
            }

            // group nodes by their foot on the path
            unordered_map<int, vector<int>> groups;
            for (int f : path) {
                groups[f].push_back(f);
            }
            for (int u : comp.nodes) {
                if (path_set.count(u)) continue;
                long long d_u_root = dist_map[u];
                long long d_u_x = dist_x[u];
                long long t = (d_u_root + d_root_x - d_u_x) / 2;
                int f = dist_to_node[t];
                groups[f].push_back(u);
            }

            // create new components for each foot with more than one node
            for (auto& entry : groups) {
                int f = entry.first;
                vector<int>& nodes_list = entry.second;
                if (nodes_list.size() <= 1) continue;
                vector<int> new_nodes;
                vector<long long> new_dists;
                long long d_f_root = dist_map[f];
                for (int u : nodes_list) {
                    new_nodes.push_back(u);
                    if (u == f) {
                        new_dists.push_back(0);
                    } else {
                        new_dists.push_back(dist_map[u] - d_f_root);
                    }
                }
                Component new_comp{new_nodes, f, new_dists};
                st.push(new_comp);
            }
        }

        // output answer
        cout << "!";
        for (int i = 2; i <= n; ++i) {
            cout << " " << parent[i] << " " << i << " " << edge_weight[i];
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}