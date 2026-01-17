#include <bits/stdc++.h>
using namespace std;

static int n;
static int qcnt = 0;

static long long ask(const vector<int>& s) {
    if ((int)s.size() <= 1) return 0;
    if (++qcnt > 50000) exit(0);
    cout << "? " << s.size() << "\n";
    for (int i = 0; i < (int)s.size(); i++) {
        if (i) cout << ' ';
        cout << s[i];
    }
    cout << "\n";
    cout.flush();

    long long ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

static vector<int> concatSets(const vector<int>& a, const vector<int>& b) {
    vector<int> res;
    res.reserve(a.size() + b.size());
    res.insert(res.end(), a.begin(), a.end());
    res.insert(res.end(), b.begin(), b.end());
    return res;
}

static int findConnectedVertex(const vector<int>& T, long long qT, const vector<int>& U) {
    if (U.size() == 1) return U[0];
    int mid = (int)U.size() / 2;
    vector<int> A(U.begin(), U.begin() + mid);
    vector<int> B(U.begin() + mid, U.end());

    long long qA = ask(A);
    vector<int> TA = concatSets(T, A);
    long long qTA = ask(TA);
    long long eTA = qTA - qT - qA;

    if (eTA > 0) return findConnectedVertex(T, qT, A);
    return findConnectedVertex(T, qT, B);
}

static int findNeighborInSet(int v, const vector<int>& T) {
    if (T.size() == 1) return T[0];
    int mid = (int)T.size() / 2;
    vector<int> A(T.begin(), T.begin() + mid);
    vector<int> B(T.begin() + mid, T.end());

    long long qA = ask(A);
    vector<int> Au = A;
    Au.push_back(v);
    long long qAu = ask(Au);
    long long e = qAu - qA; // edges between v and A

    if (e > 0) return findNeighborInSet(v, A);
    return findNeighborInSet(v, B);
}

static int findVertexWithNeighborAcross(const vector<int>& A, const vector<int>& B, long long qB) {
    if (A.size() == 1) return A[0];
    int mid = (int)A.size() / 2;
    vector<int> A1(A.begin(), A.begin() + mid);
    vector<int> A2(A.begin() + mid, A.end());

    long long qA1 = ask(A1);
    vector<int> U = concatSets(A1, B);
    long long qU = ask(U);
    long long e = qU - qA1 - qB; // edges between A1 and B

    if (e > 0) return findVertexWithNeighborAcross(A1, B, qB);
    return findVertexWithNeighborAcross(A2, B, qB);
}

static pair<int,int> findEdgeInside(const vector<int>& S, long long qS = -1) {
    if (qS == -1) qS = ask(S);
    if (S.size() == 2) return {S[0], S[1]};

    int mid = (int)S.size() / 2;
    vector<int> A(S.begin(), S.begin() + mid);
    vector<int> B(S.begin() + mid, S.end());

    long long qA = ask(A);
    if (qA > 0) return findEdgeInside(A, qA);

    long long qB = ask(B);
    if (qB > 0) return findEdgeInside(B, qB);

    // must be a cross edge between A and B
    int u = findVertexWithNeighborAcross(A, B, qB);
    int v = findNeighborInSet(u, B);
    return {u, v};
}

static vector<int> getTreePath(int u, int v, const vector<int>& parent, const vector<int>& depth) {
    vector<int> pu, pv;
    int uu = u, vv = v;
    while (uu != vv) {
        if (depth[uu] >= depth[vv]) {
            pu.push_back(uu);
            uu = parent[uu];
        } else {
            pv.push_back(vv);
            vv = parent[vv];
        }
    }
    pu.push_back(uu); // LCA
    reverse(pv.begin(), pv.end());
    pu.insert(pu.end(), pv.begin(), pv.end());
    return pu;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;

    vector<int> parent(n + 1, 0), depth(n + 1, 0);
    vector<vector<int>> treeAdj(n + 1);

    vector<int> T;
    T.reserve(n);
    T.push_back(1);

    vector<int> U;
    U.reserve(n);
    for (int i = 2; i <= n; i++) U.push_back(i);

    for (int iter = 0; iter < n - 1; iter++) {
        long long qT = ask(T);
        int x = findConnectedVertex(T, qT, U);
        int p = findNeighborInSet(x, T);

        parent[x] = p;
        depth[x] = depth[p] + 1;
        treeAdj[p].push_back(x);
        treeAdj[x].push_back(p);

        T.push_back(x);
        auto it = find(U.begin(), U.end(), x);
        if (it != U.end()) U.erase(it);
        else exit(0);
    }

    vector<int> color(n + 1, -1);
    queue<int> q;
    color[1] = 0;
    q.push(1);
    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int to : treeAdj[v]) {
            if (color[to] == -1) {
                color[to] = color[v] ^ 1;
                q.push(to);
            }
        }
    }

    vector<int> C0, C1;
    for (int i = 1; i <= n; i++) {
        if (color[i] == 0) C0.push_back(i);
        else C1.push_back(i);
    }

    long long q0 = ask(C0);
    long long q1 = ask(C1);

    if (q0 == 0 && q1 == 0) {
        cout << "Y " << C0.size() << "\n";
        for (int i = 0; i < (int)C0.size(); i++) {
            if (i) cout << ' ';
            cout << C0[i];
        }
        cout << "\n";
        cout.flush();
        return 0;
    }

    vector<int> S = (q0 > 0 ? C0 : C1);
    long long qS = (q0 > 0 ? q0 : q1);
    auto [u, v] = findEdgeInside(S, qS);

    vector<int> cycle = getTreePath(u, v, parent, depth);

    cout << "N " << cycle.size() << "\n";
    for (int i = 0; i < (int)cycle.size(); i++) {
        if (i) cout << ' ';
        cout << cycle[i];
    }
    cout << "\n";
    cout.flush();
    return 0;
}