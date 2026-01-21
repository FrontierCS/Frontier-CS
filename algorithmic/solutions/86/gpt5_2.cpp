#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    vector<long long> rest;
    long long x;
    while (cin >> x) rest.push_back(x);

    vector<pair<int,int>> edges;

    if ((int)rest.size() >= 2*(n-1)) {
        // Interpret as edge list
        for (int i = 0; i < n-1; ++i) {
            int u = (int)rest[2*i];
            int v = (int)rest[2*i+1];
            if (u < 1 || u > n || v < 1 || v > n) {
                // Fallback to chain if invalid
                edges.clear();
                break;
            }
            edges.emplace_back(u, v);
        }
        if ((int)edges.size() != n-1) {
            edges.clear();
        }
    }

    if (edges.empty() && (int)rest.size() == n-1) {
        // Interpret as parent list for nodes 2..n
        for (int i = 2; i <= n; ++i) {
            int p = (int)rest[i-2];
            if (p < 1 || p > n) { edges.clear(); break; }
            edges.emplace_back(i, p);
        }
        if ((int)edges.size() != n-1) {
            edges.clear();
        }
    }

    if (edges.empty()) {
        // Fallback: chain 1-2-3-...-n
        for (int i = 1; i < n; ++i) edges.emplace_back(i, i+1);
    }

    cout << 1;
    for (auto &e : edges) cout << ' ' << e.first << ' ' << e.second;
    cout << '\n';
    cout.flush();

    return 0;
}