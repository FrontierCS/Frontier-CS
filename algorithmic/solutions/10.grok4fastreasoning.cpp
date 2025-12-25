#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        int n;
        cin >> n;
        vector<ll> D(n + 1, 0);
        vector<tuple<int, int, ll>> edges;
        queue<pair<int, vector<int>>> q;
        vector<int> initial;
        if (n >= 2) {
            for (int j = 2; j <= n; j++) {
                cout << "? 1 " << j << "\n";
                cout.flush();
                cin >> D[j];
            }
            for (int j = 2; j <= n; j++) initial.push_back(j);
            q.push({1, initial});
        }
        while (!q.empty()) {
            auto front = q.front();
            q.pop();
            int rt = front.first;
            vector<int> dsc = front.second;
            if (dsc.empty()) continue;
            vector<int> current_active = dsc;
            while (!current_active.empty()) {
                int pivot = current_active[0];
                vector<int> temp_remaining;
                vector<int> same_group{pivot};
                for (size_t j = 1; j < current_active.size(); j++) {
                    int u = current_active[j];
                    cout << "? " << pivot << " " << u << "\n";
                    cout.flush();
                    ll dd;
                    cin >> dd;
                    ll expected = D[pivot] + D[u] - 2LL * D[rt];
                    if (dd < expected) {
                        same_group.push_back(u);
                    } else {
                        temp_remaining.push_back(u);
                    }
                }
                current_active = temp_remaining;
                int c = same_group[0];
                ll minn = D[c];
                for (int nd : same_group) {
                    if (D[nd] < minn) {
                        minn = D[nd];
                        c = nd;
                    }
                }
                ll w = D[c] - D[rt];
                edges.emplace_back(rt, c, w);
                vector<int> sub_dsc;
                for (int nd : same_group) {
                    if (nd != c) sub_dsc.push_back(nd);
                }
                if (!sub_dsc.empty()) {
                    q.push({c, sub_dsc});
                }
            }
        }
        cout << "!";
        for (auto& e : edges) {
            int u, v;
            ll w;
            tie(u, v, w) = e;
            cout << " " << u << " " << v << " " << w;
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}