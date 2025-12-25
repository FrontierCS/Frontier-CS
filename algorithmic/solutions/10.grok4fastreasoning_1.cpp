#include <bits/stdc++.h>
using namespace std;

void build(int root, vector<int> S, const vector<long long>& dist, vector<tuple<int, int, long long>>& edges, int n) {
    if (S.empty()) return;
    sort(S.begin(), S.end(), [&](int x, int y) {
        return dist[x] < dist[y];
    });
    vector<int> direct_children;
    vector<vector<int>> subs;
    for (int v : S) {
        bool found = false;
        for (size_t j = 0; j < direct_children.size(); ++j) {
            int c = direct_children[j];
            cout << "? " << c << " " << v << endl;
            cout.flush();
            long long dd;
            cin >> dd;
            long long expected = dist[v] - dist[c];
            if (dd == expected) {
                subs[j].push_back(v);
                found = true;
                break;
            }
        }
        if (!found) {
            direct_children.push_back(v);
            subs.emplace_back();
            long long w = dist[v] - dist[root];
            edges.emplace_back(root, v, w);
        }
    }
    for (size_t j = 0; j < direct_children.size(); ++j) {
        int c = direct_children[j];
        vector<int> sub = subs[j];
        if (!sub.empty()) {
            build(c, sub, dist, edges, n);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int n;
        cin >> n;
        if (n == 1) {
            cout << "!" << endl;
            cout.flush();
            continue;
        }
        vector<long long> dist(n + 1, 0LL);
        for (int j = 2; j <= n; ++j) {
            cout << "? 1 " << j << endl;
            cout.flush();
            cin >> dist[j];
        }
        vector<int> all_nodes(n - 1);
        iota(all_nodes.begin(), all_nodes.end(), 2);
        sort(all_nodes.begin(), all_nodes.end(), [&](int x, int y) {
            return dist[x] < dist[y];
        });
        vector<tuple<int, int, long long>> edges;
        build(1, all_nodes, dist, edges, n);
        cout << "!";
        for (auto [u, v, w] : edges) {
            cout << " " << u << " " << v << " " << w;
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}