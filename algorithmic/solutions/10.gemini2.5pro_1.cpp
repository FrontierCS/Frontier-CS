#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

long long query(int u, int v) {
    cout << "? " << u << " " << v << endl;
    long long dist;
    cin >> dist;
    return dist;
}

struct Edge {
    int u, v, w;
};

void solve() {
    int n;
    cin >> n;

    if (n == 1) {
        cout << "!" << endl;
        return;
    }

    vector<long long> d(n + 1, 0);
    for (int i = 2; i <= n; ++i) {
        d[i] = query(1, i);
    }

    vector<pair<long long, int>> sorted_vertices;
    for (int i = 2; i <= n; ++i) {
        sorted_vertices.push_back({d[i], i});
    }
    sort(sorted_vertices.begin(), sorted_vertices.end());

    vector<int> p(n + 1, 0);
    vector<vector<int>> children(n + 1);
    vector<Edge> edges;

    if (n > 1) {
        int v2 = sorted_vertices[0].second;
        p[v2] = 1;
        children[1].push_back(v2);
        edges.push_back({1, v2, (int)d[v2]});
    }

    for (size_t i = 1; i < sorted_vertices.size(); ++i) {
        int v = sorted_vertices[i].second;
        int u = sorted_vertices[i - 1].second;

        long long dist_uv = query(u, v);
        long long d_lca = (d[u] + d[v] - dist_uv) / 2;
        
        int curr = u;
        while (d[curr] > d_lca) {
            curr = p[curr];
        }
        int lca = curr;

        curr = lca;
        while (true) {
            int next_node = -1;
            
            int child_on_path_to_u = -1;
            if (curr != u) {
                int temp = u;
                while (p[temp] != curr) {
                    temp = p[temp];
                }
                child_on_path_to_u = temp;
            }

            // To make search potentially faster, process children in a random order
            vector<int> current_children = children[curr];
            random_shuffle(current_children.begin(), current_children.end());

            for (int child : current_children) {
                if (child == child_on_path_to_u) continue;
                
                long long dist_child_v = query(child, v);
                if (d[v] - d[child] == dist_child_v) {
                    next_node = child;
                    break;
                }
            }

            if (next_node != -1) {
                curr = next_node;
            } else {
                p[v] = curr;
                children[curr].push_back(v);
                edges.push_back({curr, v, (int)(d[v] - d[curr])});
                break;
            }
        }
    }

    cout << "!";
    for (const auto& edge : edges) {
        cout << " " << edge.u << " " << edge.v << " " << edge.w;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int t;
    cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}