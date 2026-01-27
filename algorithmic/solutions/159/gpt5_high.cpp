#include <bits/stdc++.h>
using namespace std;

struct Operation {
    int x1, y1, x2, y2, x3, y3, x4, y4;
};

static inline uint64_t edgeKey(int x1, int y1, int x2, int y2) {
    if (x1 > x2 || (x1 == x2 && y1 > y2)) {
        swap(x1, x2);
        swap(y1, y2);
    }
    uint64_t k = 0;
    k |= (uint64_t)(x1 & 0xFFFF) << 48;
    k |= (uint64_t)(y1 & 0xFFFF) << 32;
    k |= (uint64_t)(x2 & 0xFFFF) << 16;
    k |= (uint64_t)(y2 & 0xFFFF);
    return k;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<vector<char>> dot(N, vector<char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        if (0 <= x && x < N && 0 <= y && y < N) dot[x][y] = 1;
    }

    unordered_set<uint64_t> usedEdges;
    usedEdges.reserve(1 << 20);
    vector<Operation> ops;

    auto can_use_edges = [&](const array<int,4>& px, const array<int,4>& py) -> bool {
        for (int i = 0; i < 4; ++i) {
            int j = (i + 1) % 4;
            uint64_t k = edgeKey(px[i], py[i], px[j], py[j]);
            if (usedEdges.find(k) != usedEdges.end()) return false;
        }
        return true;
    };

    auto add_edges = [&](const array<int,4>& px, const array<int,4>& py) {
        for (int i = 0; i < 4; ++i) {
            int j = (i + 1) % 4;
            usedEdges.insert(edgeKey(px[i], py[i], px[j], py[j]));
        }
    };

    bool changed = true;
    while (changed) {
        changed = false;

        // Axis-aligned unit squares
        for (int y = 0; y + 1 < N; ++y) {
            for (int x = 0; x + 1 < N; ++x) {
                array<int,4> px = {x, x+1, x+1, x};
                array<int,4> py = {y, y, y+1, y+1};
                int cnt = 0, missing = -1;
                for (int i = 0; i < 4; ++i) {
                    if (dot[px[i]][py[i]]) cnt++;
                    else missing = i;
                }
                if (cnt != 3) continue;
                if (!can_use_edges(px, py)) continue;
                // Place dot and record operation
                int i1 = missing;
                int i2 = (missing + 1) % 4;
                int i3 = (missing + 2) % 4;
                int i4 = (missing + 3) % 4;
                ops.push_back({px[i1], py[i1], px[i2], py[i2], px[i3], py[i3], px[i4], py[i4]});
                dot[px[i1]][py[i1]] = 1;
                add_edges(px, py);
                changed = true;
            }
        }

        // 45-degree unit squares (diamonds)
        for (int y = 0; y + 2 < N; ++y) {
            for (int x = 1; x + 1 < N; ++x) {
                array<int,4> px = {x, x+1, x, x-1};
                array<int,4> py = {y, y+1, y+2, y+1};
                // Check bounds (already ensured by loops)
                int cnt = 0, missing = -1;
                for (int i = 0; i < 4; ++i) {
                    if (dot[px[i]][py[i]]) cnt++;
                    else missing = i;
                }
                if (cnt != 3) continue;
                if (!can_use_edges(px, py)) continue;
                int i1 = missing;
                int i2 = (missing + 1) % 4;
                int i3 = (missing + 2) % 4;
                int i4 = (missing + 3) % 4;
                ops.push_back({px[i1], py[i1], px[i2], py[i2], px[i3], py[i3], px[i4], py[i4]});
                dot[px[i1]][py[i1]] = 1;
                add_edges(px, py);
                changed = true;
            }
        }
    }

    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.x1 << " " << op.y1 << " " << op.x2 << " " << op.y2 << " "
             << op.x3 << " " << op.y3 << " " << op.x4 << " " << op.y4 << "\n";
    }
    return 0;
}