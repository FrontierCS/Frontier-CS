#include <bits/stdc++.h>
using namespace std;

using ll = long long;

int n;

ll ask(const vector<int>& S) {
    int k = (int)S.size();
    if (k == 0) {
        // Problem forbids empty queries; should never happen
        return 0;
    }
    cout << "? " << k << '\n';
    for (int i = 0; i < k; ++i) {
        if (i) cout << ' ';
        cout << S[i];
    }
    cout << '\n';
    cout.flush();
    ll res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

vector<int> merge_sets(const vector<int>& A, const vector<int>& B) {
    vector<int> R = A;
    R.insert(R.end(), B.begin(), B.end());
    return R;
}

pair<vector<int>, vector<int>> split_half(const vector<int>& S) {
    int m = (int)S.size();
    int mid = m / 2;
    vector<int> A(S.begin(), S.begin() + mid);
    vector<int> B(S.begin() + mid, S.end());
    if (A.empty()) { // ensure non-empty parts
        A.push_back(B.back());
        B.pop_back();
    }
    return {A, B};
}

// Find a vertex u in U such that there is an edge between u and any vertex in S.
// Assumes S and U are non-empty and cross(S, U) > 0.
int findVertexConnectedToSet(const vector<int>& S, const vector<int>& U) {
    vector<int> cur = U;
    while (cur.size() > 1) {
        auto [A, B] = split_half(cur);
        ll eA = ask(A);
        vector<int> SA = merge_sets(S, A);
        ll eSA = ask(SA);
        // cross(S, A) = eSA - eS - eA, but eS is not passed; we can use property:
        // We don't have eS here; but we only need to know if cross(S, A) > 0.
        // cross(S, A) > 0 <=> eSA - eA > eS. We don't have eS number.
        // Instead, compute eS once outside and pass as static/global cache? Let's compute here once per recursion:
        // To avoid extra queries each step, compute eS once outside and capture via lambda was not used.
        // We'll compute eS first time outside function.
        // To keep code simple, we will hold eS as static thread_local in this call using a closure-like trick.
        // But C++ doesn't have closures easily; Instead, we refactor to a version with eS as global for this search.
        // For now, break to reimplement with helper including eS.
        // Placeholder
        return -1;
    }
    return cur[0];
}

// Helper with known eS, find u in U connected to S
int findVertexConnectedToSet_with_eS(const vector<int>& S, ll eS, const vector<int>& U) {
    vector<int> cur = U;
    while (cur.size() > 1) {
        auto [A, B] = split_half(cur);
        ll eA = ask(A);
        vector<int> SA = merge_sets(S, A);
        ll eSA = ask(SA);
        ll cross1 = eSA - eS - eA;
        if (cross1 > 0) cur = A;
        else cur = B;
    }
    return cur[0];
}

// Find a neighbor of u inside set S (non-empty), assuming u has at least one neighbor in S.
int findNeighborInSet(int u, const vector<int>& S) {
    vector<int> cur = S;
    while (cur.size() > 1) {
        auto [A, B] = split_half(cur);
        ll eA = ask(A);
        vector<int> Au = A;
        Au.push_back(u);
        ll eAu = ask(Au);
        if (eAu - eA > 0) {
            cur = A;
        } else {
            cur = B;
        }
    }
    return cur[0];
}

// Find an adjacent pair within set Z where ask(Z) > 0; returns pair (u, v)
pair<int,int> findEdgeWithinSet(vector<int> Z) {
    while (true) {
        if (Z.size() == 2) return {Z[0], Z[1]};
        auto [A, B] = split_half(Z);
        ll eA = ask(A);
        if (eA > 0) {
            Z = A;
            continue;
        }
        ll eB = ask(B);
        if (eB > 0) {
            Z = B;
            continue;
        }
        // No internal edges in A or B; must be cross edges between A and B
        ll eB_saved = eB; // reuse
        // Find u in A with neighbor in B
        vector<int> curA = A;
        while (curA.size() > 1) {
            auto [A1, A2] = split_half(curA);
            ll eA1 = ask(A1);
            vector<int> A1B = merge_sets(A1, B);
            ll eA1B = ask(A1B);
            ll cross1 = eA1B - eA1 - eB_saved;
            if (cross1 > 0) curA = A1;
            else curA = A2;
        }
        int u = curA[0];
        int v = findNeighborInSet(u, B);
        return {u, v};
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;

    vector<int> parent(n+1, -1), depth(n+1, 0), color(n+1, 0);
    vector<vector<int>> adj(n+1);
    vector<int> S; S.reserve(n);
    vector<char> inS(n+1, 0);

    // Start with vertex 1 as root
    S.push_back(1);
    inS[1] = 1;
    parent[1] = 0;
    depth[1] = 0;
    color[1] = 0;

    while ((int)S.size() < n) {
        // Build U = V \ S
        vector<int> U;
        for (int i = 1; i <= n; ++i) if (!inS[i]) U.push_back(i);

        // Find a vertex in U that has an edge to S
        ll eS = ask(S);
        // Using binary search over U to find existence
        // Pre-check cross(S, U) > 0
        ll eU = ask(U);
        vector<int> SU = merge_sets(S, U);
        ll eSU = ask(SU);
        ll crossSU = eSU - eS - eU;
        int u;
        if (crossSU > 0) {
            u = findVertexConnectedToSet_with_eS(S, eS, U);
        } else {
            // Should not happen for connected graph unless S empty (which it's not after first add)
            // But in case, just add an arbitrary vertex from U as a new component root
            u = U[0];
        }

        // If cross>0, find neighbor in S
        int p = -1;
        if (crossSU > 0) {
            p = findNeighborInSet(u, S);
            // Add tree edge u-p
            parent[u] = p;
            depth[u] = depth[p] + 1;
            color[u] = color[p] ^ 1;
            adj[u].push_back(p);
            adj[p].push_back(u);
        } else {
            parent[u] = 0;
            depth[u] = 0;
            color[u] = 0;
        }

        // Add u to S
        S.push_back(u);
        inS[u] = 1;
    }

    // Build color classes
    vector<int> C0, C1;
    for (int i = 1; i <= n; ++i) {
        if (color[i] == 0) C0.push_back(i);
        else C1.push_back(i);
    }

    ll e0 = C0.empty() ? 0 : ask(C0);
    ll e1 = C1.empty() ? 0 : ask(C1);

    if (e0 == 0 && e1 == 0) {
        cout << "Y " << C0.size() << '\n';
        for (size_t i = 0; i < C0.size(); ++i) {
            if (i) cout << ' ';
            cout << C0[i];
        }
        cout << '\n';
        cout.flush();
        return 0;
    }

    // Not bipartite: find odd cycle
    vector<int> Z = (e0 > 0 ? C0 : C1);
    auto [u, v] = findEdgeWithinSet(Z);

    // Get path between u and v in the built tree
    int a = u, b = v;
    vector<int> path_u, path_b;
    int uu = a, vv = b;
    while (depth[uu] > depth[vv]) { path_u.push_back(uu); uu = parent[uu]; }
    while (depth[vv] > depth[uu]) { path_b.push_back(vv); vv = parent[vv]; }
    while (uu != vv) {
        path_u.push_back(uu);
        path_b.push_back(vv);
        uu = parent[uu];
        vv = parent[vv];
    }
    int lca = uu;
    vector<int> cycle;
    for (int x : path_u) cycle.push_back(x);
    cycle.push_back(lca);
    reverse(path_b.begin(), path_b.end());
    for (int x : path_b) cycle.push_back(x);
    // Now cycle is path from u to v. The edge (v,u) closes the cycle.

    cout << "N " << cycle.size() << '\n';
    for (size_t i = 0; i < cycle.size(); ++i) {
        if (i) cout << ' ';
        cout << cycle[i];
    }
    cout << '\n';
    cout.flush();

    return 0;
}