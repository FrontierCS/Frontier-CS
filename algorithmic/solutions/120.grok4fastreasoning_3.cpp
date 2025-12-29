#include <bits/stdc++.h>
using namespace std;

int main() {
    vector<vector<int>> adj(101, vector<int>(101, 0));
    vector<pair<int, int>> edges = {{1,2}, {1,3}, {1,4}, {2,3}, {2,4}, {3,4}};
    int triplets[4][3] = {{1,2,3}, {1,2,4}, {1,3,4}, {2,3,4}};
    vector<int> responses(4);
    for (int q = 0; q < 4; q++) {
        int a = triplets[q][0], b = triplets[q][1], c = triplets[q][2];
        cout << "? " << a << " " << b << " " << c << endl;
        int s;
        cin >> s;
        responses[q] = s;
    }
    bool found = false;
    int best_mask = -1;
    for (int mask = 0; mask < 64; mask++) {
        int e12 = (mask & 1) ? 1 : 0;
        int e13 = (mask & 2) ? 1 : 0;
        int e14 = (mask & 4) ? 1 : 0;
        int e23 = (mask & 8) ? 1 : 0;
        int e24 = (mask & 16) ? 1 : 0;
        int e34 = (mask & 32) ? 1 : 0;
        int s123 = e12 + e13 + e23;
        int s124 = e12 + e14 + e24;
        int s134 = e13 + e14 + e34;
        int s234 = e23 + e24 + e34;
        if (s123 == responses[0] && s124 == responses[1] && s134 == responses[2] && s234 == responses[3]) {
            best_mask = mask;
            found = true;
            break;  // assume unique
        }
    }
    // set adj
    int e12 = (best_mask & 1) ? 1 : 0;
    int e13 = (best_mask & 2) ? 1 : 0;
    int e14 = (best_mask & 4) ? 1 : 0;
    int e23 = (best_mask & 8) ? 1 : 0;
    int e24 = (best_mask & 16) ? 1 : 0;
    int e34 = (best_mask & 32) ? 1 : 0;
    adj[1][2] = adj[2][1] = e12;
    adj[1][3] = adj[3][1] = e13;
    adj[1][4] = adj[4][1] = e14;
    adj[2][3] = adj[3][2] = e23;
    adj[2][4] = adj[4][2] = e24;
    adj[3][4] = adj[4][3] = e34;

    int r = 1;
    for (int m = 5; m <= 100; m++) {
        int k = m - 1;
        vector<int> t(k - 1);
        bool all_one = true;
        for (int p = 0; p < k - 1; p++) {
            int i = p + 2;
            cout << "? " << r << " " << i << " " << m << endl;
            int s;
            cin >> s;
            int e = adj[r][i];
            t[p] = s - e;
            if (t[p] != 1) all_one = false;
        }
        int xr;
        if (!all_one) {
            bool has_zero = false;
            bool has_two = false;
            for (int tt : t) {
                if (tt == 0) has_zero = true;
                if (tt == 2) has_two = true;
            }
            if (has_zero) {
                xr = 0;
            } else {
                xr = 1;
            }
        } else {
            // resolve
            int i1 = 2, i2 = 3;
            cout << "? " << i1 << " " << i2 << " " << m << endl;
            int s;
            cin >> s;
            int e = adj[i1][i2];
            int tt = s - e;
            if (tt == 2) {
                xr = 0;
            } else {
                xr = 1;
            }
        }
        adj[r][m] = adj[m][r] = xr;
        int pos = 0;
        for (int p = 0; p < k - 1; p++) {
            int i = p + 2;
            int xi;
            if (!all_one) {
                xi = t[pos] - xr;
            } else {
                xi = 1 - xr;
            }
            pos++;
            adj[i][m] = adj[m][i] = xi;
        }
    }
    cout << "!" << endl;
    for (int i = 1; i <= 100; i++) {
        for (int j = 1; j <= 100; j++) {
            cout << adj[i][j];
        }
        cout << endl;
    }
    cout << flush;
    return 0;
}