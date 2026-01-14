#include <bits/stdc++.h>
using namespace std;

int main() {
    int d;
    cin >> d;
    while (d > 0) {
        bool found = false;
        for (int c = 0; c < 2; c++) {
            cout << "move " << c << endl;
            cout.flush();
            int r;
            cin >> r;
            if (r == 1) return 0;
            cout << "query" << endl;
            cout.flush();
            int nd;
            cin >> nd;
            if (nd == d - 1) {
                d = nd;
                found = true;
                break;
            } else {
                cout << "move " << c << endl;
                cout.flush();
                int r2;
                cin >> r2;
                if (r2 == 1) return 0;
            }
        }
        if (!found) {
            int c = 2;
            cout << "move " << c << endl;
            cout.flush();
            int r;
            cin >> r;
            if (r == 1) return 0;
            d = d - 1;
        }
    }
    return 0;
}