#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

ll query(int u, int v) {
    cout << "? " << u << " " << v << endl;
    ll d;
    cin >> d;
    return d;
}

void solve() {
    int n;
    cin >> n;
    if (n == 1) {
        cout << "!" << endl;
        return;
    }
    if (n == 2) {
        ll d = query(1, 2);
        cout << "! 1 2 " << d << endl;
        return;
    }

    vector<ll> dist1(n+1), distA(n+1), distB(n+1);
    for (int i = 2; i <= n; ++i) {
        dist1[i] = query(1, i);
    }
    dist1[1] = 0;
    int A = 2;
    for (int i = 3; i <= n; ++i) {
        if (dist1[i] > dist1[A]) A = i;
    }
    for (int i = 1; i <= n; ++i) {
        if (i == A) continue;
        distA[i] = query(A, i);
    }
    distA[A] = 0;
    int B = 1;
    if (B == A) B = 2;
    for (int i = 1; i <= n; ++i) {
        if (i == A) continue;
        if (distA[i] > distA[B]) B = i;
    }
    for (int i = 1; i <= n; ++i) {
        if (i == B) continue;
        distB[i] = query(B, i);
    }
    distB[B] = 0;

    ll L = distA[B];
    vector<ll> x(n+1), h(n+1);
    unordered_map<ll, int> x_to_diam;
    vector<pair<ll, int>> diam;
    for (int i = 1; i <= n; ++i) {
        x[i] = (distA[i] + L - distB[i]) / 2;
        h[i] = distA[i] - x[i];
        if (h[i] == 0) {
            diam.push_back({x[i], i});
            x_to_diam[x[i]] = i;
        }
    }
    sort(diam.begin(), diam.end());

    unordered_map<int, vector<pair<ll, int>>> groups;
    for (int i = 1; i <= n; ++i) {
        if (h[i] > 0) {
            int p = x_to_diam[x[i]];
            groups[p].push_back({h[i], i});
        }
    }

    vector<tuple<int, int, ll>> edges;
    for (size_t i = 0; i + 1 < diam.size(); ++i) {
        int u = diam[i].second;
        int v = diam[i+1].second;
        ll w = diam[i+1].first - diam[i].first;
        edges.emplace_back(u, v, w);
    }

    for (auto& kv : groups) {
        int p = kv.first;
        auto& vec = kv.second;
        sort(vec.begin(), vec.end());
        vector<pair<ll, int>> nodes = {{0, p}};
        for (auto& hi : vec) {
            ll h_i = hi.first;
            int i = hi.second;
            int left = 0, right = (int)nodes.size() - 1;
            while (left < right) {
                int mid = (left + right + 1) / 2;
                int j = nodes[mid].second;
                ll h_j = nodes[mid].first;
                ll dij = query(i, j);
                ll dlca = (h_i + h_j - dij) / 2;
                if (dlca == h_j) {
                    left = mid;
                } else {
                    right = mid - 1;
                }
            }
            int parent = nodes[left].second;
            ll w = h_i - nodes[left].first;
            edges.emplace_back(i, parent, w);
            auto it = lower_bound(nodes.begin(), nodes.end(), make_pair(h_i, i));
            nodes.insert(it, {h_i, i});
        }
    }

    cout << "!";
    for (auto& e : edges) {
        int u, v; ll w;
        tie(u, v, w) = e;
        cout << " " << u << " " << v << " " << w;
    }
    cout << endl;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    while (T--) {
        solve();
    }
    return 0;
}