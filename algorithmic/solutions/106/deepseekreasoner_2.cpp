#include <iostream>
#include <vector>
#include <algorithm>
#include <cstdlib>
using namespace std;

int n;
bool tree_adj[601][601];
vector<pair<int, int>> tree_edges;
int parent[601];
int depth[601];
int color[601];

int query(const vector<int>& s) {
    cout << "? " << s.size() << endl;
    for (size_t i = 0; i < s.size(); ++i) {
        if (i) cout << ' ';
        cout << s[i];
    }
    cout << endl;
    cout.flush();
    int ans;
    cin >> ans;
    if (ans == -1) exit(0);
    return ans;
}

int count_tree_edges(const vector<int>& s) {
    bool in_s[601] = {false};
    for (int v : s) in_s[v] = true;
    int cnt = 0;
    for (const auto& e : tree_edges) {
        if (in_s[e.first] && in_s[e.second]) cnt++;
    }
    return cnt;
}

// Find a vertex v in U_vec[l..r) that has a neighbor in T_vec
int find_vertex(const vector<int>& T_vec, const vector<int>& U_vec, int l, int r) {
    if (l >= r) return -1;
    if (r - l == 1) {
        int v = U_vec[l];
        vector<int> q = T_vec;
        q.push_back(v);
        int ans = query(q);
        int edges_T = T_vec.size() - 1; // tree on |T| vertices has |T|-1 edges
        int deg = ans - edges_T;
        if (deg > 0) return v;
        else return -1;
    }
    int mid = (l + r) / 2;
    // Check first half
    vector<int> S1(U_vec.begin() + l, U_vec.begin() + mid);
    int e1 = query(S1);
    vector<int> TS1 = T_vec;
    TS1.insert(TS1.end(), S1.begin(), S1.end());
    int eT1 = query(TS1);
    int cross1 = eT1 - (T_vec.size() - 1) - e1;
    if (cross1 > 0) {
        return find_vertex(T_vec, U_vec, l, mid);
    } else {
        // Check second half
        vector<int> S2(U_vec.begin() + mid, U_vec.begin() + r);
        int e2 = query(S2);
        vector<int> TS2 = T_vec;
        TS2.insert(TS2.end(), S2.begin(), S2.end());
        int eT2 = query(TS2);
        int cross2 = eT2 - (T_vec.size() - 1) - e2;
        if (cross2 > 0) {
            return find_vertex(T_vec, U_vec, mid, r);
        } else {
            return -1;
        }
    }
}

// Find a neighbor of v in T_vec using binary search
int find_neighbor_in_T(int v, const vector<int>& T_vec) {
    int l = 0, r = T_vec.size();
    while (l < r) {
        int mid = (l + r) / 2;
        vector<int> S(T_vec.begin() + l, T_vec.begin() + mid);
        int edges_S = count_tree_edges(S);
        vector<int> q = S;
        q.push_back(v);
        int ans = query(q);
        int cross = ans - edges_S; // edges between v and S
        if (cross > 0) {
            r = mid;
        } else {
            l = mid + 1;
        }
    }
    return T_vec[l];
}

// Find one edge inside a set S (which has no tree edges)
pair<int, int> find_one_bad_edge(const vector<int>& S) {
    vector<int> T = S;
    while (true) {
        if (T.size() == 2) {
            return {T[0], T[1]};
        }
        int v = T[0];
        vector<int> Tprime(T.begin() + 1, T.end());
        int edges_Tprime = query(Tprime);
        if (edges_Tprime > 0) {
            T = Tprime;
        } else {
            // all edges involve v
            vector<int> U = Tprime;
            int l = 0, r = U.size();
            while (l < r) {
                int mid = (l + r) / 2;
                vector<int> W(U.begin() + l, U.begin() + mid);
                vector<int> q = W;
                q.push_back(v);
                int ans = query(q); // equals edges from v to W
                if (ans > 0) {
                    r = mid;
                } else {
                    l = mid + 1;
                }
            }
            int u = U[l];
            return {v, u};
        }
    }
}

vector<int> get_tree_path(int a, int b) {
    // Return vertices along the unique tree path from a to b (including both)
    vector<int> path_a, path_b;
    int x = a, y = b;
    while (x != y) {
        if (depth[x] > depth[y]) {
            path_a.push_back(x);
            x = parent[x];
        } else if (depth[y] > depth[x]) {
            path_b.push_back(y);
            y = parent[y];
        } else {
            path_a.push_back(x);
            path_b.push_back(y);
            x = parent[x];
            y = parent[y];
        }
    }
    // x = y = LCA
    vector<int> path;
    for (int v : path_a) path.push_back(v);
    path.push_back(x);
    reverse(path_b.begin(), path_b.end());
    for (int v : path_b) path.push_back(v);
    return path;
}

int main() {
    cin >> n;
    if (n == 1) {
        cout << "Y 1" << endl;
        cout << 1 << endl;
        return 0;
    }

    vector<int> T_vec = {1};
    vector<int> U_vec;
    for (int i = 2; i <= n; ++i) U_vec.push_back(i);
    parent[1] = -1;
    depth[1] = 0;

    // Build spanning tree
    for (int step = 0; step < n - 1; ++step) {
        int v = find_vertex(T_vec, U_vec, 0, U_vec.size());
        // v must exist because graph is connected
        int u = find_neighbor_in_T(v, T_vec);
        // Add edge (v, u) to tree
        tree_edges.push_back({v, u});
        tree_adj[v][u] = tree_adj[u][v] = true;
        parent[v] = u;
        // Update depth later via BFS
        // Move v from U to T
        T_vec.push_back(v);
        U_vec.erase(remove(U_vec.begin(), U_vec.end(), v), U_vec.end());
    }

    // Compute depths using BFS from root 1
    for (int i = 1; i <= n; ++i) depth[i] = -1;
    vector<int> q = {1};
    depth[1] = 0;
    for (int i = 0; i < (int)q.size(); ++i) {
        int u = q[i];
        for (int v = 1; v <= n; ++v) {
            if (tree_adj[u][v] && depth[v] == -1) {
                depth[v] = depth[u] + 1;
                parent[v] = u;
                q.push_back(v);
            }
        }
    }

    // Color vertices by parity of depth
    vector<int> color0, color1;
    for (int i = 1; i <= n; ++i) {
        if (depth[i] % 2 == 0) {
            color0.push_back(i);
            color[i] = 0;
        } else {
            color1.push_back(i);
            color[i] = 1;
        }
    }

    int bad0 = query(color0);
    int bad1 = query(color1);

    if (bad0 == 0 && bad1 == 0) {
        // Bipartite
        cout << "Y " << color0.size() << endl;
        for (size_t i = 0; i < color0.size(); ++i) {
            if (i) cout << ' ';
            cout << color0[i];
        }
        cout << endl;
    } else {
        // Not bipartite
        vector<int> S = (bad0 > 0) ? color0 : color1;
        pair<int, int> bad_edge = find_one_bad_edge(S);
        int a = bad_edge.first, b = bad_edge.second;
        vector<int> cycle = get_tree_path(a, b);
        cout << "N " << cycle.size() << endl;
        for (size_t i = 0; i < cycle.size(); ++i) {
            if (i) cout << ' ';
            cout << cycle[i];
        }
        cout << endl;
    }

    return 0;
}