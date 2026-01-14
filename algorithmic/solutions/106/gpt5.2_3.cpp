#include <bits/stdc++.h>
using namespace std;

static int n;
static int qcount = 0;
static vector<int> seen;
static int stampv = 1;

static void die() { exit(0); }

static vector<int> mergeSets(const vector<int>& a, const vector<int>& b) {
    ++stampv;
    vector<int> res;
    res.reserve(a.size() + b.size());
    for (int x : a) {
        seen[x] = stampv;
        res.push_back(x);
    }
    for (int x : b) {
        if (seen[x] != stampv) {
            seen[x] = stampv;
            res.push_back(x);
        }
    }
    return res;
}

static vector<int> addVertex(const vector<int>& a, int x) {
    ++stampv;
    vector<int> res;
    res.reserve(a.size() + 1);
    for (int y : a) {
        seen[y] = stampv;
        res.push_back(y);
    }
    if (seen[x] != stampv) {
        seen[x] = stampv;
        res.push_back(x);
    }
    return res;
}

static long long ask(const vector<int>& v) {
    if (v.size() <= 1) return 0;
    ++qcount;
    if (qcount > 50000) die();
    cout << "? " << v.size() << "\n";
    for (size_t i = 0; i < v.size(); i++) {
        if (i) cout << ' ';
        cout << v[i];
    }
    cout << "\n";
    cout.flush();

    long long m;
    if (!(cin >> m)) die();
    if (m == -1) die();
    return m;
}

static long long crossEdges(const vector<int>& C, long long eC, const vector<int>& T) {
    if (T.empty()) return 0;
    long long eT = ask(T);
    vector<int> u = mergeSets(C, T);
    long long eU = ask(u);
    return eU - eC - eT;
}

static long long edgesBetweenVertexAndSet(int v, const vector<int>& S) {
    if (S.empty()) return 0;
    long long eS = ask(S);
    vector<int> u = addVertex(S, v);
    long long eU = ask(u);
    return eU - eS;
}

static int findConnectingVertex(const vector<int>& C, long long eC, const vector<int>& U) {
    vector<int> cur = U;
    while (cur.size() > 1) {
        int mid = (int)cur.size() / 2;
        vector<int> left(cur.begin(), cur.begin() + mid);
        long long cr = crossEdges(C, eC, left);
        if (cr > 0) {
            cur.swap(left);
        } else {
            vector<int> right(cur.begin() + mid, cur.end());
            cur.swap(right);
        }
    }
    return cur[0];
}

static int findNeighborInComponent(int v, const vector<int>& C) {
    vector<int> cur = C;
    while (cur.size() > 1) {
        int mid = (int)cur.size() / 2;
        vector<int> left(cur.begin(), cur.begin() + mid);
        long long deg = edgesBetweenVertexAndSet(v, left);
        if (deg > 0) {
            cur.swap(left);
        } else {
            vector<int> right(cur.begin() + mid, cur.end());
            cur.swap(right);
        }
    }
    return cur[0];
}

static pair<int,int> findCrossEdge(const vector<int>& A, long long /*eA*/, const vector<int>& B, long long eB) {
    vector<int> curA = A;
    while (curA.size() > 1) {
        int mid = (int)curA.size() / 2;
        vector<int> left(curA.begin(), curA.begin() + mid);

        long long eLeft = ask(left);
        vector<int> unionLB = mergeSets(left, B);
        long long eUnion = ask(unionLB);
        long long crossL = eUnion - eLeft - eB;

        if (crossL > 0) {
            curA.swap(left);
        } else {
            vector<int> right(curA.begin() + mid, curA.end());
            curA.swap(right);
        }
    }
    int u = curA[0];

    vector<int> curB = B;
    while (curB.size() > 1) {
        int mid = (int)curB.size() / 2;
        vector<int> left(curB.begin(), curB.begin() + mid);

        long long eLeft = ask(left);
        vector<int> unionLU = addVertex(left, u);
        long long eUnion = ask(unionLU);
        long long deg = eUnion - eLeft;

        if (deg > 0) {
            curB.swap(left);
        } else {
            vector<int> right(curB.begin() + mid, curB.end());
            curB.swap(right);
        }
    }
    return {u, curB[0]};
}

static pair<int,int> findEdgeRec(const vector<int>& S, long long eS) {
    (void)eS;
    if (S.size() == 2) return {S[0], S[1]};
    int mid = (int)S.size() / 2;
    vector<int> A(S.begin(), S.begin() + mid);
    vector<int> B(S.begin() + mid, S.end());

    long long eA = ask(A);
    if (eA > 0) return findEdgeRec(A, eA);

    long long eB = ask(B);
    if (eB > 0) return findEdgeRec(B, eB);

    return findCrossEdge(A, eA, B, eB);
}

static pair<int,int> findAnyEdge(const vector<int>& S) {
    long long eS = ask(S);
    return findEdgeRec(S, eS);
}

static vector<int> getPath(int x, int y, const vector<int>& parent, const vector<int>& depth) {
    int u = x, v = y;
    vector<int> a, b;
    while (depth[u] > depth[v]) {
        a.push_back(u);
        u = parent[u];
    }
    while (depth[v] > depth[u]) {
        b.push_back(v);
        v = parent[v];
    }
    while (u != v) {
        a.push_back(u);
        u = parent[u];
        b.push_back(v);
        v = parent[v];
    }
    a.push_back(u);
    reverse(b.begin(), b.end());
    a.insert(a.end(), b.begin(), b.end());
    return a;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    seen.assign(n + 1, 0);

    vector<int> parent(n + 1, 0), depth(n + 1, 0);

    vector<int> component;
    component.reserve(n);
    component.push_back(1);
    long long eC = 0;

    vector<int> remaining;
    remaining.reserve(max(0, n - 1));
    for (int i = 2; i <= n; i++) remaining.push_back(i);

    while (!remaining.empty()) {
        int v = findConnectingVertex(component, eC, remaining);
        int u = findNeighborInComponent(v, component);

        parent[v] = u;
        depth[v] = depth[u] + 1;

        component.push_back(v);
        auto it = find(remaining.begin(), remaining.end(), v);
        if (it != remaining.end()) remaining.erase(it);

        eC = ask(component);
    }

    vector<int> part0, part1;
    part0.reserve(n);
    part1.reserve(n);
    for (int i = 1; i <= n; i++) {
        if (depth[i] & 1) part1.push_back(i);
        else part0.push_back(i);
    }

    long long e0 = ask(part0);
    long long e1 = ask(part1);

    if (e0 == 0 && e1 == 0) {
        cout << "Y " << part0.size() << "\n";
        for (size_t i = 0; i < part0.size(); i++) {
            if (i) cout << ' ';
            cout << part0[i];
        }
        cout << "\n";
        cout.flush();
        return 0;
    }

    const vector<int>& badSet = (e0 > 0 ? part0 : part1);
    auto [x, y] = findAnyEdge(badSet);

    vector<int> cycle = getPath(x, y, parent, depth);
    cout << "N " << cycle.size() << "\n";
    for (size_t i = 0; i < cycle.size(); i++) {
        if (i) cout << ' ';
        cout << cycle[i];
    }
    cout << "\n";
    cout.flush();
    return 0;
}