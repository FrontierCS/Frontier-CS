#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<vector<int>> D(n, vector<int>(n));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cin >> D[i][j];
        }
    }
    vector<vector<int>> F(n, vector<int>(n));
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            cin >> F[i][j];
        }
    }
    vector<int> deg_f(n, 0), deg_d(n, 0);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            deg_f[i] += F[i][j];
            deg_d[i] += D[i][j];
        }
    }
    vector<int> fac_order(n);
    iota(fac_order.begin(), fac_order.end(), 0);
    sort(fac_order.begin(), fac_order.end(), [&](int x, int y) {
        if (deg_f[x] != deg_f[y]) return deg_f[x] > deg_f[y];
        return x < y;
    });
    vector<int> loc_order(n);
    iota(loc_order.begin(), loc_order.end(), 0);
    sort(loc_order.begin(), loc_order.end(), [&](int x, int y) {
        if (deg_d[x] != deg_d[y]) return deg_d[x] < deg_d[y];
        return x < y;
    });
    vector<int> p(n + 1);
    for (int k = 0; k < n; k++) {
        int fac = fac_order[k];
        int loc = loc_order[k];
        p[fac + 1] = loc + 1;
    }
    for (int i = 1; i <= n; i++) {
        cout << p[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}