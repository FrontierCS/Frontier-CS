#include <bits/stdc++.h>
using namespace std;

static const long long INF_NEG = -1;

long long query_count = 0;

long long ask(const vector<int>& s) {
    if (s.empty()) return 0; // Empty set has zero edges; avoid invalid query.
    cout << "? " << s.size() << "\n";
    for (size_t i = 0; i < s.size(); ++i) {
        if (i) cout << " ";
        cout << s[i];
    }
    cout << "\n";
    cout.flush();
    long long m;
    if (!(cin >> m)) {
        exit(0);
    }
    if (m == -1) exit(0);
    ++query_count;
    return m;
}

pair<vector<int>, vector<int>> split_half(const vector<int>& v) {
    size_t mid = v.size() / 2;
    vector<int> a(v.begin(), v.begin() + mid);
    vector<int> b(v.begin() + mid, v.end());
    if (a.empty()) { // ensure non-empty first part
        a.push_back(b.back());
        b.pop_back();
    }
    return {a, b};
}

vector<int> concat(const vector<int>& a, const vector<int>& b) {
    vector<int> r;
    r.reserve(a.size() + b.size());
    r.insert(r.end(), a.begin(), a.end());
    r.insert(r.end(), b.begin(), b.end());
    return r;
}

int find_vertex_connected_to_set(const vector<int>& C, const vector<int>& R) {
    long long eC = ask(C);
    vector<int> cur = R;
    while (cur.size() > 1) {
        auto [L, Rhalf] = split_half(cur);
        long long eL = ask(L);
        vector<int> CL = concat(C, L);
        long long eCL = ask(CL);
        long long cross = eCL - eC - eL;
        if (cross > 0) cur = L;
        else cur = Rhalf;
    }
    return cur[0];
}

int find_neighbor_in_set(int v, const vector<int>& C) {
    vector<int> cur = C;
    while (cur.size() > 1) {
        auto [L, Rhalf] = split_half(cur);
        long long eL = ask(L);
        vector<int> Lp = L;
        Lp.push_back(v);
        long long eLv = ask(Lp);
        long long cross = eLv - eL; // since ask({v})=0
        if (cross > 0) cur = L;
        else cur = Rhalf;
    }
    return cur[0];
}

int find_endpoint_in_first_with_edges_to_second(vector<int> A, const vector<int>& B) {
    long long eB = ask(B);
    vector<int> cur = A;
    while (cur.size() > 1) {
        auto [L, Rhalf] = split_half(cur);
        long long eL = ask(L);
        vector<int> LB = concat(L, B);
        long long eLB = ask(LB);
        long long cross = eLB - eL - eB;
        if (cross > 0) cur = L;
        else cur = Rhalf;
    }
    return cur[0];
}

int find_neighbor_in_B_of_a(int a, vector<int> B) {
    vector<int> cur = B;
    while (cur.size() > 1) {
        auto [L, Rhalf] = split_half(cur);
        long long eL = ask(L);
        vector<int> LwithA = L;
        LwithA.push_back(a);
        long long eLa = ask(LwithA);
        long long cross = eLa - eL;
        if (cross > 0) cur = L;
        else cur = Rhalf;
    }
    return cur[0];
}

pair<int,int> find_internal_edge_in_set(vector<int> S, long long eS) {
    if (S.size() == 2) return {S[0], S[1]};
    auto [A, B] = split_half(S);
    long long eA = ask(A);
    if (eA > 0) return find_internal_edge_in_set(A, eA);
    long long eB = ask(B);
    if (eB > 0) return find_internal_edge_in_set(B, eB);
    // edges are crossing between A and B
    int a = find_endpoint_in_first_with_edges_to_second(A, B);
    int b = find_neighbor_in_B_of_a(a, B);
    return {a, b};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<int>> tree(n + 1);
    vector<int> parent(n + 1, 0);

    vector<int> C;
    vector<int> R;
    for (int i = 1; i <= n; ++i) R.push_back(i);

    // Start with the first vertex
    int root = R[0];
    C.push_back(root);
    R.erase(R.begin());

    while (!R.empty()) {
        int v = find_vertex_connected_to_set(C, R);
        // remove v from R
        auto it = find(R.begin(), R.end(), v);
        if (it != R.end()) R.erase(it);

        int u = find_neighbor_in_set(v, C);

        tree[u].push_back(v);
        tree[v].push_back(u);
        parent[v] = u;
        C.push_back(v);
    }

    // BFS to assign colors and parents
    vector<int> color(n + 1, -1);
    queue<int> q;
    color[root] = 0;
    parent[root] = 0;
    q.push(root);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int w : tree[u]) {
            if (color[w] == -1) {
                color[w] = color[u] ^ 1;
                parent[w] = u;
                q.push(w);
            }
        }
    }

    vector<int> part0, part1;
    for (int i = 1; i <= n; ++i) {
        if (color[i] == 0) part0.push_back(i);
        else part1.push_back(i);
    }

    long long e0 = part0.empty() ? 0 : ask(part0);
    long long e1 = part1.empty() ? 0 : ask(part1);

    if (e0 == 0 && e1 == 0) {
        cout << "Y " << part0.size() << "\n";
        for (size_t i = 0; i < part0.size(); ++i) {
            if (i) cout << " ";
            cout << part0[i];
        }
        cout << "\n";
        cout.flush();
        return 0;
    } else {
        vector<int> S = (e0 > 0 ? part0 : part1);
        long long eS = (e0 > 0 ? e0 : e1);
        auto edge = find_internal_edge_in_set(S, eS);
        int a = edge.first, b = edge.second;

        // Build path between a and b in the tree
        vector<int> pa, pb;
        int x = a;
        while (x) {
            pa.push_back(x);
            x = parent[x];
        }
        int y = b;
        while (y) {
            pb.push_back(y);
            y = parent[y];
        }
        unordered_map<int,int> pos;
        for (int i = 0; i < (int)pa.size(); ++i) pos[pa[i]] = i;
        int idxB = 0;
        while (idxB < (int)pb.size() && !pos.count(pb[idxB])) ++idxB;
        int lca = pb[idxB];
        int idxA = pos[lca];

        vector<int> cycle;
        for (int i = 0; i <= idxA; ++i) cycle.push_back(pa[i]);
        for (int i = idxB - 1; i >= 0; --i) cycle.push_back(pb[i]);

        cout << "N " << cycle.size() << "\n";
        for (size_t i = 0; i < cycle.size(); ++i) {
            if (i) cout << " ";
            cout << cycle[i];
        }
        cout << "\n";
        cout.flush();
    }

    return 0;
}