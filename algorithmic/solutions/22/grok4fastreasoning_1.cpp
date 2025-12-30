#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    cin >> N;
    vector<int> par(N + 1);
    vector<vector<int>> adj(N + 1);
    for (int j = 1; j <= N - 1; ++j) {
        int p;
        cin >> p;
        par[j + 1] = p;
        adj[p].push_back(j + 1);
        adj[j + 1].push_back(p);
    }
    
    vector<int> deg(N + 1);
    for (int i = 1; i <= N; ++i) {
        deg[i] = adj[i].size();
    }
    
    vector<int> leaves;
    for (int i = 2; i <= N; ++i) {
        if (deg[i] == 1) {
            leaves.push_back(i);
        }
    }
    sort(leaves.begin(), leaves.end());
    int kk = leaves.size();
    
    int id = 1;
    vector<int> h_id(N + 1, 0);
    for (int i = 1; i <= N; ++i) {
        if (deg[i] >= 2 || i == 1) {
            h_id[i] = id;
            id++;
        }
    }
    int numh = id - 1;
    
    vector<int> m_id(N + 1, 0);
    for (int i = 2; i <= N; ++i) {
        m_id[i] = id;
        id++;
    }
    int num_main = id - 1;
    
    vector<vector<int>> bag(4 * N + 10);
    // Assign bags for h
    for (int i = 1; i <= N; ++i) {
        if (h_id[i]) {
            bag[h_id[i]] = {i};
        }
    }
    // Assign bags for m
    for (int i = 2; i <= N; ++i) {
        bag[m_id[i]] = {par[i], i};
    }
    
    // Ring R's
    vector<int> ra(kk), rb(kk);
    for (int j = 0; j < kk; ++j) {
        int vi = leaves[j];
        int vi1 = leaves[(j + 1) % kk];
        ra[j] = id;
        bag[id] = {vi, vi1};
        id++;
        rb[j] = id;
        bag[id] = {vi, vi1};
        id++;
    }
    int KK = id - 1;
    
    // Now edges
    vector<pair<int, int>> edges;
    // Main subdivision
    for (int i = 2; i <= N; ++i) {
        int mm = m_id[i];
        int pp = par[i];
        int hp = h_id[pp];
        edges.emplace_back(hp, mm);
        if (h_id[i]) {
            edges.emplace_back(mm, h_id[i]);
        }
    }
    // Ring attachments
    for (int j = 0; j < kk; ++j) {
        int vi = leaves[j];
        int vi1 = leaves[(j + 1) % kk];
        // left to vi
        edges.emplace_back(m_id[vi], ra[j]);
        // right to vi1
        edges.emplace_back(m_id[vi1], rb[j]);
    }
    
    // Output
    cout << KK << '\n';
    for (int i = 1; i <= KK; ++i) {
        cout << bag[i].size();
        for (int x : bag[i]) {
            cout << ' ' << x;
        }
        cout << '\n';
    }
    for (auto [a, b] : edges) {
        if (a > b) swap(a, b);
        cout << a << ' ' << b << '\n';
    }
    
    return 0;
}