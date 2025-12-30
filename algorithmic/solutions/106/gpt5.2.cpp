#include <bits/stdc++.h>
using namespace std;

static int n;
static int queryCount = 0;

static long long ask(const vector<int>& s) {
    int k = (int)s.size();
    if (k <= 1) return 0; // 0 edges inside empty or singleton set
    ++queryCount;
    cout << "? " << k << "\n";
    for (int i = 0; i < k; i++) {
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

static vector<int> merged(const vector<int>& a, const vector<int>& b) {
    vector<int> r;
    r.reserve(a.size() + b.size());
    r.insert(r.end(), a.begin(), a.end());
    r.insert(r.end(), b.begin(), b.end());
    return r;
}

static int findVertexConnectedToVisited(const vector<int>& V, long long eV, const vector<int>& U) {
    vector<int> cand = U;
    while (cand.size() > 1) {
        int mid = (int)cand.size() / 2;
        vector<int> L(cand.begin(), cand.begin() + mid);
        vector<int> R(cand.begin() + mid, cand.end());

        long long eL = ask(L);
        vector<int> VL = merged(V, L);
        long long eVL = ask(VL);
        long long cross = eVL - eV - eL;

        if (cross > 0) cand.swap(L);
        else cand.swap(R);
    }
    return cand[0];
}

static int findNeighborInVisited(int v, const vector<int>& V, long long degToV) {
    vector<int> cand = V;
    long long degCand = degToV;

    while (cand.size() > 1) {
        int mid = (int)cand.size() / 2;
        vector<int> L(cand.begin(), cand.begin() + mid);
        vector<int> R(cand.begin() + mid, cand.end());

        long long eL = ask(L);
        vector<int> Lv = L;
        Lv.push_back(v);
        long long eLv = ask(Lv);
        long long degL = eLv - eL;

        if (degL > 0) {
            cand.swap(L);
            degCand = degL;
        } else {
            cand.swap(R);
            degCand = degCand - degL;
        }
    }
    return cand[0];
}

static pair<int,int> findCrossEdgeIndependent(const vector<int>& A, const vector<int>& B) {
    // Assumes e(A)=e(B)=0 and there is at least one edge between A and B.
    vector<int> candA = A;
    while (candA.size() > 1) {
        int mid = (int)candA.size() / 2;
        vector<int> L(candA.begin(), candA.begin() + mid);
        vector<int> R(candA.begin() + mid, candA.end());
        vector<int> LB = merged(L, B);
        long long eLB = ask(LB); // equals #edges between L and B since both independent
        if (eLB > 0) candA.swap(L);
        else candA.swap(R);
    }
    int u = candA[0];

    vector<int> candB = B;
    while (candB.size() > 1) {
        int mid = (int)candB.size() / 2;
        vector<int> L(candB.begin(), candB.begin() + mid);
        vector<int> R(candB.begin() + mid, candB.end());
        vector<int> Lu = L;
        Lu.push_back(u);
        long long eLu = ask(Lu); // equals #edges between u and L since L independent
        if (eLu > 0) candB.swap(L);
        else candB.swap(R);
    }
    int v = candB[0];
    return {u, v};
}

static pair<int,int> findAnyEdgeInside(vector<int> S, long long eS) {
    // Returns endpoints of some edge within S. Requires eS > 0.
    while (true) {
        if (S.size() == 2) return {S[0], S[1]};

        int mid = (int)S.size() / 2;
        vector<int> A(S.begin(), S.begin() + mid);
        vector<int> B(S.begin() + mid, S.end());

        long long eA = ask(A);
        if (eA > 0) {
            S.swap(A);
            eS = eA;
            continue;
        }
        long long eB = ask(B);
        if (eB > 0) {
            S.swap(B);
            eS = eB;
            continue;
        }

        // No edges inside A or B, so any edge is cross between A and B
        return findCrossEdgeIndependent(A, B);
    }
}

static vector<int> getTreePath(int a, int b, const vector<int>& parent, const vector<int>& depth) {
    int u = a, v = b;
    vector<int> pa, pb;
    while (depth[u] > depth[v]) {
        pa.push_back(u);
        u = parent[u];
    }
    while (depth[v] > depth[u]) {
        pb.push_back(v);
        v = parent[v];
    }
    while (u != v) {
        pa.push_back(u);
        pb.push_back(v);
        u = parent[u];
        v = parent[v];
    }
    pa.push_back(u); // LCA
    reverse(pb.begin(), pb.end());
    pa.insert(pa.end(), pb.begin(), pb.end());
    return pa;
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

    vector<int> parent(n + 1, -1), depth(n + 1, 0), color(n + 1, 0);
    vector<int> V;
    V.reserve(n);
    V.push_back(1);
    parent[1] = 0;
    depth[1] = 0;
    color[1] = 0;

    vector<int> U;
    U.reserve(n - 1);
    for (int i = 2; i <= n; i++) U.push_back(i);

    long long eV = 0; // edges inside V

    while (!U.empty()) {
        int v = findVertexConnectedToVisited(V, eV, U);

        vector<int> Vv = V;
        Vv.push_back(v);
        long long eVnew = ask(Vv);
        long long degToV = eVnew - eV;

        int p = findNeighborInVisited(v, V, degToV);

        parent[v] = p;
        depth[v] = depth[p] + 1;
        color[v] = color[p] ^ 1;

        V.push_back(v);
        eV = eVnew;

        auto it = find(U.begin(), U.end(), v);
        if (it != U.end()) {
            *it = U.back();
            U.pop_back();
        } else {
            exit(0);
        }
    }

    vector<int> part0, part1;
    part0.reserve(n);
    part1.reserve(n);
    for (int i = 1; i <= n; i++) {
        if (color[i] == 0) part0.push_back(i);
        else part1.push_back(i);
    }

    long long e0 = ask(part0);
    long long e1 = ask(part1);

    if (e0 == 0 && e1 == 0) {
        cout << "Y " << part0.size() << "\n";
        for (int i = 0; i < (int)part0.size(); i++) {
            if (i) cout << ' ';
            cout << part0[i];
        }
        cout << "\n";
        cout.flush();
        return 0;
    }

    vector<int> badSet = (e0 > 0 ? part0 : part1);
    long long eBad = (e0 > 0 ? e0 : e1);

    auto [a, b] = findAnyEdgeInside(badSet, eBad);
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