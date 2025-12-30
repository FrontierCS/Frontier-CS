#include <bits/stdc++.h>
using namespace std;

struct Cell {
    int r, c, val;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> h(N, vector<int>(N));
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            cin >> h[i][j];

    vector<Cell> pos, neg;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (h[i][j] > 0) pos.push_back({i, j, h[i][j]});
            else if (h[i][j] < 0) neg.push_back({i, j, h[i][j]});
        }
    }

    vector<string> ops;
    int curR = 0, curC = 0;
    long long load = 0;

    auto moveTo = [&](int tr, int tc) {
        while (curR < tr) {
            ops.push_back("D");
            ++curR;
        }
        while (curR > tr) {
            ops.push_back("U");
            --curR;
        }
        while (curC < tc) {
            ops.push_back("R");
            ++curC;
        }
        while (curC > tc) {
            ops.push_back("L");
            --curC;
        }
    };

    // Collect soil from positive cells
    for (const Cell &p : pos) {
        moveTo(p.r, p.c);
        if (p.val > 0) {
            ops.push_back("+" + to_string(p.val));
            load += p.val;
        }
    }

    // Distribute soil to negative cells
    for (const Cell &n : neg) {
        moveTo(n.r, n.c);
        int d = -n.val; // positive amount to unload
        if (d > 0) {
            ops.push_back("-" + to_string(d));
            load -= d;
        }
    }

    for (const string &s : ops) {
        cout << s << '\n';
    }

    return 0;
}