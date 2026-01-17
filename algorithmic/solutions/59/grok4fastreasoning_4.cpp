#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<vector<int>> g(n + 1);
    vector<int> indeg(n + 1, 0);
    auto ask = [&](int x, int y) -> char {
        cout << "? " << x << " " << y << endl;
        fflush(stdout);
        char c;
        cin >> c;
        return c;
    };
    for (int i = 1; i < n; ++i) {
        char c = ask(i, i + 1);
        if (c == '<') {
            g[i].push_back(i + 1);
            indeg[i + 1]++;
        } else {
            g[i + 1].push_back(i);
            indeg[i]++;
        }
    }
    for (int i = 1; i <= n - 2; ++i) {
        if (i % 3 != 0) {
            char c = ask(i, i + 2);
            if (c == '<') {
                g[i].push_back(i + 2);
                indeg[i + 2]++;
            } else {
                g[i + 2].push_back(i);
                indeg[i]++;
            }
        }
    }
    queue<int> q;
    for (int i = 1; i <= n; ++i) {
        if (indeg[i] == 0) {
            q.push(i);
        }
    }
    vector<int> ans(n + 1);
    int cnt = 1;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        ans[u] = cnt++;
        for (int v : g[u]) {
            indeg[v]--;
            if (indeg[v] == 0) {
                q.push(v);
            }
        }
    }
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;
    fflush(stdout);
    return 0;
}