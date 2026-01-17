#include <bits/stdc++.h>
using namespace std;

int n;

int query(const vector<int>& S) {
    if (S.empty()) return 0; // should never happen for valid calls
    cout << "? " << S.size() << '\n';
    for (int i = 0; i < (int)S.size(); ++i) {
        if (i) cout << ' ';
        cout << S[i];
    }
    cout << '\n';
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

vector<int> get_path(int u, int v, const vector<int>& parent, const vector<int>& depth) {
    vector<int> path_u, path_v;
    int uu = u, vv = v;
    while (uu != vv) {
        if (depth[uu] > depth[vv]) {
            path_u.push_back(uu);
            uu = parent[uu];
        } else if (depth[vv] > depth[uu]) {
            path_v.push_back(vv);
            vv = parent[vv];
        } else {
            path_u.push_back(uu);
            path_v.push_back(vv);
            uu = parent[uu];
            vv = parent[vv];
        }
    }
    int lca = uu;
    vector<int> path;
    for (int x : path_u) path.push_back(x);
    path.push_back(lca);
    for (int i = (int)path_v.size() - 1; i >= 0; --i) path.push_back(path_v[i]);
    return path;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "Y 1\n1\n";
        cout.flush();
        return 0;
    }

    vector<vector<int>> tree_adj(n + 1);
    vector<int> parent(n + 1, 0), depth(n + 1, 0);

    vector<int> V; // visited / in-tree
    vector<int> U; // not yet in tree
    V.push_back(1);
    for (int i = 2; i <= n; ++i) U.push_back(i);
    parent[1] = 0;
    depth[1] = 0;

    int eV = 0; // number of edges within V

    // Build a spanning tree
    while ((int)V.size() < n) {
        // Step 1: find vertex b in U adjacent to some vertex in V
        vector<int> S = U;
        while (S.size() > 1) {
            int mid = (int)S.size() / 2;
            vector<int> S1(S.begin(), S.begin() + mid);
            vector<int> S2(S.begin() + mid, S.end());

            int eS1 = query(S1);
            vector<int> temp = S1;
            temp.insert(temp.end(), V.begin(), V.end());
            int eVS1 = query(temp);
            int cross1 = eVS1 - eS1 - eV; // edges between V and S1

            if (cross1 > 0) {
                S.swap(S1);
            } else {
                S.swap(S2);
            }
        }
        int b = S[0];

        // Step 2: find neighbor a in V for b
        vector<int> VplusB = V;
        VplusB.push_back(b);
        int eVb = query(VplusB);
        int deg = eVb - eV; // deg(b, V), should be > 0 by connectivity

        vector<int> cand = V;
        int k = deg;
        while (cand.size() > 1) {
            int mid = (int)cand.size() / 2;
            vector<int> C1(cand.begin(), cand.begin() + mid);
            vector<int> C2(cand.begin() + mid, cand.end());

            int eC1 = query(C1);
            vector<int> temp2 = C1;
            temp2.push_back(b);
            int eC1b = query(temp2);
            int deg1 = eC1b - eC1; // edges between b and C1

            if (deg1 > 0) {
                cand.swap(C1);
                k = deg1;
            } else {
                cand.swap(C2);
                k = k - deg1; // deg1 == 0 here
            }
        }
        int a = cand[0];

        // Add tree edge (a, b)
        tree_adj[a].push_back(b);
        tree_adj[b].push_back(a);
        parent[b] = a;
        depth[b] = depth[a] + 1;

        // Update sets
        V.push_back(b);
        eV = eVb;
        auto it = find(U.begin(), U.end(), b);
        if (it != U.end()) U.erase(it);
    }

    // Color the tree bipartitely
    vector<int> color(n + 1, -1);
    queue<int> q;
    color[1] = 0;
    q.push(1);
    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int to : tree_adj[v]) {
            if (color[to] == -1) {
                color[to] = color[v] ^ 1;
                q.push(to);
            }
        }
    }

    vector<int> C[2];
    for (int i = 1; i <= n; ++i) C[color[i]].push_back(i);

    int e0 = query(C[0]);
    int e1 = query(C[1]);

    if (e0 == 0 && e1 == 0) {
        // Graph is bipartite
        cout << "Y " << C[0].size() << '\n';
        for (int i = 0; i < (int)C[0].size(); ++i) {
            if (i) cout << ' ';
            cout << C[0][i];
        }
        cout << '\n';
        cout.flush();
        return 0;
    }

    // Graph is not bipartite: find an odd cycle
    int badColor = (e0 > 0) ? 0 : 1;
    vector<int> S_bad = C[badColor];
    int eS = (badColor == 0 ? e0 : e1);

    int vstar = -1;
    int deg_vstar = 0;
    vector<int> T;

    for (int v : S_bad) {
        T.clear();
        T.reserve(S_bad.size() - 1);
        for (int u : S_bad) if (u != v) T.push_back(u);
        int eSmv = query(T);
        int deg_v = eS - eSmv; // edges from v to S_bad \ {v}
        if (deg_v > 0) {
            vstar = v;
            deg_vstar = deg_v;
            break;
        }
    }

    // Now find neighbor u of vstar inside T
    vector<int> cand2 = T;
    int k2 = deg_vstar;
    while (cand2.size() > 1) {
        int mid = (int)cand2.size() / 2;
        vector<int> C1(cand2.begin(), cand2.begin() + mid);
        vector<int> C2(cand2.begin() + mid, cand2.end());

        int eC1 = query(C1);
        vector<int> temp = C1;
        temp.push_back(vstar);
        int eC1v = query(temp);
        int d1 = eC1v - eC1; // edges between vstar and C1

        if (d1 > 0) {
            cand2.swap(C1);
            k2 = d1;
        } else {
            cand2.swap(C2);
            k2 = k2 - d1; // d1 == 0 here
        }
    }
    int ustar = cand2[0];

    // Build odd cycle along tree path between vstar and ustar plus edge {vstar, ustar}
    vector<int> cycle = get_path(vstar, ustar, parent, depth);
    int l = cycle.size(); // odd length

    cout << "N " << l << '\n';
    for (int i = 0; i < l; ++i) {
        if (i) cout << ' ';
        cout << cycle[i];
    }
    cout << '\n';
    cout.flush();

    return 0;
}