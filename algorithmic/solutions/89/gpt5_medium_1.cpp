#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int r = 1;
    vector<int> depth(n + 1, 0);
    vector<vector<unsigned char>> onpath(n + 1, vector<unsigned char>(n + 1, 0));

    auto ask = [&](int k, int v, int a, int b) -> int {
        cout << "? " << k << " " << v << " " << a;
        if (k == 2) cout << " " << b;
        cout << endl;
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);
        return ans;
    };

    // Compute depths and store membership of all nodes on paths (r, x) for x != r
    for (int x = 1; x <= n; ++x) {
        if (x == r) { depth[x] = 0; continue; }
        int cnt = 0;
        for (int v = 1; v <= n; ++v) {
            int ans = ask(2, v, r, x);
            onpath[x][v] = (unsigned char)ans;
            cnt += ans;
        }
        depth[x] = cnt - 1;
    }

    // Determine parents using depth and onpath info
    vector<int> parent(n + 1, -1);
    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        int need = depth[x] - 1;
        int p = -1;
        for (int y = 1; y <= n; ++y) {
            if (depth[y] == need && onpath[x][y]) {
                p = y;
                break;
            }
        }
        if (p == -1) {
            // Fallback: in case we didn't compute path info (shouldn't happen), try querying
            for (int y = 1; y <= n; ++y) {
                if (depth[y] == need) {
                    int ans = ask(2, y, r, x);
                    if (ans) { p = y; break; }
                }
            }
        }
        parent[x] = p;
    }

    // Output the reconstructed tree
    cout << "!" << endl;
    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        cout << parent[x] << " " << x << endl;
    }
    cout.flush();
    return 0;
}