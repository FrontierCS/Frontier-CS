#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1005;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int r = 1; // choose 1 as root

    vector< bitset<MAXN> > onPath(n + 1);

    // For each vertex x != r, query for each w if w lies on path(r, x)
    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        onPath[x].reset();
        onPath[x][r] = 1;
        onPath[x][x] = 1;
        for (int w = 1; w <= n; ++w) {
            if (w == r || w == x) continue;
            cout << "? 2 " << w << " " << r << " " << x << endl;
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            if (ans == 1) onPath[x][w] = 1;
        }
    }

    // Compute depth from root r
    vector<int> depth(n + 1, 0);
    depth[r] = 0;
    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        int cnt = (int)onPath[x].count();
        depth[x] = cnt - 1; // path length is (#vertices on path) - 1
    }

    // Determine parent of each vertex (except root)
    vector<int> parent(n + 1, 0);
    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        int dep = depth[x];
        int best = 0;
        for (int y = 1; y <= n; ++y) {
            if (depth[y] == dep - 1 && onPath[x][y]) {
                best = y;
                break;
            }
        }
        parent[x] = best;
    }

    // Output the reconstructed tree
    cout << "!\n";
    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        cout << parent[x] << " " << x << "\n";
    }
    cout.flush();

    return 0;
}