#include <bits/stdc++.h>
using namespace std;

static const int QUERY_LIMIT = 50000;

struct Interactor {
    int q = 0;

    long long ask(const vector<int>& s) {
        if (s.empty()) return 0;
        if (++q > QUERY_LIMIT) exit(0);
        cout << "? " << s.size() << "\n";
        for (int i = 0; i < (int)s.size(); i++) {
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

    long long inducedEdges(const vector<int>& s) {
        if (s.size() <= 1) return 0;
        return ask(s);
    }
};

static inline vector<int> concatSets(const vector<int>& a, const vector<int>& b) {
    vector<int> res;
    res.reserve(a.size() + b.size());
    res.insert(res.end(), a.begin(), a.end());
    res.insert(res.end(), b.begin(), b.end());
    return res;
}

int findVertexConnectedToA(Interactor& it, const vector<int>& A, long long fA, const vector<int>& cand) {
    if ((int)cand.size() == 1) return cand[0];
    int mid = (int)cand.size() / 2;
    vector<int> left(cand.begin(), cand.begin() + mid);
    vector<int> right(cand.begin() + mid, cand.end());

    long long fLeft = it.inducedEdges(left);
    vector<int> uni = concatSets(A, left);
    long long fUni = it.inducedEdges(uni);
    long long e = fUni - fA - fLeft;
    if (e > 0) return findVertexConnectedToA(it, A, fA, left);
    return findVertexConnectedToA(it, A, fA, right);
}

int findNeighborInA(Interactor& it, int v, const vector<int>& A) {
    if ((int)A.size() == 1) return A[0];
    int mid = (int)A.size() / 2;
    vector<int> left(A.begin(), A.begin() + mid);
    vector<int> right(A.begin() + mid, A.end());

    long long fLeft = it.inducedEdges(left);
    vector<int> uni = left;
    uni.push_back(v);
    long long fUni = it.inducedEdges(uni);
    long long e = fUni - fLeft;
    if (e > 0) return findNeighborInA(it, v, left);
    return findNeighborInA(it, v, right);
}

int findVertexWithCrossEdge(Interactor& it, const vector<int>& S, const vector<int>& T, long long fT) {
    if ((int)S.size() == 1) return S[0];
    int mid = (int)S.size() / 2;
    vector<int> left(S.begin(), S.begin() + mid);
    vector<int> right(S.begin() + mid, S.end());

    long long fLeft = it.inducedEdges(left);
    vector<int> uni = concatSets(left, T);
    long long fUni = it.inducedEdges(uni);
    long long e = fUni - fLeft - fT;
    if (e > 0) return findVertexWithCrossEdge(it, left, T, fT);
    return findVertexWithCrossEdge(it, right, T, fT);
}

int findNeighborInSet(Interactor& it, int x, const vector<int>& T) {
    if ((int)T.size() == 1) return T[0];
    int mid = (int)T.size() / 2;
    vector<int> left(T.begin(), T.begin() + mid);
    vector<int> right(T.begin() + mid, T.end());

    long long fLeft = it.inducedEdges(left);
    vector<int> uni = left;
    uni.push_back(x);
    long long fUni = it.inducedEdges(uni);
    long long e = fUni - fLeft;
    if (e > 0) return findNeighborInSet(it, x, left);
    return findNeighborInSet(it, x, right);
}

pair<int,int> findEdgeBetweenSets(Interactor& it, const vector<int>& L, const vector<int>& R) {
    long long fR = it.inducedEdges(R);
    int x = findVertexWithCrossEdge(it, L, R, fR);
    int y = findNeighborInSet(it, x, R);
    return {x, y};
}

pair<int,int> findEdgeWithinSet(Interactor& it, const vector<int>& C) {
    if ((int)C.size() == 2) return {C[0], C[1]};
    int mid = (int)C.size() / 2;
    vector<int> L(C.begin(), C.begin() + mid);
    vector<int> R(C.begin() + mid, C.end());

    long long fL = it.inducedEdges(L);
    if (fL > 0) return findEdgeWithinSet(it, L);

    long long fR = it.inducedEdges(R);
    if (fR > 0) return findEdgeWithinSet(it, R);

    return findEdgeBetweenSets(it, L, R);
}

static inline void eraseValue(vector<int>& v, int x) {
    for (int i = 0; i < (int)v.size(); i++) {
        if (v[i] == x) {
            v[i] = v.back();
            v.pop_back();
            return;
        }
    }
}

vector<int> getTreePath(int u, int v, const vector<int>& parent, const vector<int>& depth) {
    int a = u, b = v;
    vector<int> up, down;
    while (depth[a] > depth[b]) { up.push_back(a); a = parent[a]; }
    while (depth[b] > depth[a]) { down.push_back(b); b = parent[b]; }
    while (a != b) {
        up.push_back(a); a = parent[a];
        down.push_back(b); b = parent[b];
    }
    up.push_back(a); // LCA
    reverse(down.begin(), down.end());
    up.insert(up.end(), down.begin(), down.end());
    return up;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    Interactor it;

    vector<int> parent(n + 1, 0), depth(n + 1, 0);

    vector<int> A;
    A.push_back(1);

    vector<int> R;
    R.reserve(max(0, n - 1));
    for (int i = 2; i <= n; i++) R.push_back(i);

    while (!R.empty()) {
        long long fA = it.inducedEdges(A);

        int v = findVertexConnectedToA(it, A, fA, R);
        int u = findNeighborInA(it, v, A);

        parent[v] = u;
        depth[v] = depth[u] + 1;

        A.push_back(v);
        eraseValue(R, v);
    }

    vector<int> part[2];
    for (int i = 1; i <= n; i++) part[depth[i] & 1].push_back(i);

    long long inside0 = it.inducedEdges(part[0]);
    long long inside1 = it.inducedEdges(part[1]);

    if (inside0 == 0 && inside1 == 0) {
        cout << "Y " << part[0].size() << "\n";
        for (int i = 0; i < (int)part[0].size(); i++) {
            if (i) cout << ' ';
            cout << part[0][i];
        }
        cout << "\n";
        cout.flush();
        return 0;
    }

    const vector<int>& C = (inside0 > 0 ? part[0] : part[1]);
    pair<int,int> e = findEdgeWithinSet(it, C);
    int a = e.first, b = e.second;

    vector<int> cycle = getTreePath(a, b, parent, depth);
    cout << "N " << cycle.size() << "\n";
    for (int i = 0; i < (int)cycle.size(); i++) {
        if (i) cout << ' ';
        cout << cycle[i];
    }
    cout << "\n";
    cout.flush();
    return 0;
}