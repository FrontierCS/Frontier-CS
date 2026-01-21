#include <bits/stdc++.h>
using namespace std;

static long long moveCnt = 0, queryCnt = 0;

int doMove(int c) {
    if (++moveCnt > 100000) exit(0);
    cout << "move " << c << "\n" << flush;
    int r;
    if (!(cin >> r)) exit(0);
    return r;
}

int doQuery() {
    if (++queryCnt > 100000) exit(0);
    cout << "query\n" << flush;
    int d;
    if (!(cin >> d)) exit(0);
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int dist;
    if (!(cin >> dist)) return 0;
    if (dist == 0) return 0;

    int back = -1; // color of edge leading back to the node we came from (a child edge at current node)

    while (dist > 0) {
        if (back == -1) {
            int a = 0, b = 1, c = 2;

            if (doMove(a) == 1) return 0;
            int d1 = doQuery();
            if (d1 == dist - 1) {
                dist = d1;
                back = a;
                continue;
            } else {
                (void)doMove(a); // back
                if (doMove(b) == 1) return 0;
                int d2 = doQuery();
                if (d2 == dist - 1) {
                    dist = d2;
                    back = b;
                    continue;
                } else {
                    (void)doMove(b); // back
                    if (doMove(c) == 1) return 0;
                    dist -= 1;
                    back = c;
                    continue;
                }
            }
        } else {
            int p = -1, q = -1;
            for (int x = 0; x < 3; x++) {
                if (x == back) continue;
                if (p == -1) p = x;
                else q = x;
            }

            if (doMove(p) == 1) return 0;
            int nd = doQuery();
            if (nd == dist - 1) {
                dist = nd;
                back = p;
                continue;
            } else {
                (void)doMove(p); // back
                if (doMove(q) == 1) return 0;
                dist -= 1;
                back = q;
                continue;
            }
        }
    }

    return 0;
}