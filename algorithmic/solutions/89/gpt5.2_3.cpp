#include <bits/stdc++.h>
using namespace std;

static int n;

static int ask_path(int test_v, int a, int b) {
    cout << "? 2 " << test_v << " " << a << " " << b << "\n";
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "!\n";
        cout.flush();
        return 0;
    }

    const int root = 1;

    vector<vector<uint8_t>> anc(n + 1, vector<uint8_t>(n + 1, 0));
    for (int v = 1; v <= n; v++) anc[v][v] = 1;
    for (int v = 1; v <= n; v++) anc[root][v] = 1;
    for (int v = 2; v <= n; v++) anc[v][root] = 0;

    for (int b = 2; b <= n; b++) {
        for (int a = 2; a <= n; a++) {
            if (a == b) continue;
            anc[a][b] = (uint8_t)ask_path(a, root, b);
        }
    }

    vector<int> parent(n + 1, 0);
    parent[root] = 0;

    for (int v = 2; v <= n; v++) {
        int cand = root;
        for (int u = 2; u <= n; u++) {
            if (u == v) continue;
            if (!anc[u][v]) continue;
            if (cand != u && anc[cand][u]) cand = u;
        }
        parent[v] = cand;
    }

    cout << "!\n";
    for (int v = 2; v <= n; v++) {
        cout << parent[v] << " " << v << "\n";
    }
    cout.flush();
    return 0;
}