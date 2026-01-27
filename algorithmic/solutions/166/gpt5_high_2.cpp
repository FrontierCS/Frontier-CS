#include <bits/stdc++.h>
using namespace std;

struct Cell {
    int y, x;
    int amt; // positive for pos list, positive (abs) for neg list
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
            else if (h[i][j] < 0) neg.push_back({i, j, -h[i][j]});
        }
    }

    int cy = 0, cx = 0;
    vector<string> ops;
    const int LIM = 100000;

    auto path_len = [&](int y1, int x1, int y2, int x2) -> int {
        return abs(y1 - y2) + abs(x1 - x2);
    };
    auto add_move = [&](int ty, int tx) {
        while (cy < ty) { ops.emplace_back("D"); cy++; }
        while (cy > ty) { ops.emplace_back("U"); cy--; }
        while (cx < tx) { ops.emplace_back("R"); cx++; }
        while (cx > tx) { ops.emplace_back("L"); cx--; }
    };

    vector<int> posAmt(pos.size()), negAmt(neg.size());
    for (size_t i = 0; i < pos.size(); ++i) posAmt[i] = pos[i].amt;
    for (size_t i = 0; i < neg.size(); ++i) negAmt[i] = neg[i].amt;

    int remainPos = 0, remainNeg = 0;
    for (int a : posAmt) if (a > 0) remainPos++;
    for (int a : negAmt) if (a > 0) remainNeg++;

    while (remainPos > 0 && remainNeg > 0) {
        int pi = -1, bestd = INT_MAX;
        for (int i = 0; i < (int)pos.size(); ++i) {
            if (posAmt[i] <= 0) continue;
            int d = abs(pos[i].y - cy) + abs(pos[i].x - cx);
            if (d < bestd) { bestd = d; pi = i; }
        }
        if (pi == -1) break;

        int ni = -1, bestd2 = INT_MAX;
        for (int j = 0; j < (int)neg.size(); ++j) {
            if (negAmt[j] <= 0) continue;
            int d2 = abs(neg[j].y - pos[pi].y) + abs(neg[j].x - pos[pi].x);
            if (d2 < bestd2) { bestd2 = d2; ni = j; }
        }
        if (ni == -1) break;

        int d = min(posAmt[pi], negAmt[ni]);
        int l1 = path_len(cy, cx, pos[pi].y, pos[pi].x);
        int l2 = path_len(pos[pi].y, pos[pi].x, neg[ni].y, neg[ni].x);

        if ((int)ops.size() + l1 + 1 + l2 + 1 > LIM) break;

        add_move(pos[pi].y, pos[pi].x);
        ops.emplace_back("+" + to_string(d));
        add_move(neg[ni].y, neg[ni].x);
        ops.emplace_back("-" + to_string(d));

        posAmt[pi] -= d;
        if (posAmt[pi] == 0) remainPos--;
        negAmt[ni] -= d;
        if (negAmt[ni] == 0) remainNeg--;
    }

    for (auto &s : ops) cout << s << '\n';
    return 0;
}