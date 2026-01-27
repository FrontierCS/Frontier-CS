#include <bits/stdc++.h>
using namespace std;

static const int MAXQ = 50000;

int n;
long long qcount = 0;

int ask(const vector<int>& S) {
    if (S.empty()) return 0; // Never query empty set; treat as 0 edges.
    cout << "? " << (int)S.size() << '\n';
    for (int i = 0; i < (int)S.size(); ++i) {
        if (i) cout << ' ';
        cout << S[i];
    }
    cout << '\n';
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    ++qcount;
    return res;
}

vector<int> unite_sets(const vector<int>& A, const vector<int>& B) {
    vector<int> res;
    res.reserve(A.size() + B.size());
    res.insert(res.end(), A.begin(), A.end());
    res.insert(res.end(), B.begin(), B.end());
    // A and B are supposed to be disjoint in our usage; but ensure uniqueness just in case.
    sort(res.begin(), res.end());
    res.erase(unique(res.begin(), res.end()), res.end());
    return res;
}

int edges_between(const vector<int>& S, const vector<int>& T, int edgesS) {
    if (T.empty()) return 0;
    vector<int> U = unite_sets(S, T);
    int eU = ask(U);
    int eT = ask(T);
    return eU - edgesS - eT;
}

int find_candidate_recursive(const vector<int>& S, const vector<int>& U, int edgesS) {
    if (U.size() == 1) return U[0];
    int mid = (int)U.size() / 2;
    vector<int> L(U.begin(), U.begin() + mid);
    vector<int> R(U.begin() + mid, U.end());
    int eL = edges_between(S, L, edgesS);
    if (eL > 0) return find_candidate_recursive(S, L, edgesS);
    return find_candidate_recursive(S, R, edgesS);
}

// Returns a vertex v in U that has at least one edge to S; or -1 if none.
int find_candidate(const vector<int>& S, const vector<int>& U, int edgesS) {
    if (U.empty()) return -1;
    int e = edges_between(S, U, edgesS);
    if (e == 0) return -1;
    return find_candidate_recursive(S, U, edgesS);
}

int find_neighbor_in_set(int v, const vector<int>& S) {
    vector<int> cur = S;
    while (cur.size() > 1) {
        int mid = (int)cur.size() / 2;
        vector<int> L(cur.begin(), cur.begin() + mid);
        vector<int> R(cur.begin() + mid, cur.end());
        vector<int> Lplus = L;
        Lplus.push_back(v);
        int eLplus = ask(Lplus);
        int eL = ask(L);
        if (eLplus - eL > 0) {
            cur = L;
        } else {
            cur = R;
        }
    }
    return cur[0];
}

// Given C with E(C) > 0, find an edge (u, v) inside C.
pair<int,int> find_internal_edge_in_set(const vector<int>& C) {
    vector<int> R;
    int edgesR = 0;
    for (int x : C) {
        vector<int> Rplus = R;
        Rplus.push_back(x);
        int eRplus = ask(Rplus);
        if (eRplus - edgesR > 0) {
            // x has a neighbor in R
            int u = find_neighbor_in_set(x, R);
            return {u, x};
        } else {
            R.push_back(x);
            edgesR = eRplus; // unchanged, since no new internal edges
        }
    }
    // Should not reach here if E(C) > 0
    return {-1, -1};
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

    vector<vector<int>> g(n + 1);
    vector<int> parent(n + 1, -1);

    vector<int> S; // processed and connected set
    S.push_back(1);
    int edgesS = 0; // E(S) initially 0
    vector<int> U;
    for (int i = 2; i <= n; ++i) U.push_back(i);

    while ((int)S.size() < n) {
        int v = find_candidate(S, U, edgesS);
        if (v == -1) {
            // Graph is connected per statement, so this should not happen.
            // To be safe, if it happens, start new component.
            v = U.back();
        }
        int u = find_neighbor_in_set(v, S);
        g[u].push_back(v);
        g[v].push_back(u);
        parent[v] = u;

        // Add v to S
        S.push_back(v);
        // Update edgesS to E(S) by querying S
        edgesS = ask(S);

        // Remove v from U
        auto it = find(U.begin(), U.end(), v);
        if (it != U.end()) U.erase(it);
    }

    // Color the tree
    vector<int> color(n + 1, -1), depth(n + 1, 0);
    queue<int> q;
    color[1] = 0;
    depth[1] = 0;
    q.push(1);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : g[u]) {
            if (color[v] == -1) {
                color[v] = color[u] ^ 1;
                depth[v] = depth[u] + 1;
                q.push(v);
            }
        }
    }

    vector<int> A, B;
    for (int i = 1; i <= n; ++i) {
        if (color[i] == 0) A.push_back(i);
        else B.push_back(i);
    }

    int eA = ask(A);
    int eB = ask(B);

    if (eA == 0 && eB == 0) {
        cout << "Y " << (int)A.size() << '\n';
        for (int i = 0; i < (int)A.size(); ++i) {
            if (i) cout << ' ';
            cout << A[i];
        }
        cout << '\n';
        cout.flush();
        return 0;
    }

    vector<int> C = (eA > 0 ? A : B);
    pair<int,int> uv = find_internal_edge_in_set(C);
    int u = uv.first, v = uv.second;

    // Build parent and depth arrays for the tree
    parent.assign(n + 1, -1);
    depth.assign(n + 1, 0);
    queue<int> qb;
    vector<int> visited(n + 1, 0);
    qb.push(1);
    visited[1] = 1;
    parent[1] = 0;
    depth[1] = 0;
    while (!qb.empty()) {
        int x = qb.front(); qb.pop();
        for (int y : g[x]) {
            if (!visited[y]) {
                visited[y] = 1;
                parent[y] = x;
                depth[y] = depth[x] + 1;
                qb.push(y);
            }
        }
    }

    // Get path from u to v in tree
    vector<int> path_u, path_v;
    int uu = u, vv = v;
    while (uu != vv) {
        if (depth[uu] >= depth[vv]) {
            path_u.push_back(uu);
            uu = parent[uu];
        } else {
            path_v.push_back(vv);
            vv = parent[vv];
        }
    }
    vector<int> cycle;
    for (int x : path_u) cycle.push_back(x);
    cycle.push_back(uu); // LCA
    reverse(path_v.begin(), path_v.end());
    for (int x : path_v) cycle.push_back(x);
    // Now cycle is the path from u to v. The non-tree edge (u, v) closes the cycle.

    cout << "N " << (int)cycle.size() << '\n';
    for (int i = 0; i < (int)cycle.size(); ++i) {
        if (i) cout << ' ';
        cout << cycle[i];
    }
    cout << '\n';
    cout.flush();
    return 0;
}