#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int B = 0;
    while ((1 << B) < n) B++;

    vector<vector<int>> bitSets(B);
    for (int b = 0; b < B; ++b) {
        for (int j = 1; j <= n; ++j) {
            if ((j >> b) & 1) bitSets[b].push_back(j);
        }
    }

    auto ask = [&](int u, long long k, const vector<int>& S) -> int {
        cout << "? " << u << " " << k << " " << (int)S.size();
        for (int x : S) cout << " " << x;
        cout << endl;
        cout.flush();
        int resp;
        if (!(cin >> resp)) exit(0);
        return resp;
    };

    vector<int> a(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        int val = 0;
        for (int b = 0; b < B; ++b) {
            int r = ask(i, 1, bitSets[b]);
            if (r == 1) val |= (1 << b);
        }
        a[i] = val;
    }

    vector<vector<int>> radj(n + 1);
    for (int i = 1; i <= n; ++i) {
        if (a[i] >= 1 && a[i] <= n)
            radj[a[i]].push_back(i);
    }

    vector<int> pos(n + 1, -1), order;
    int cur = 1;
    while (pos[cur] == -1) {
        pos[cur] = (int)order.size();
        order.push_back(cur);
        cur = a[cur];
    }
    int start = pos[cur];
    vector<int> cycle;
    for (int i = start; i < (int)order.size(); ++i) cycle.push_back(order[i]);

    vector<char> good(n + 1, false);
    queue<int> q;
    for (int v : cycle) {
        if (!good[v]) {
            good[v] = true;
            q.push(v);
        }
    }
    while (!q.empty()) {
        int x = q.front(); q.pop();
        for (int y : radj[x]) {
            if (!good[y]) {
                good[y] = true;
                q.push(y);
            }
        }
    }

    vector<int> ans;
    for (int i = 1; i <= n; ++i) if (good[i]) ans.push_back(i);

    cout << "! " << ans.size();
    for (int x : ans) cout << " " << x;
    cout << endl;
    cout.flush();

    return 0;
}