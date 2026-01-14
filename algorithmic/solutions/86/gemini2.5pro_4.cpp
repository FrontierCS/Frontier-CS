#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

int ask_query(int u, int v, int w) {
    cout << "0 " << u << " " << v << " " << w << endl;
    int median;
    cin >> median;
    return median;
}

void answer(const vector<pair<int, int>>& edges) {
    cout << "1";
    for (const auto& edge : edges) {
        cout << " " << edge.first << " " << edge.second;
    }
    cout << endl;
}

vector<int> get_path(int start, int end, int n, const vector<vector<int>>& adj) {
    vector<int> path;
    vector<int> p(n + 1, 0);
    vector<bool> visited(n + 1, false);
    vector<int> q;
    q.push_back(start);
    visited[start] = true;

    int head = 0;
    bool found = false;
    while(head < q.size()){
        int u = q[head++];
        if (u == end) {
            found = true;
            break;
        }
        for (int v : adj[u]) {
            if (!visited[v]) {
                visited[v] = true;
                p[v] = u;
                q.push_back(v);
            }
        }
    }

    if (!found) return {};

    int curr = end;
    while (curr != 0) {
        path.push_back(curr);
        curr = p[curr];
    }
    reverse(path.begin(), path.end());
    return path;
}

pair<int, vector<int>> bfs(int start, int n, const vector<vector<int>>& adj) {
    vector<int> dist(n + 1, -1);
    vector<int> q;
    q.push_back(start);
    dist[start] = 0;
    
    int head = 0;
    int farthest_node = start;
    int max_dist = 0;

    while(head < q.size()){
        int u = q[head++];
        if (dist[u] > max_dist) {
            max_dist = dist[u];
            farthest_node = u;
        }
        for (int v : adj[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                q.push_back(v);
            }
        }
    }
    return {farthest_node, dist};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    if (n == 3) {
        int m = ask_query(1, 2, 3);
        vector<pair<int, int>> edges;
        for(int i = 1; i <= 3; ++i) {
            if (i != m) {
                edges.push_back({m, i});
            }
        }
        answer(edges);
        return 0;
    }

    vector<pair<int, int>> edges;
    vector<vector<int>> adj(n + 1);

    auto add_edge = [&](int u, int v) {
        edges.push_back({u, v});
        adj[u].push_back(v);
        adj[v].push_back(u);
    };

    int u1 = -1, u2 = -1, m_base = -1;
    vector<int> initial_nodes = {1,2,3};
    m_base = ask_query(1, 2, 3);
    for(int node : initial_nodes) {
        if(node != m_base) {
            if (u1 == -1) u1 = node;
            else u2 = node;
        }
    }
    
    add_edge(m_base, u1);
    add_edge(m_base, u2);
    
    int L = u1, R = u2;

    for (int i = 4; i <= n; ++i) {
        int m = ask_query(L, R, i);

        if (m == L) {
            add_edge(i, L);
            L = i;
        } else if (m == R) {
            add_edge(i, R);
            R = i;
        } else {
            vector<int> path_to_L = get_path(m, L, n, adj);
            vector<int> path_to_R = get_path(m, R, n, adj);
            
            int u_search, v_search_far;
            if (path_to_L.size() > path_to_R.size()) {
                u_search = L;
                v_search_far = R;
            } else {
                u_search = R;
                v_search_far = L;
            }

            vector<int> path_m_u = get_path(m, u_search, n, adj);
            
            int low = 0, high = path_m_u.size() - 1;
            int parent_node = m;

            while (low <= high) {
                int mid_idx = low + (high - low) / 2;
                if (mid_idx == 0) {
                     low = 1;
                     continue;
                }
                int curr_node = path_m_u[mid_idx];
                
                int res = ask_query(curr_node, v_search_far, i);
                if (res == curr_node) {
                    parent_node = curr_node;
                    low = mid_idx + 1;
                } else {
                    high = mid_idx - 1;
                }
            }
            add_edge(i, parent_node);
            
            auto [farthest_from_L, dist_L] = bfs(L, n, adj);
            if (dist_L[i] > dist_L[R]) {
                R = i;
            }
            auto [farthest_from_R, dist_R] = bfs(R, n, adj);
             if (dist_R[i] > dist_R[L]) {
                L = i;
            }
            
            if (dist_L[R] > dist_R[L]) {
                // Diameter might have changed completely
                 auto [u_tmp, dist_tmp] = bfs(1, n, adj);
                 auto [u_new, dist_new] = bfs(u_tmp, n, adj);
                 auto [v_new, dist_v_new] = bfs(u_new, n, adj);
                 L = u_new;
                 R = v_new;

            }
        }
    }

    answer(edges);

    return 0;
}