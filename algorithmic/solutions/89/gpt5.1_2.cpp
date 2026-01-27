#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1000 + 5;

bool anc[MAXN][MAXN];
int depthArr[MAXN];
int parentArr[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 0) return 0;

    int r = 1;

    anc[r][r] = true;

    for (int t = 1; t <= n; ++t) {
        if (t == r) continue;
        anc[t][t] = true;
        anc[r][t] = true;
        for (int x = 1; x <= n; ++x) {
            if (x == r || x == t) continue;
            cout << "? 2 " << x << " " << r << " " << t << endl;
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            if (ans == 1) {
                anc[x][t] = true;
            }
        }
    }

    // Compute depths
    for (int v = 1; v <= n; ++v) {
        int cnt = 0;
        for (int u = 1; u <= n; ++u) {
            if (anc[u][v]) ++cnt;
        }
        depthArr[v] = cnt - 1;
    }

    int root = r;
    parentArr[root] = 0;

    // Compute parents
    for (int v = 1; v <= n; ++v) {
        if (v == root) continue;
        parentArr[v] = -1;
        for (int u = 1; u <= n; ++u) {
            if (u == v) continue;
            if (anc[u][v] && depthArr[u] == depthArr[v] - 1) {
                parentArr[v] = u;
                break;
            }
        }
    }

    cout << "!" << endl;
    for (int v = 1; v <= n; ++v) {
        if (v == root) continue;
        cout << v << " " << parentArr[v] << endl;
    }
    cout.flush();

    return 0;
}