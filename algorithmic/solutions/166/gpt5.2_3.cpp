#include <bits/stdc++.h>
using namespace std;

static const int N_FIXED = 20;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<vector<int>> h(N, vector<int>(N));
    long long sum = 0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> h[i][j];
            sum += h[i][j];
        }
    }

    vector<string> ops;
    int x = 0, y = 0;
    long long load = 0;

    auto push_op = [&](const string& s) {
        ops.push_back(s);
    };

    auto moveTo = [&](int tx, int ty) {
        while (x < tx) { push_op("D"); x++; }
        while (x > tx) { push_op("U"); x--; }
        while (y < ty) { push_op("R"); y++; }
        while (y > ty) { push_op("L"); y--; }
    };

    auto existsNonZero = [&]() -> bool {
        for (int i = 0; i < N; i++)
            for (int j = 0; j < N; j++)
                if (h[i][j] != 0) return true;
        return false;
    };

    auto nearestCell = [&](int sx, int sy, int sign) -> pair<int,int> {
        // sign: +1 => h>0, -1 => h<0
        int bestD = INT_MAX;
        int bx = -1, by = -1;
        int bestMag = -1;
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                if ((sign == 1 && h[i][j] > 0) || (sign == -1 && h[i][j] < 0)) {
                    int d = abs(i - sx) + abs(j - sy);
                    int mag = abs(h[i][j]);
                    if (d < bestD || (d == bestD && mag > bestMag)) {
                        bestD = d;
                        bestMag = mag;
                        bx = i; by = j;
                    }
                }
            }
        }
        return {bx, by};
    };

    auto processCurrent = [&]() {
        if (h[x][y] > 0) {
            int d = h[x][y];
            push_op("+" + to_string(d));
            load += d;
            h[x][y] -= d;
        }
        if (h[x][y] < 0 && load > 0) {
            long long need = -(long long)h[x][y];
            long long d = min(load, need);
            push_op("-" + to_string((long long)d));
            load -= d;
            h[x][y] += (int)d;
        }
    };

    // Main loop
    int safe_iter = 0;
    while (existsNonZero()) {
        if (++safe_iter > 200000) break; // safety
        processCurrent();
        if (!existsNonZero()) break;

        if (load == 0) {
            auto [px, py] = nearestCell(x, y, +1);
            if (px == -1) break; // should not happen
            moveTo(px, py);
        } else {
            auto [nx, ny] = nearestCell(x, y, -1);
            if (nx == -1) break; // should not happen
            moveTo(nx, ny);
        }

        if ((int)ops.size() > 100000) break;
    }

    // Final attempt at current cell
    processCurrent();

    // Output (may be empty)
    for (auto &s : ops) cout << s << "\n";
    return 0;
}