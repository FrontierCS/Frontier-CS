#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<unsigned char>> on(n + 1, vector<unsigned char>(n + 1, 0));
    vector<int> depth(n + 1, 0);

    if (n >= 1) {
        on[1][1] = 1;
        depth[1] = 0;
    }

    for (int x = 2; x <= n; ++x) {
        int cnt = 0;
        for (int v = 1; v <= n; ++v) {
            cout << "? 2 " << v << " 1 " << x << "\n" << flush;
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            on[x][v] = (ans == 1);
            if (ans == 1) ++cnt;
        }
        depth[x] = cnt - 1;
    }

    vector<pair<int,int>> edges;
    edges.reserve(n - 1);

    for (int x = 2; x <= n; ++x) {
        int want = depth[x] - 1;
        int parent = -1;
        for (int v = 1; v <= n; ++v) {
            if (on[x][v] && depth[v] == want) {
                parent = v;
                break;
            }
        }
        if (parent == -1) parent = 1; // Fallback (should not happen in valid interaction)
        edges.emplace_back(x, parent);
    }

    cout << "!\n";
    for (auto &e : edges) {
        cout << e.first << " " << e.second << "\n";
    }
    cout.flush();

    return 0;
}