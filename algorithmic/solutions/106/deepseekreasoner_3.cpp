#include <bits/stdc++.h>
using namespace std;

int n;
map<vector<int>, int> cache;

int query(vector<int> s) {
    sort(s.begin(), s.end());
    if (cache.count(s)) return cache[s];
    cout << "? " << s.size() << endl;
    for (size_t i = 0; i < s.size(); ++i) {
        if (i) cout << " ";
        cout << s[i];
    }
    cout << endl;
    cout.flush();
    int ans;
    cin >> ans;
    if (ans == -1) exit(0);
    cache[s] = ans;
    return ans;
}

// Find a vertex v in U that has at least one neighbor in T.
// eT = query(T) is already known.
int find_vertex(const vector<int>& T, int eT, const vector<int>& U) {
    if (U.size() == 1) return U[0];
    int mid = U.size() / 2;
    vector<int> A(U.begin(), U.begin() + mid);
    vector<int> B(U.begin() + mid, U.end());
    int eA = query(A);
    vector<int> TA = T;
    TA.insert(TA.end(), A.begin(), A.end());
    int eTA = query(TA);
    int cross = eTA - eT - eA;
    if (cross > 0) {
        return find_vertex(T, eT, A);
    } else {
        return find_vertex(T, eT, B);
    }
}

// Find a neighbor of v inside T (T is non-empty and contains at least one neighbor).
int find_neighbor(int v, const vector<int>& T) {
    if (T.size() == 1) return T[0];
    int mid = T.size() / 2;
    vector<int> A(T.begin(), T.begin() + mid);
    vector<int> B(T.begin() + mid, T.end());
    int eA = query(A);
    vector<int> A_v = A;
    A_v.push_back(v);
    int eAv = query(A_v);
    if (eAv > eA) {
        return find_neighbor(v, A);
    } else {
        return find_neighbor(v, B);
    }
}

// Given a set S with at least one edge inside, find any edge (u,w) with both endpoints in S.
pair<int,int> find_edge_in_S(const vector<int>& S) {
    if (S.size() == 2) {
        // We know there is at least one edge, so this pair must be adjacent.
        return {S[0], S[1]};
    }
    int mid = S.size() / 2;
    vector<int> A(S.begin(), S.begin() + mid);
    vector<int> B(S.begin() + mid, S.end());
    int eA = query(A);
    int eB = query(B);
    if (eA > 0) return find_edge_in_S(A);
    if (eB > 0) return find_edge_in_S(B);
    // Otherwise there is a cross edge between A and B.
    if (A.size() > B.size()) swap(A, B); // iterate over the smaller set
    int eB_val = eB;
    for (int u : A) {
        vector<int> Bplus = B;
        Bplus.push_back(u);
        int eBplus = query(Bplus);
        if (eBplus > eB_val) {
            // u has a neighbor in B, find it by binary search.
            vector<int> Bcur = B;
            while (Bcur.size() > 1) {
                int m = Bcur.size() / 2;
                vector<int> B1(Bcur.begin(), Bcur.begin() + m);
                vector<int> B2(Bcur.begin() + m, Bcur.end());
                int eB1 = query(B1);
                vector<int> B1plus = B1;
                B1plus.push_back(u);
                int eB1plus = query(B1plus);
                if (eB1plus > eB1) {
                    Bcur = B1;
                } else {
                    Bcur = B2;
                }
            }
            int w = Bcur[0];
            return {u, w};
        }
    }
    // Should never reach here because we know there is a cross edge.
    return {-1, -1};
}

int get_lca(int u, int v, const vector<int>& depth, const vector<int>& parent) {
    while (depth[u] > depth[v]) u = parent[u];
    while (depth[v] > depth[u]) v = parent[v];
    while (u != v) {
        u = parent[u];
        v = parent[v];
    }
    return u;
}

vector<int> get_path(int u, int v, const vector<int>& depth, const vector<int>& parent) {
    int lca = get_lca(u, v, depth, parent);
    vector<int> path;
    // from u to lca (excluding lca)
    int x = u;
    while (x != lca) {
        path.push_back(x);
        x = parent[x];
    }
    path.push_back(lca);
    vector<int> temp;
    x = v;
    while (x != lca) {
        temp.push_back(x);
        x = parent[x];
    }
    reverse(temp.begin(), temp.end());
    path.insert(path.end(), temp.begin(), temp.end());
    return path;
}

int main() {
    cin >> n;
    vector<int> parent(n+1), color(n+1), depth(n+1);
    // start with vertex 1
    parent[1] = 1;
    color[1] = 0;
    depth[1] = 0;
    vector<int> T = {1};
    vector<int> U;
    for (int i = 2; i <= n; ++i) U.push_back(i);

    while (!U.empty()) {
        int eT = query(T);
        int v = find_vertex(T, eT, U);
        int u = find_neighbor(v, T);
        parent[v] = u;
        color[v] = color[u] ^ 1;
        depth[v] = depth[u] + 1;
        T.push_back(v);
        U.erase(find(U.begin(), U.end(), v));
    }

    vector<int> L, R;
    for (int i = 1; i <= n; ++i) {
        if (color[i] == 0) L.push_back(i);
        else R.push_back(i);
    }

    int eL = 0, eR = 0;
    if (!L.empty()) eL = query(L);
    if (!R.empty()) eR = query(R);

    if (eL == 0 && eR == 0) {
        cout << "Y " << L.size() << endl;
        for (size_t i = 0; i < L.size(); ++i) {
            if (i) cout << " ";
            cout << L[i];
        }
        cout << endl;
    } else {
        vector<int> S;
        if (eL > 0) S = L;
        else S = R;
        auto [u, w] = find_edge_in_S(S);
        vector<int> cycle = get_path(u, w, depth, parent);
        cout << "N " << cycle.size() << endl;
        for (size_t i = 0; i < cycle.size(); ++i) {
            if (i) cout << " ";
            cout << cycle[i];
        }
        cout << endl;
    }

    return 0;
}