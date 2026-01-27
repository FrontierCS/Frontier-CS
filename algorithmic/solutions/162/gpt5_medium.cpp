#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 30;
    vector<vector<int>> b(N);
    for (int x = 0; x < N; ++x) {
        b[x].resize(x + 1);
        for (int y = 0; y <= x; ++y) cin >> b[x][y];
    }

    vector<array<int,4>> ops;
    ops.reserve(10000);

    while ((int)ops.size() < 10000) {
        bool changed = false;
        for (int x = N - 2; x >= 0; --x) {
            for (int y = 0; y <= x; ++y) {
                int p = b[x][y];
                int bestcx = -1, bestcy = -1, bestv = p;

                // child (x+1, y)
                if (b[x+1][y] < bestv) {
                    bestv = b[x+1][y];
                    bestcx = x + 1;
                    bestcy = y;
                }
                // child (x+1, y+1)
                if (b[x+1][y+1] < bestv) {
                    bestv = b[x+1][y+1];
                    bestcx = x + 1;
                    bestcy = y + 1;
                }

                if (bestcx != -1) {
                    swap(b[x][y], b[bestcx][bestcy]);
                    ops.push_back({x, y, bestcx, bestcy});
                    changed = true;
                    if ((int)ops.size() >= 10000) break;
                }
            }
            if ((int)ops.size() >= 10000) break;
        }
        if (!changed) break;
    }

    cout << ops.size() << '\n';
    for (auto &o : ops) {
        cout << o[0] << ' ' << o[1] << ' ' << o[2] << ' ' << o[3] << '\n';
    }
    return 0;
}