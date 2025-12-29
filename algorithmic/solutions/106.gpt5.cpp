#include <bits/stdc++.h>
using namespace std;

int n;

int ask(const vector<int>& S) {
    if (S.empty()) return 0; // We must not actually ask with empty; treat as 0.
    cout << "? " << (int)S.size() << endl;
    for (int i = 0; i < (int)S.size(); ++i) {
        if (i) cout << ' ';
        cout << S[i];
    }
    cout << endl;
    cout.flush();
    int m;
    if (!(cin >> m)) exit(0);
    if (m == -1) exit(0);
    return m;
}

int cross_edges_count(const vector<int>& A, const vector<int>& B, int EB) {
    if (A.empty() || B.empty()) return 0;
    int EA = ask(A);
    vector<int> U;
    U.reserve(A.size() + B.size());
    for (int x : B) U.push_back(x);
    for (int x : A) U.push_back(x);
    int EAB = ask(U);
    return EAB - EB - EA;
}

int edges_from_v_to_set(int v, const vector<int>& S) {
    if (S.empty()) return 0;
    int ES = ask(S);
    vector<int> U = S;
    U.push_back(v);
    int EUS = ask(U);
    return EUS - ES;
}

int find_vertex_connected_to_B(const vector<int>& B, const vector<int>& Rest, int EB) {
    vector<int> T = Rest;
    while (T.size() > 1) {
        int mid = (int)T.size() / 2;
        vector<int> T1(T.begin(), T.begin() + mid);
        int c = cross_edges_count(T1, B, EB);
        if (c > 0) {
            T = move(T1);
        } else {
            T.erase(T.begin(), T.begin() + mid);
        }
    }
    return T[0];
}

int find_neighbor_in_set(int v, const vector<int>& S) {
    vector<int> T = S;
    while (T.size() > 1) {
        int mid = (int)T.size() / 2;
        vector<int> T1(T.begin(), T.begin() + mid);
        int deg1 = edges_from_v_to_set(v, T1);
        if (deg1 > 0) {
            T = move(T1);
        } else {
            T.erase(T.begin(), T.begin() + mid);
        }
    }
    return T[0];
}

vector<int> get_path(int a, int b, const vector<int>& parent) {
    vector<int> pa, pb;
    int x = a;
    while (x != 0) {
        pa.push_back(x);
        x = parent[x];
    }
    x = b;
    while (x != 0) {
        pb.push_back(x);
        x = parent[x];
    }
    int i = (int)pa.size() - 1;
    int j = (int)pb.size() - 1;
    while (i >= 0 && j >= 0 && pa[i] == pb[j]) {
        i--; j--;
    }
    int lca = pa[i + 1];
    vector<int> path;
    for (int k = 0; k <= i + 1; ++k) path.push_back(pa[k]); // a -> ... -> lca
    for (int k = j; k >= 0; --k) path.push_back(pb[k]);     // lca -> ... -> b (excluding duplicate lca)
    return path; // path from a to b along the tree (unique simple path)
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    if (!(cin >> n)) return 0;

    vector<int> color(n + 1, -1);
    vector<int> parent(n + 1, 0), depth(n + 1, 0);
    vector<int> part[2];
    vector<int> B; B.reserve(n);
    vector<char> inB(n + 1, 0);

    // Initialize with vertex 1
    int root = 1;
    color[root] = 0;
    parent[root] = 0;
    depth[root] = 0;
    part[0].push_back(root);
    B.push_back(root);
    inB[root] = 1;

    int EB = 0; // edges inside B

    while ((int)B.size() < n) {
        vector<int> U;
        U.reserve(n - B.size());
        for (int i = 1; i <= n; ++i) if (!inB[i]) U.push_back(i);

        // Find a vertex v in U that has an edge to B (graph is connected)
        int v = find_vertex_connected_to_B(B, U, EB);

        // Find a neighbor u of v in B
        int u = find_neighbor_in_set(v, B);

        // Set parent, depth, color
        parent[v] = u;
        depth[v] = depth[u] + 1;
        color[v] = 1 - color[u];

        // Check for intra-color edge with previous vertices of same color
        int c = color[v];
        int degSame = 0;
        if (!part[c].empty()) {
            int ES = ask(part[c]);
            vector<int> SwithV = part[c];
            SwithV.push_back(v);
            int ESv = ask(SwithV);
            degSame = ESv - ES;
        }
        if (degSame > 0) {
            // Find exact neighbor w in same color set
            int w = find_neighbor_in_set(v, part[c]);
            // Build odd cycle: path from v to w along tree (even length), add edge (v,w) as closing edge
            vector<int> cycle = get_path(v, w, parent);
            cout << "N " << (int)cycle.size() << endl;
            for (int i = 0; i < (int)cycle.size(); ++i) {
                if (i) cout << ' ';
                cout << cycle[i];
            }
            cout << endl;
            cout.flush();
            return 0;
        }

        // Update EB (edges inside B) after adding v
        {
            vector<int> Bplus = B;
            Bplus.push_back(v);
            int EBplus = ask(Bplus);
            EB = EBplus;
        }

        // Insert v into structures
        part[c].push_back(v);
        B.push_back(v);
        inB[v] = 1;
    }

    // If we reach here, graph is bipartite
    cout << "Y " << (int)part[0].size() << endl;
    for (int i = 0; i < (int)part[0].size(); ++i) {
        if (i) cout << ' ';
        cout << part[0][i];
    }
    cout << endl;
    cout.flush();

    return 0;
}