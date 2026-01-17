#include <bits/stdc++.h>
using namespace std;

int main() {
    long long xx;
    cin >> xx;
    __int128 x = xx;
    const int MAX = 121;
    __int128 c[MAX + 1][MAX + 1];
    memset(c, 0, sizeof(c));
    for (int i = 0; i <= MAX; i++) {
        c[i][0] = 1;
        if (i <= MAX) c[i][i] = 1;
        for (int j = 1; j < i && j <= MAX; j++) {
            c[i][j] = c[i - 1][j] + c[i - 1][j - 1];
        }
    }
    int chosen_n = -1;
    int ci = -1, cj = -1;
    bool block = false;
    for (int nn = 1; nn <= 300; nn++) {
        if (2 * nn - 2 > MAX || nn - 1 > MAX) continue;
        __int128 bb = c[2 * nn - 2][nn - 1];
        if (bb < x) continue;
        __int128 ee = bb - x;
        bool f = false;
        if (ee == 0) {
            f = true;
        } else {
            for (int ii = 1; ii <= nn && !f; ii++) {
                for (int jj = 1; jj <= nn && !f; jj++) {
                    int aa = ii + jj - 2;
                    int kk = ii - 1;
                    __int128 too = (aa < 0 || kk < 0 || kk > aa) ? 0 : c[aa][kk];
                    aa = 2 * nn - ii - jj;
                    kk = nn - ii;
                    __int128 frr = (aa < 0 || kk < 0 || kk > aa) ? 0 : c[aa][kk];
                    __int128 thh = too * frr;
                    if (thh == ee) {
                        f = true;
                        chosen_n = nn;
                        ci = ii;
                        cj = jj;
                        block = true;
                    }
                }
            }
        }
        if (f) {
            chosen_n = nn;
            break;
        }
    }
    cout << chosen_n << endl;
    for (int i = 1; i <= chosen_n; i++) {
        for (int j = 1; j <= chosen_n; j++) {
            if (block && i == ci && j == cj) {
                cout << 0;
            } else {
                cout << 1;
            }
            cout << (j == chosen_n ? "\n" : " ");
        }
    }
    return 0;
}