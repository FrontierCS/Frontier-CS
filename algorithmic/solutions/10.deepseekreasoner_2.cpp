#include <bits/stdc++.h>
using namespace std;
using ll = long long;

void solve() {
    int n;
    cin >> n;
    vector<ll> d1(n+1, 0), da(n+1, 0);
    // query distances from vertex 1
    for (int i = 2; i <= n; ++i) {
        cout << "? 1 " << i << endl;
        cout.flush();
        cin >> d1[i];
    }
    d1[1] = 0;
    // find farthest from 1
    int a = 1;
    for (int i = 2; i <= n; ++i) {
        if (d1[i] > d1[a]) a = i;
    }
    // query distances from a
    for (int i = 1; i <= n; ++i) {
        if (i != a) {
            cout << "? " << a << " " << i << endl;
            cout.flush();
            cin >> da[i];
        }
    }
    da[a] = 0;
    ll D = d1[a];
    // compute x and h
    vector<ll> x(n+1), h(n+1);
    for (int i = 1; i <= n; ++i) {
        x[i] = (d1[i] - da[i] + D) / 2;
        h[i] = (d1[i] + da[i] - D) / 2; // also = d1[i] - x[i]
    }
    // group vertices by x
    map<ll, vector<int>> group;
    for (int i = 1; i <= n; ++i) {
        group[x[i]].push_back(i);
    }
    // path vertices: h == 0
    vector<int> path;
    for (int i = 1; i <= n; ++i) {
        if (h[i] == 0) path.push_back(i);
    }
    sort(path.begin(), path.end(), [&](int u, int v) { return x[u] < x[v]; });
    vector<tuple<int,int,ll>> edges;
    // edges on the path
    for (size_t i = 0; i+1 < path.size(); ++i) {