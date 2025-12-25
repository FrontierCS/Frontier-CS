#include <bits/stdc++.h>
using namespace std;

int n;
vector<pair<int, int>> edges;
int query_count = 0;

int query(int a, int b, int c) {
    cout << "0 " << a << ' ' << b << ' ' << c << endl;
    cout.flush();
    int res;
    cin >> res;
    query_count++;
    return res;
}

void brute_force(vector<int> S, int root) {
    if (S.size() <= 1) return;
    if (S.size() == 2) {
        edges.emplace_back(S[0], S[1]);
        return;
    }
    map<int, int> idx;
    int m = S.size();
    for (int i = 0; i < m; ++i) idx[S[i]] = i;
    vector<vector<int>> lca(m, vector<int>(m));
    for (int i = 0; i < m; ++i) {
        for (int j = i + 1; j < m; ++j) {
            int x = S[i], y = S[j];
            int res = query(root, x, y);
            lca[i][j] = lca[j][i] = idx[res];
        }
    }
    vector<vector<int>> ancestors(m);
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < m; ++j) {
            if (lca[i][j] == i)
                ancestors[j].push_back(i);
        }
    }
    vector<int> depth(m);
    for (int i = 0; i < m; ++i)
        depth[i] = ancestors[i].size() - 1;
    int root_idx = idx[root];
    for (int i = 0; i < m; ++i) {
        if (i == root_idx) continue;
        int x = S[i];
        int parent = -1;
        for (int a_idx : ancestors[i]) {
            if (a_idx != i && depth[a_idx] == depth[i] - 1) {
                parent = S[a_idx];
                break;
            }
        }
        if (parent != -1)
            edges.emplace_back(parent, x);
    }
}

void solve(vector<int> S, int root) {
    if (S.size() <= 10) {
        brute_force(S, root);
        return;
    }
    if (S.size() == 2) {
        edges.emplace_back(S[0], S[1]);
        return;
    }
    int a, b;
    vector<int> candidates;
    for (int x : S)
        if (x != root) candidates.push_back(x);
    if (candidates.size() >= 2) {
        a = *min_element(candidates.begin(), candidates.end());
        b = *max_element(candidates.begin(), candidates.end());
    } else {
        a = root;
        b = candidates[0];
    }
    map<int, int> proj;
    vector<int> spine = {a, b};
    for (int x : S) {
        if (x == a || x == b) continue;
        int p = query(a, b, x);
        proj[x] = p;
        spine.push_back(p);
    }
    sort(spine.begin(), spine.end());
    spine.erase(unique(spine.begin(), spine.end()), spine.end());
    vector<int> spine_sorted = {a};
    vector<int> rest;
    for (int x : spine)
        if (x != a) rest.push_back(x);
    sort(rest.begin(), rest.end(), [&](int u, int v) {
        int res = query(a, u, v);
        return res == u;
    });
    spine_sorted.insert(spine_sorted.end(), rest.begin(), rest.end());
    for (size_t i = 0; i + 1 < spine_sorted.size(); ++i)
        edges.emplace_back(spine_sorted[i], spine_sorted[i + 1]);
    map<int, vector<int>> clusters;
    for (int x : S) {
        if (x == a || x == b) continue;
        int p = proj[x];
        clusters[p].push_back(x);
    }
    for (int p : spine_sorted) {
        vector<int> cluster = clusters[p];
        cluster.push_back(p);
        if (cluster.size() > 1)
            solve(cluster, p);
    }
}

int main() {
    cin >> n;
    vector<int> all_nodes(n);
    iota(all_nodes.begin(), all_nodes.end(), 1);
    solve(all_nodes, 1);
    cout << "1";
    for (auto [u, v] : edges)
        cout << ' ' << u << ' ' << v;
    cout << endl;
    cout.flush();
    return 0;
}