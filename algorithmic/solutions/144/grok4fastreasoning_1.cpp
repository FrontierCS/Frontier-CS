#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    int A, B;
    cout << 0 << " " << n;
    for (int i = 1; i <= n; i++) {
        cout << " " << i;
    }
    cout << endl;
    cout.flush();
    cin >> A >> B;
    vector<pair<int, int>> pair_resp(n / 2);
    for (int p = 0; p < n / 2; p++) {
        int i = 2 * p + 1;
        int j = 2 * p + 2;
        cout << 0 << " " << n - 2;
        for (int idx = 1; idx <= n; idx++) {
            if (idx != i && idx != j) {
                cout << " " << idx;
            }
        }
        cout << endl;
        cout.flush();
        int m1, m2;
        cin >> m1 >> m2;
        pair_resp[p] = {m1, m2};
    }
    int pairA = -1;
    for (int p = 0; p < n / 2; p++) {
        int m1 = pair_resp[p].first;
        int m2 = pair_resp[p].second;
        if ((m1 == A - 1 && m2 == B) ||
            (m1 == B && m2 == B + 1) ||
            (m1 == A - 1 && m2 == B + 1)) {
            pairA = p;
            break;
        }
    }
    int pairB = -1;
    for (int p = 0; p < n / 2; p++) {
        int m1 = pair_resp[p].first;
        int m2 = pair_resp[p].second;
        if ((m1 == A && m2 == B + 1) ||
            (m1 == A - 1 && m2 == B + 1)) {
            pairB = p;
            break;
        }
    }
    int posA, posB;
    int x = 2 * pairA + 1;
    int y = x + 1;
    int xb = 2 * pairB + 1;
    int yb = xb + 1;
    if (pairA == pairB) {
        int zz = 1;
        while (zz == x || zz == y) zz++;
        cout << 0 << " " << n - 2;
        for (int idx = 1; idx <= n; idx++) {
            if (idx != x && idx != zz) {
                cout << " " << idx;
            }
        }
        cout << endl;
        cout.flush();
        int mm1, mm2;
        cin >> mm1 >> mm2;
        bool x_is_A = ((mm1 == A - 1 && mm2 == B) ||
                       (mm1 == B && mm2 == B + 1) ||
                       (mm1 == A - 1 && mm2 == B + 1));
        posA = x_is_A ? x : y;
        posB = x_is_A ? y : x;
    } else {
        int zz = 1;
        while (zz == x || zz == y) zz++;
        cout << 0 << " " << n - 2;
        for (int idx = 1; idx <= n; idx++) {
            if (idx != x && idx != zz) {
                cout << " " << idx;
            }
        }
        cout << endl;
        cout.flush();
        int mm1, mm2;
        cin >> mm1 >> mm2;
        bool x_is_A = ((mm1 == A - 1 && mm2 == B) ||
                       (mm1 == B && mm2 == B + 1) ||
                       (mm1 == A - 1 && mm2 == B + 1));
        posA = x_is_A ? x : y;
        int zz2 = 1;
        while (zz2 == xb || zz2 == yb || zz2 == posA) zz2++;
        cout << 0 << " " << n - 2;
        for (int idx = 1; idx <= n; idx++) {
            if (idx != xb && idx != zz2) {
                cout << " " << idx;
            }
        }
        cout << endl;
        cout.flush();
        int mmb1, mmb2;
        cin >> mmb1 >> mmb2;
        bool xb_is_B = ((mmb1 == A && mmb2 == B + 1) ||
                        (mmb1 == A - 1 && mmb2 == B + 1));
        posB = xb_is_B ? xb : yb;
    }
    if (posA > posB) {
        swap(posA, posB);
    }
    cout << 1 << " " << posA << " " << posB << endl;
    cout.flush();
    return 0;
}