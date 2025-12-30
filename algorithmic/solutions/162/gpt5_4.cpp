#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int x1, y1, x2, y2;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    const int N = 30;
    vector<vector<int>> a(N);
    for (int x = 0; x < N; x++) {
        a[x].resize(x + 1);
        for (int y = 0; y <= x; y++) {
            cin >> a[x][y];
        }
    }

    auto in = [&](int x, int y) -> bool {
        return (0 <= x && x < N && 0 <= y && y <= x);
    };

    auto countViolTop = [&](int x, int y) -> int {
        if (x >= N - 1) return 0;
        int v = a[x][y];
        int res = 0;
        if (v > a[x + 1][y]) res++;
        if (v > a[x + 1][y + 1]) res++;
        return res;
    };

    auto totalViol = [&]() -> int {
        int E = 0;
        for (int x = 0; x < N - 1; x++) {
            for (int y = 0; y <= x; y++) {
                int v = a[x][y];
                if (v > a[x + 1][y]) E++;
                if (v > a[x + 1][y + 1]) E++;
            }
        }
        return E;
    };

    vector<Edge> edges;
    edges.reserve(2000);
    for (int x = 0; x < N; x++) {
        for (int y = 0; y <= x; y++) {
            if (y + 1 <= x) {
                edges.push_back({x, y, x, y + 1});
            }
            if (x + 1 < N) {
                edges.push_back({x, y, x + 1, y});
                edges.push_back({x, y, x + 1, y + 1});
            }
        }
    }

    auto addTop = [&](vector<pair<int,int>>& tops, int tx, int ty) {
        if (!in(tx, ty)) return;
        for (auto &p : tops) {
            if (p.first == tx && p.second == ty) return;
        }
        tops.emplace_back(tx, ty);
    };

    auto deltaSwap = [&](const Edge& e) -> int {
        int x1 = e.x1, y1 = e.y1, x2 = e.x2, y2 = e.y2;
        vector<pair<int,int>> tops;
        if (x1 < N - 1) addTop(tops, x1, y1);
        if (x2 < N - 1) addTop(tops, x2, y2);
        addTop(tops, x1 - 1, y1 - 1);
        addTop(tops, x1 - 1, y1);
        addTop(tops, x2 - 1, y2 - 1);
        addTop(tops, x2 - 1, y2);

        int before = 0;
        for (auto &t : tops) before += countViolTop(t.first, t.second);
        swap(a[x1][y1], a[x2][y2]);
        int after = 0;
        for (auto &t : tops) after += countViolTop(t.first, t.second);
        swap(a[x1][y1], a[x2][y2]);
        return after - before;
    };

    vector<array<int,4>> ops;
    ops.reserve(10000);

    int E = totalViol();

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    int K = 0;
    while (K < 10000 && E > 0) {
        bool improved = false;
        shuffle(edges.begin(), edges.end(), rng);
        for (const auto& e : edges) {
            if (K >= 10000 || E == 0) break;
            int d = deltaSwap(e);
            if (d < 0) {
                // perform swap
                swap(a[e.x1][e.y1], a[e.x2][e.y2]);
                ops.push_back({e.x1, e.y1, e.x2, e.y2});
                K++;
                E += d;
                improved = true;
            }
        }
        if (!improved) break;
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op[0] << ' ' << op[1] << ' ' << op[2] << ' ' << op[3] << '\n';
    }
    return 0;
}