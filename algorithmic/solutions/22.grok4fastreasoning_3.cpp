#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> adj;
vector<vector<int>> sets;
vector<int> central;
vector<pair<int, int>> decomp_edges;
int cur_id;

void build(int u, int par, int incoming_bag) {
    int c = central[u];
    if (incoming_bag != 0) {
        decomp_edges.push_back({c, incoming_bag});
    }
    for (int v : adj[u]) {
        if (v == par) continue;
        int b = cur_id++;
        sets[b] = {u, v};
        decomp_edges.push_back({c, b});
        build(v, u, b);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    cin >> N;
    adj.resize(N + 1);
    for (int i = 2; i <= N; i++) {
        int p;
        cin >> p;
        adj[p].push_back(i);
        adj[i].push_back(p);
    }
    vector<int> leaves;
    for (int i = 1; i <= N; i++) {
        if (adj[i].size() == 1) {
            leaves.push_back(i);
        }
    }
    sort(leaves.begin(), leaves.end());
    int k = leaves.size();
    sets.resize(4 * N + 10);
    central.resize(N + 1);
    cur_id = 1;
    for (int j = 1; j <= N; j++) {
        central[j] = cur_id++;
        sets[central[j]] = {j};
    }
    build(1, -1, 0);
    if (k >= 2) {
        int v1 = leaves[0];
        int attach = central[v1];
        vector<int> d(k - 1);
        for (int i = 0; i < k - 1; i++) {
            int va = leaves[i], vb = leaves[i + 1];
            d[i] = cur_id++;
            sets[d[i]] = {va, vb};
        }
        int f = cur_id++;
        int va = leaves[0], vb = leaves[k - 1];
        sets[f] = {va, vb};
        for (int i = 0; i < k - 2; i++) {
            decomp_edges.push_back({d[i], d[i + 1]});
        }
        decomp_edges.push_back({f, d[0]});
        decomp_edges.push_back({d[0], attach});
    }
    int K = cur_id - 1;
    cout << K << '\n';
    for (int i = 1; i <= K; i++) {
        cout << sets[i].size();
        for (int x : sets[i]) {
            cout << " " << x;
        }
        cout << '\n';
    }
    for (auto& e : decomp_edges) {
        cout << e.first << " " << e.second << '\n';
    }
    return 0;
}