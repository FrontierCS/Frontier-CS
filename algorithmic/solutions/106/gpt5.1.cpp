#include <bits/stdc++.h>
using namespace std;

long long ask(const vector<int>& S) {
    if (S.size() <= 1) return 0; // no edges possible
    cout << "? " << S.size() << '\n';
    for (size_t i = 0; i < S.size(); ++i) {
        if (i) cout << ' ';
        cout << S[i];
    }
    cout << '\n' << flush;
    long long res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

bool hasCross(const vector<int>& S, const vector<int>& U, long long eS) {
    if (S.empty() || U.empty()) return false;
    long long eU = ask(U);
    vector<int> SU;
    SU.reserve(S.size() + U.size());
    SU.insert(SU.end(), S.begin(), S.end());
    SU.insert(SU.end(), U.begin(), U.end());
    long long eSU = ask(SU);
    long long cross = eSU - eS - eU;
    return cross > 0;
}

int findVertexWithNeighbor_rec(const vector<int>& S, const vector<int>& U, long long eS) {
    if (U.size() == 1) return U[0];
    int half = (int)U.size() / 2;
    vector<int> A(U.begin(), U.begin() + half);
    vector<int> B(U.begin() + half, U.end());
    if (hasCross(S, A, eS)) {
        return findVertexWithNeighbor_rec(S, A, eS);
    } else {
        return findVertexWithNeighbor_rec(S, B, eS);
    }
}

int findVertexWithNeighbor(const vector<int>& S, const vector<int>& T, long long eS) {
    return findVertexWithNeighbor_rec(S, T, eS);
}

bool hasNeighborInSubset(const vector<int>& subset, int v) {
    if (subset.empty()) return false;
    long long eSubset = ask(subset);
    vector<int> Av = subset;
    Av.push_back(v);
    long long eAv = ask(Av);
    long long deg = eAv - eSubset;
    return deg > 0;
}

int findNeighborInS_rec(const vector<int>& U, int v) {
    if (U.size() == 1) return U[0];
    int half = (int)U.size() / 2;
    vector<int> A(U.begin(), U.begin() + half);
    vector<int> B(U.begin() + half, U.end());
    if (hasNeighborInSubset(A, v)) {
        return findNeighborInS_rec(A, v);
    } else {
        return findNeighborInS_rec(B, v);
    }
}

int findNeighborInS(const vector<int>& S, int v) {
    return findNeighborInS_rec(S, v);
}

pair<int,int> findEdgeInPart(const vector<int>& P, long long eP);

pair<int,int> findEdgeBetweenSets(const vector<int>& A, const vector<int>& B) {
    long long eA = ask(A); // may be 0
    int v = findVertexWithNeighbor(A, B, eA);
    int u = findNeighborInS(A, v);
    return {u, v};
}

pair<int,int> findEdgeInPart(const vector<int>& P, long long eP) {
    if (P.size() == 2) {
        return {P[0], P[1]};
    }
    int half = (int)P.size() / 2;
    vector<int> A(P.begin(), P.begin() + half);
    vector<int> B(P.begin() + half, P.end());

    long long eA = ask(A);
    if (eA > 0) {
        return findEdgeInPart(A, eA);
    }
    long long eB = ask(B);
    if (eB > 0) {
        return findEdgeInPart(B, eB);
    }
    // All edges are between A and B
    return findEdgeBetweenSets(A, B);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "Y 1\n1\n" << flush;
        return 0;
    }

    vector<vector<int>> adj(n + 1);

    vector<int> S, T;
    S.push_back(1);
    for (int i = 2; i <= n; ++i) T.push_back(i);

    long long edges_S = 0; // edges in {1}

    while (!T.empty()) {
        int v = findVertexWithNeighbor(S, T, edges_S);
        int u = findNeighborInS(S, v);

        adj[u].push_back(v);
        adj[v].push_back(u);

        S.push_back(v);
        auto it = find(T.begin(), T.end(), v);
        if (it != T.end()) T.erase(it);

        edges_S = ask(S);
    }

    vector<int> color(n + 1, -1), parent(n + 1, -1), depth(n + 1, 0);
    queue<int> q;
    q.push(1);
    color[1] = 0;
    parent[1] = 0;
    depth[1] = 0;

    while (!q.empty()) {
        int x = q.front(); q.pop();
        for (int y : adj[x]) {
            if (color[y] == -1) {
                color[y] = color[x] ^ 1;
                parent[y] = x;
                depth[y] = depth[x] + 1;
                q.push(y);
            }
        }
    }

    vector<int> part0, part1;
    for (int v = 1; v <= n; ++v) {
        if (color[v] == 0) part0.push_back(v);
        else part1.push_back(v);
    }

    long long e0 = (part0.size() <= 1 ? 0 : ask(part0));
    long long e1 = (part1.size() <= 1 ? 0 : ask(part1));

    if (e0 == 0 && e1 == 0) {
        cout << "Y " << part0.size() << '\n';
        for (size_t i = 0; i < part0.size(); ++i) {
            if (i) cout << ' ';
            cout << part0[i];
        }
        cout << '\n' << flush;
        return 0;
    } else {
        vector<int> P;
        long long eP;
        if (e0 > 0) {
            P = part0;
            eP = e0;
        } else {
            P = part1;
            eP = e1;
        }

        pair<int,int> edge = findEdgeInPart(P, eP);
        int u = edge.first;
        int v = edge.second;

        vector<int> path_u, path_v;
        int a = u, b = v;
        while (a != b) {
            if (depth[a] >= depth[b]) {
                path_u.push_back(a);
                a = parent[a];
            } else {
                path_v.push_back(b);
                b = parent[b];
            }
        }
        int lca = a;
        path_u.push_back(lca);
        reverse(path_v.begin(), path_v.end());
        for (int x : path_v) path_u.push_back(x);

        int L = (int)path_u.size();
        cout << "N " << L << '\n';
        for (int i = 0; i < L; ++i) {
            if (i) cout << ' ';
            cout << path_u[i];
        }
        cout << '\n' << flush;
    }

    return 0;
}