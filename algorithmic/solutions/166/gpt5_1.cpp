#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> h(N, vector<int>(N));
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) cin >> h[i][j];

    struct Cell { int r, c, amt; };
    vector<Cell> posCells, negCells;

    // Snake order
    for (int i = 0; i < N; i++) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; j++) {
                if (h[i][j] > 0) posCells.push_back({i, j, h[i][j]});
                else if (h[i][j] < 0) negCells.push_back({i, j, -h[i][j]});
            }
        } else {
            for (int j = N - 1; j >= 0; j--) {
                if (h[i][j] > 0) posCells.push_back({i, j, h[i][j]});
                else if (h[i][j] < 0) negCells.push_back({i, j, -h[i][j]});
            }
        }
    }

    auto moveTo = [&](int &cr, int &cc, int tr, int tc) {
        while (cr < tr) { cout << "D\n"; cr++; }
        while (cr > tr) { cout << "U\n"; cr--; }
        while (cc < tc) { cout << "R\n"; cc++; }
        while (cc > tc) { cout << "L\n"; cc--; }
    };

    int cr = 0, cc = 0;
    long long carry = 0;

    // Collect from positive cells
    for (auto &cell : posCells) {
        moveTo(cr, cc, cell.r, cell.c);
        if (cell.amt > 0) {
            cout << "+" << cell.amt << "\n";
            carry += cell.amt;
        }
    }

    // Distribute to negative cells
    for (auto &cell : negCells) {
        moveTo(cr, cc, cell.r, cell.c);
        if (cell.amt > 0) {
            int d = cell.amt;
            if (d > carry) d = (int)carry; // Shouldn't happen, but just in case
            if (d > 0) {
                cout << "-" << d << "\n";
                carry -= d;
            }
            // If any remainder (shouldn't), ignore to keep within constraints
        }
    }

    return 0;
}