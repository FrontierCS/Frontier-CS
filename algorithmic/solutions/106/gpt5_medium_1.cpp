#include <bits/stdc++.h>
using namespace std;

static const bool DEBUG_LOCAL = false;

long long ask(const vector<int>& s) {
    cout << "? " << s.size() << "\n";
    for (size_t i = 0; i < s.size(); ++i) {
        if (i) cout << ' ';
        cout << s[i];
    }
    cout << "\n";
    cout.flush();
    long long m;
    if (!(cin >> m)) exit(0);
    if (m == -1) exit(0);
    return m;
}

vector<int> merge_sets(const vector<int>& a, const vector<int>& b) {
    vector<int> res;
    res.reserve(a.size() + b.size());
    res.insert(res.end(), a.begin(), a.end());
    res.insert(res.end(), b.begin(), b.end());
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;

    vector<int> all_nodes(n);
    for (int i = 0; i < n; ++i) all_nodes[i] = i + 1;

    // Data structures for building a spanning tree and coloring
    vector<int> parent(n + 1, -1);
    vector<int> depth(n + 1, 0);
    vector<int> color(n + 1, -1);
    vector<vector<int>> tree(n + 1);

    // Current discovered set T and its internal edge count E_T
    vector<int> T;
    T.push_back(1);
    long long E_T = 0; // Q({1}) = 0
    color[1] = 0;
    parent[1] = 0;
    depth[1] = 0;

    // Unknown set Uall
    vector<int> Uall;
    for (int i = 2; i <= n; ++i) Uall.push_back(i);

    // Helper lambdas

    function<int(const vector<int>&)> find_v_connecting_T;

    function<int(int, const vector<int>&)> find_neighbor_in_T;

    function<long long(const vector<int>&, const vector<int>&, long long, long long)> cross_edges; // returns #edges crossing A,B given q(A), q(B)

    function<int(const vector<int>&, const vector<int>&, long long)> find_cross_vertex; // find a in A with edge to B

    function<int(int, const vector<int>&)> find_neighbor_in_subset; // find neighbor of u in subset B

    function<pair<int,int>(const vector<int>&)> find_edge_in_set; // find an edge (u,v) inside S

    cross_edges = [&](const vector<int>& A, const vector<int>& B, long long qA, long long qB) -> long long {
        vector<int> AB = merge_sets(A, B);
        long long qAB = ask(AB);
        return qAB - qA - qB;
    };

    find_v_connecting_T = [&](const vector<int>& U) -> int {
        if (U.size() == 1) return U[0];
        size_t mid = U.size() / 2;
        vector<int> U1(U.begin(), U.begin() + mid);
        vector<int> U2(U.begin() + mid, U.end());

        long long qU1 = ask(U1);
        vector<int> TU1 = merge_sets(T, U1);
        long long qTU1 = ask(TU1);
        long long cross1 = qTU1 - E_T - qU1;

        if (cross1 > 0) return find_v_connecting_T(U1);
        else return find_v_connecting_T(U2);
    };

    find_neighbor_in_T = [&](int v, const vector<int>& S) -> int {
        if (S.size() == 1) return S[0];
        size_t mid = S.size() / 2;
        vector<int> S1(S.begin(), S.begin() + mid);
        vector<int> S2(S.begin() + mid, S.end());

        long long qS1 = ask(S1);
        vector<int> S1v = S1;
        S1v.push_back(v);
        long long qS1v = ask(S1v);
        long long deg1 = qS1v - qS1;

        if (deg1 > 0) return find_neighbor_in_T(v, S1);
        else return find_neighbor_in_T(v, S2);
    };

    find_cross_vertex = [&](const vector<int>& A, const vector<int>& B, long long qB) -> int {
        if (A.size() == 1) return A[0];
        size_t mid = A.size() / 2;
        vector<int> A1(A.begin(), A.begin() + mid);
        vector<int> A2(A.begin() + mid, A.end());

        long long qA1 = ask(A1);
        vector<int> A1B = merge_sets(A1, B);
        long long qA1B = ask(A1B);
        long long cross1 = qA1B - qA1 - qB;

        if (cross1 > 0) return find_cross_vertex(A1, B, qB);
        else return find_cross_vertex(A2, B, qB);
    };

    find_neighbor_in_subset = [&](int u, const vector<int>& B) -> int {
        if (B.size() == 1) return B[0];
        size_t mid = B.size() / 2;
        vector<int> B1(B.begin(), B.begin() + mid);
        vector<int> B2(B.begin() + mid, B.end());

        long long qB1 = ask(B1);
        vector<int> B1u = B1;
        B1u.push_back(u);
        long long qB1u = ask(B1u);
        long long degB1 = qB1u - qB1;

        if (degB1 > 0) return find_neighbor_in_subset(u, B1);
        else return find_neighbor_in_subset(u, B2);
    };

    find_edge_in_set = [&](const vector<int>& S) -> pair<int,int> {
        vector<int> cur = S;
        long long qCur = ask(cur);
        while (cur.size() > 2) {
            size_t mid = cur.size() / 2;
            vector<int> S1(cur.begin(), cur.begin() + mid);
            vector<int> S2(cur.begin() + mid, cur.end());

            long long q1 = ask(S1);
            if (q1 > 0) {
                cur = S1;
                qCur = q1;
                continue;
            }
            long long q2 = ask(S2);
            if (q2 > 0) {
                cur = S2;
                qCur = q2;
                continue;
            }
            // Edge crosses between S1 and S2
            long long qB = q2; // q(S2)
            int u = find_cross_vertex(S1, S2, qB);
            int v = find_neighbor_in_subset(u, S2);
            return {u, v};
        }
        // cur size == 2
        return {cur[0], cur[1]};
    };

    // Build the tree and coloring
    while ((int)T.size() < n) {
        // Find a vertex in Uall that connects to T
        int v = find_v_connecting_T(Uall);

        // Find one neighbor in T
        int y = find_neighbor_in_T(v, T);

        // Add tree edge and color
        parent[v] = y;
        depth[v] = depth[y] + 1;
        color[v] = color[y] ^ 1;
        tree[v].push_back(y);
        tree[y].push_back(v);

        // Update E_T by querying Q(T ∪ {v})
        vector<int> Tv = T;
        Tv.push_back(v);
        long long qTv = ask(Tv);
        long long deg_v_T = qTv - E_T; // since Q({v}) = 0
        E_T += deg_v_T;

        // Move v from Uall to T
        T.push_back(v);
        // Remove v from Uall
        vector<int> NU;
        NU.reserve(Uall.size());
        for (int x : Uall) if (x != v) NU.push_back(x);
        Uall.swap(NU);
    }

    // Build partitions
    vector<int> A, B;
    A.reserve(n);
    B.reserve(n);
    for (int i = 1; i <= n; ++i) {
        if (color[i] == 0) A.push_back(i);
        else B.push_back(i);
    }

    long long qA = A.empty() ? 0 : ask(A);
    if (qA == 0) {
        cout << "Y " << A.size() << "\n";
        for (size_t i = 0; i < A.size(); ++i) {
            if (i) cout << ' ';
            cout << A[i];
        }
        cout << "\n";
        cout.flush();
        return 0;
    }

    // Non-bipartite: find edge inside A or B
    pair<int,int> bad;
    if (qA > 0) {
        bad = find_edge_in_set(A);
    } else {
        long long qBv = B.empty() ? 0 : ask(B);
        if (qBv > 0) bad = find_edge_in_set(B);
        else {
            // Shouldn't happen if qA==0 and qB==0; graph bipartite
            cout << "Y " << A.size() << "\n";
            for (size_t i = 0; i < A.size(); ++i) {
                if (i) cout << ' ';
                cout << A[i];
            }
            cout << "\n";
            cout.flush();
            return 0;
        }
    }

    int u = bad.first, v = bad.second;

    // Get path between u and v in the tree
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
    int lca = uu;
    vector<int> cycle;
    for (int x : path_u) cycle.push_back(x);
    cycle.push_back(lca);
    reverse(path_v.begin(), path_v.end());
    for (int x : path_v) cycle.push_back(x);

    cout << "N " << cycle.size() << "\n";
    for (size_t i = 0; i < cycle.size(); ++i) {
        if (i) cout << ' ';
        cout << cycle[i];
    }
    cout << "\n";
    cout.flush();
    return 0;
}