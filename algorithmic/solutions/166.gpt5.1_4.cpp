#include <bits/stdc++.h>
using namespace std;

struct Cell {
    int i, j;
    int rem;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> h(N, vector<int>(N));
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> h[i][j];
        }
    }

    vector<Cell> pos, neg;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (h[i][j] > 0) pos.push_back({i, j, h[i][j]});
            else if (h[i][j] < 0) neg.push_back({i, j, -h[i][j]});
        }
    }

    vector<string> ops;
    int ci = 0, cj = 0; // current position

    auto move_to = [&](int ti, int tj) {
        while (ci < ti) {
            ops.emplace_back("D");
            ++ci;
        }
        while (ci > ti) {
            ops.emplace_back("U");
            --ci;
        }
        while (cj < tj) {
            ops.emplace_back("R");
            ++cj;
        }
        while (cj > tj) {
            ops.emplace_back("L");
            --cj;
        }
    };

    size_t pi = 0, ni = 0;
    while (pi < pos.size() && ni < neg.size()) {
        while (pi < pos.size() && pos[pi].rem == 0) ++pi;
        while (ni < neg.size() && neg[ni].rem == 0) ++ni;
        if (pi >= pos.size() || ni >= neg.size()) break;

        Cell &pc = pos[pi];
        Cell &nc = neg[ni];

        move_to(pc.i, pc.j);
        int d = min(pc.rem, nc.rem);
        // load d from positive cell
        ops.push_back("+" + to_string(d));
        pc.rem -= d;

        move_to(nc.i, nc.j);
        // unload d to negative cell
        ops.push_back("-" + to_string(d));
        nc.rem -= d;
    }

    for (const auto &s : ops) {
        cout << s << '\n';
    }

    return 0;
}