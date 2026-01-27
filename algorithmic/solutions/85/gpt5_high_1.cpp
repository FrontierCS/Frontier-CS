#include <bits/stdc++.h>
using namespace std;

int moveOp(int c) {
    cout << "move " << c << endl;
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    return r;
}

int queryOp() {
    cout << "query" << endl;
    cout.flush();
    int d;
    if (!(cin >> d)) exit(0);
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0;
    if (d == 0) return 0;

    while (d > 0) {
        int flag = moveOp(0);
        if (flag == 1) return 0;
        int nd = queryOp();
        if (nd == d - 1) {
            d = nd;
            continue;
        }
        // move back
        flag = moveOp(0);
        if (flag == 1) return 0;

        flag = moveOp(1);
        if (flag == 1) return 0;
        nd = queryOp();
        if (nd == d - 1) {
            d = nd;
            continue;
        }
        // move back
        flag = moveOp(1);
        if (flag == 1) return 0;

        // must be color 2
        flag = moveOp(2);
        if (flag == 1) return 0;
        d = d - 1;
    }
    return 0;
}