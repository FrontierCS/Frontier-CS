#include <bits/stdc++.h>
using namespace std;

int main() {
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        int n;
        cin >> n;
        vector<int> deg(n + 1);
        for (int i = 1; i <= n; i++) {
            string q(n, '0');
            q[i - 1] = '1';
            cout << "? " << q << endl;
            fflush(stdout);
            int d;
            cin >> d;
            deg[i] = d;
        }
        vector<bool> inS(n + 1, false);
        inS[1] = true;
        int sizeS = 1;
        while (true) {
            string qs(n, '0');
            for (int i = 1; i <= n; i++) {
                if (inS[i]) qs[i - 1] = '1';
            }
            cout << "? " << qs << endl;
            fflush(stdout);
            int b;
            cin >> b;
            if (b == 0) {
                cout << "! " << (sizeS == n ? 1 : 0) << endl;
                fflush(stdout);
                break;
            }
            vector<int> delta(n + 1, 0);
            for (int i = 1; i <= n; i++) {
                if (inS[i]) continue;
                string qx = qs;
                qx[i - 1] = '1';
                cout << "? " << qx << endl;
                fflush(stdout);
                int bx;
                cin >> bx;
                delta[i] = bx - b;
            }
            vector<int> to_add;
            for (int i = 1; i <= n; i++) {
                if (inS[i]) continue;
                int dlt = delta[i];
                bool eligible = (dlt <= 0) || (deg[i] > dlt);
                if (eligible) {
                    to_add.push_back(i);
                }
            }
            bool added = !to_add.empty();
            for (int i : to_add) {
                inS[i] = true;
                sizeS++;
            }
            if (!added) {
                cout << "! 0" << endl;
                fflush(stdout);
                break;
            }
        }
    }
    return 0;
}