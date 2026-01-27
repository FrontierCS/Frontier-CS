#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    if (n <= 0) return 0;

    int r = 1; // choose 1 as root

    vector<vector<unsigned char>> onpath(n + 1, vector<unsigned char>(n + 1, 0));
    vector<int> dist(n + 1, 0);

    auto ask = [&](int v, int a, int b) -> int {
        cout << "? 2 " << v << " " << a << " " << b << endl;
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);
        return ans;
    };

    if (n == 1) {
        cout << "!" << endl;
        cout.flush();
        return 0;
    }

    // For each i != r, query all v != i, r: whether v is on path(i, r).
    for (int i = 1; i <= n; i++) {
        if (i == r) { dist[i] = 0; continue; }
        int cnt = 0;
        for (int v = 1; v <= n; v++) {
            if (v == i || v == r) continue; // skip obvious ones
            int ans = ask(v, i, r);
            onpath[i][v] = (unsigned char)(ans ? 1 : 0);
            if (ans) cnt++;
        }
        // i and r are always on the path
        onpath[i][i] = 1;
        onpath[i][r] = 1;
        dist[i] = (cnt + 2) - 1; // number of vertices on path minus 1 = distance
    }

    vector<pair<int,int>> edges;
    edges.reserve(n - 1);

    for (int i = 1; i <= n; i++) {
        if (i == r) continue;
        int parent = -1;
        for (int j = 1; j <= n; j++) {
            if (j == i) continue;
            if (dist[j] == dist[i] - 1 && onpath[i][j]) {
                parent = j;
                break;
            }
        }
        if (parent == -1) {
            // As a fallback (should not happen), connect to root
            parent = r;
        }
        edges.emplace_back(i, parent);
    }

    cout << "!" << endl;
    for (auto &e : edges) {
        cout << e.first << " " << e.second << endl;
    }
    cout.flush();

    return 0;
}