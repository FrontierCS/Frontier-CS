#include <bits/stdc++.h>
using namespace std;

static constexpr int N = 30;
static constexpr int M = N * (N + 1) / 2;
static constexpr int K_LIMIT = 10000;

struct Op {
    int x1, y1, x2, y2;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> val(M, -1);

    int id[N][N];
    int cur = 0;
    for (int x = 0; x < N; x++) {
        for (int y = 0; y <= x; y++) id[x][y] = cur++;
    }

    vector<int> xs(M), ys(M);
    for (int x = 0; x < N; x++) {
        for (int y = 0; y <= x; y++) {
            int v = id[x][y];
            xs[v] = x;
            ys[v] = y;
        }
    }

    // Read
    for (int x = 0; x < N; x++) {
        for (int y = 0; y <= x; y++) {
            int b;
            cin >> b;
            val[id[x][y]] = b;
        }
    }

    vector<int> ch1(M, -1), ch2(M, -1);
    vector<array<int, 2>> parents(M, array<int,2>{-1, -1});
    for (int x = 0; x < N; x++) {
        for (int y = 0; y <= x; y++) {
            int u = id[x][y];
            if (x + 1 < N) {
                ch1[u] = id[x + 1][y];
                ch2[u] = id[x + 1][y + 1];
            }
            int pi = 0;
            if (x - 1 >= 0) {
                if (y - 1 >= 0) parents[u][pi++] = id[x - 1][y - 1];
                if (y <= x - 1) parents[u][pi++] = id[x - 1][y];
            }
        }
    }

    auto bestChildAndDiff = [&](int u) -> pair<int,int> {
        if (ch1[u] < 0) return {0, -1};
        int a = ch1[u], b = ch2[u];
        int c = (val[a] < val[b]) ? a : b;
        return {val[u] - val[c], c};
    };

    priority_queue<pair<int,int>> pq; // (diff, node)
    auto pushNode = [&](int u) {
        if (u < 0 || ch1[u] < 0) return;
        auto [diff, c] = bestChildAndDiff(u);
        if (diff > 0) pq.push({diff, u});
    };

    for (int u = 0; u < M; u++) pushNode(u);

    vector<Op> ops;
    ops.reserve(K_LIMIT);

    while (!pq.empty() && (int)ops.size() < K_LIMIT) {
        auto [d, u] = pq.top();
        pq.pop();

        if (ch1[u] < 0) continue;
        auto [diff, c] = bestChildAndDiff(u);
        if (diff <= 0) continue;

        // swap u and c
        swap(val[u], val[c]);
        ops.push_back(Op{xs[u], ys[u], xs[c], ys[c]});

        // c increased: may violate with its children
        pushNode(c);

        // u decreased: its parents may now violate
        pushNode(parents[u][0]);
        pushNode(parents[u][1]);
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op.x1 << ' ' << op.y1 << ' ' << op.x2 << ' ' << op.y2 << '\n';
    }
    return 0;
}