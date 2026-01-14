#include <bits/stdc++.h>
using namespace std;

static const int QUERY_LIMIT = 50000;

int n;
int qcnt = 0;

long long ask_raw(const vector<int>& s) {
    if ((int)s.size() < 1 || (int)s.size() > n) {
        exit(0);
    }
    if (++qcnt > QUERY_LIMIT) {
        cout << "?\n" << flush;
        exit(0);
    }
    cout << "? " << (int)s.size() << "\n";
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

long long induced_edges(const vector<int>& s) {
    if ((int)s.size() < 2) return 0;
    return ask_raw(s);
}

vector<int> merge_disjoint_sorted(const vector<int>& a, const vector<int>& b) {
    vector<int> res;
    res.reserve(a.size() + b.size());
    size_t i = 0, j = 0;
    while (i < a.size() && j < b.size()) {
        if (a[i] < b[j]) res.push_back(a[i++]);
        else res.push_back(b[j++]);
    }
    while (i < a.size()) res.push_back(a[i++]);
    while (j < b.size()) res.push_back(b[j++]);
    return res;
}

// Finds one vertex in candidates that has at least one edge to fixed.
// Precondition: fixed and candidates are disjoint, and there exists at least one edge between them.
int find_vertex_connected(const vector<int>& fixed, long long fFixed, const vector<int>& candidates) {
    if (candidates.size() == 1) return candidates[0];

    int mid = (int)candidates.size() / 2;
    vector<int> left(candidates.begin(), candidates.begin() + mid);
    vector<int> right(candidates.begin() + mid, candidates.end());

    long long fLeft = induced_edges(left);
    vector<int> uni = merge_disjoint_sorted(fixed, left);
    long long fUni = induced_edges(uni);
    long long cross = fUni - fFixed - fLeft;

    if (cross > 0) return find_vertex_connected(fixed, fFixed, left);
    return find_vertex_connected(fixed, fFixed, right);
}

pair<int,int> find_edge_within_set(const vector<int>& S, long long fS) {
    if (S.size() == 2) return {S[0], S[1]};

    int mid = (int)S.size() / 2;
    vector<int> A(S.begin(), S.begin() + mid);
    vector<int> B(S.begin() + mid, S.end());

    long long fA = induced_edges(A);
    if (fA > 0) return find_edge_within_set(A, fA);

    long long fB = induced_edges(B);
    if (fB > 0) return find_edge_within_set(B, fB);

    // Then there must be at least one edge between A and B (since fS > 0).
    // Find endpoint a in A connected to B, then b in B connected to {a}.
    int a = find_vertex_connected(B, fB, A);
    vector<int> fixed = {a};
    int b = find_vertex_connected(fixed, 0, B);
    return {a, b};
}

vector<int> tree_path(int u, int v, const vector<int>& parent, const vector<int>& depth) {
    vector<int> a, b;
    int uu = u, vv = v;
    while (depth[uu] > depth[vv]) {
        a.push_back(uu);
        uu = parent[uu];
    }
    while (depth[vv] > depth[uu]) {
        b.push_back(vv);
        vv = parent[vv];
    }
    while (uu != vv) {
        a.push_back(uu);
        b.push_back(vv);
        uu = parent[uu];
        vv = parent[vv];
    }
    a.push_back(uu); // LCA
    reverse(b.begin(), b.end());
    a.insert(a.end(), b.begin(), b.end());
    return a;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    vector<int> parent(n + 1, 0), depth(n + 1, 0);

    vector<int> visited = {1};
    vector<int> unvisited;
    unvisited.reserve(max(0, n - 1));
    for (int i = 2; i <= n; i++) unvisited.push_back(i);

    long long fVisited = 0; // induced_edges({1}) = 0

    while (!unvisited.empty()) {
        // Find x in unvisited connected to visited.
        int x = find_vertex_connected(visited, fVisited, unvisited);

        // Find y in visited connected to x.
        vector<int> fixed = {x};
        int y = find_vertex_connected(fixed, 0, visited);

        parent[x] = y;
        depth[x] = depth[y] + 1;

        // Move x from unvisited to visited (keep sorted).
        auto itU = lower_bound(unvisited.begin(), unvisited.end(), x);
        if (itU == unvisited.end() || *itU != x) exit(0);
        unvisited.erase(itU);
        visited.insert(lower_bound(visited.begin(), visited.end(), x), x);

        // Update fVisited for next step.
        fVisited = induced_edges(visited);
    }

    vector<int> c0, c1;
    c0.reserve(n); c1.reserve(n);
    for (int i = 1; i <= n; i++) {
        if (depth[i] % 2 == 0) c0.push_back(i);
        else c1.push_back(i);
    }

    long long f0 = induced_edges(c0);
    long long f1 = induced_edges(c1);

    if (f0 == 0 && f1 == 0) {
        cout << "Y " << (int)c0.size() << "\n";
        for (int i = 0; i < (int)c0.size(); i++) {
            if (i) cout << ' ';
            cout << c0[i];
        }
        cout << "\n";
        cout.flush();
        return 0;
    }

    vector<int> S;
    long long fS;
    if (f0 > 0) {
        S = c0;
        fS = f0;
    } else {
        S = c1;
        fS = f1;
    }

    auto [u, v] = find_edge_within_set(S, fS);
    vector<int> cycle = tree_path(u, v, parent, depth);

    cout << "N " << (int)cycle.size() << "\n";
    for (int i = 0; i < (int)cycle.size(); i++) {
        if (i) cout << ' ';
        cout << cycle[i];
    }
    cout << "\n";
    cout.flush();
    return 0;
}