#include <bits/stdc++.h>
using namespace std;

int n;

// Ask the judge for number of edges inside subset S
int ask(const vector<int>& S) {
    int k = (int)S.size();
    if (k == 0) return 0; // we will not actually use empty queries
    cout << "? " << k << '\n';
    for (int i = 0; i < k; ++i) {
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

// Find a vertex in U which has at least one edge to P
int find_vertex_connected_to_P(const vector<int>& P, int fP, const vector<int>& U) {
    vector<int> X = U;
    while (X.size() > 1) {
        int mid = (int)X.size() / 2;
        vector<int> X1(X.begin(), X.begin() + mid);
        vector<int> X2(X.begin() + mid, X.end());
        int fX1 = ask(X1);
        vector<int> PplusX1;
        PplusX1.reserve(P.size() + X1.size());
        PplusX1.insert(PplusX1.end(), P.begin(), P.end());
        PplusX1.insert(PplusX1.end(), X1.begin(), X1.end());
        int fPplusX1 = ask(PplusX1);
        long long ePX1 = (long long)fPplusX1 - fP - fX1;
        if (ePX1 > 0) {
            X.swap(X1);
        } else {
            X.swap(X2);
        }
    }
    return X[0];
}

// Find a neighbor in P of vertex v, knowing that such neighbor exists
int find_neighbor_in_P(int v, const vector<int>& P) {
    vector<int> S = P;
    while (S.size() > 1) {
        int mid = (int)S.size() / 2;
        vector<int> S1(S.begin(), S.begin() + mid);
        vector<int> S2(S.begin() + mid, S.end());
        int fS1 = ask(S1);
        vector<int> S1v = S1;
        S1v.push_back(v);
        int fS1v = ask(S1v);
        long long deg1 = (long long)fS1v - fS1;
        if (deg1 > 0) {
            S.swap(S1);
        } else {
            S.swap(S2);
        }
    }
    return S[0];
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

    vector<vector<int>> adj(n + 1);
    vector<int> parent(n + 1, 0), depth(n + 1, 0);

    vector<int> P;
    P.push_back(1);
    vector<bool> inP(n + 1, false);
    inP[1] = true;

    parent[1] = 0;
    depth[1] = 0;

    int fP = 0; // edges inside {1} is 0

    // Build a spanning tree
    while ((int)P.size() < n) {
        vector<int> U;
        U.reserve(n);
        for (int i = 1; i <= n; ++i)
            if (!inP[i]) U.push_back(i);

        int v = find_vertex_connected_to_P(P, fP, U);
        int u = find_neighbor_in_P(v, P);

        // add tree edge u-v
        adj[u].push_back(v);
        adj[v].push_back(u);
        parent[v] = u;
        depth[v] = depth[u] + 1;

        // update P and fP
        vector<int> Pplusv = P;
        Pplusv.push_back(v);
        fP = ask(Pplusv);

        P.push_back(v);
        inP[v] = true;
    }

    // 2-color the tree
    vector<int> color(n + 1, -1);
    queue<int> q;
    color[1] = 0;
    q.push(1);
    while (!q.empty()) {
        int v = q.front();
        q.pop();
        for (int to : adj[v]) {
            if (color[to] == -1) {
                color[to] = color[v] ^ 1;
                q.push(to);
            }
        }
    }

    vector<int> side[2];
    for (int i = 1; i <= n; ++i) {
        side[color[i]].push_back(i);
    }

    int fA = ask(side[0]);
    int fB = ask(side[1]);

    if (fA == 0 && fB == 0) {
        // Graph is bipartite
        cout << "Y " << side[0].size() << '\n';
        for (int i = 0; i < (int)side[0].size(); ++i) {
            if (i) cout << ' ';
            cout << side[0][i];
        }
        cout << '\n';
        cout.flush();
        return 0;
    }

    // Non-bipartite: find an odd cycle
    vector<int> C;
    if (fA > 0) C = side[0];
    else C = side[1];

    int fC = ask(C);

    int u = -1;
    int szC = (int)C.size();
    for (int i = 0; i < szC; ++i) {
        vector<int> S;
        S.reserve(szC - 1);
        for (int j = 0; j < szC; ++j) {
            if (j == i) continue;
            S.push_back(C[j]);
        }
        int fS = ask(S);
        long long deg = (long long)fC - fS;
        if (deg > 0) {
            u = C[i];
            break;
        }
    }

    // Find a neighbor w of u inside C
    vector<int> D;
    D.reserve(szC - 1);
    for (int x : C) if (x != u) D.push_back(x);

    int w;
    {
        vector<int> cur = D;
        while (cur.size() > 1) {
            int mid = (int)cur.size() / 2;
            vector<int> D1(cur.begin(), cur.begin() + mid);
            vector<int> D2(cur.begin() + mid, cur.end());
            int fD1 = ask(D1);
            vector<int> D1u = D1;
            D1u.push_back(u);
            int fD1u = ask(D1u);
            long long deg1 = (long long)fD1u - fD1;
            if (deg1 > 0) {
                cur.swap(D1);
            } else {
                cur.swap(D2);
            }
        }
        w = cur[0];
    }

    // Build path between u and w in the tree
    int a = u, b = w;
    vector<int> path_u, path_b;
    while (a != b) {
        if (depth[a] >= depth[b]) {
            path_u.push_back(a);
            a = parent[a];
        } else {
            path_b.push_back(b);
            b = parent[b];
        }
    }
    int lca = a;
    path_u.push_back(lca);
    reverse(path_b.begin(), path_b.end());

    vector<int> cycle = path_u;
    cycle.insert(cycle.end(), path_b.begin(), path_b.end());

    cout << "N " << cycle.size() << '\n';
    for (int i = 0; i < (int)cycle.size(); ++i) {
        if (i) cout << ' ';
        cout << cycle[i];
    }
    cout << '\n';
    cout.flush();

    return 0;
}