#include <bits/stdc++.h>
using namespace std;

inline long long edgeKey(int x1, int y1, int x2, int y2) {
    if (x1 > x2 || (x1 == x2 && y1 > y2)) {
        swap(x1, x2);
        swap(y1, y2);
    }
    return ( (long long)x1 << 48 ) | ( (long long)y1 << 32 ) |
           ( (long long)x2 << 16 ) | (long long)y2;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<bool>> dot(N, vector<bool>(N, false));
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        dot[x][y] = true;
    }

    unordered_set<long long> edges;
    edges.reserve(20000);
    edges.max_load_factor(0.7);

    struct Op { int a[8]; };
    vector<Op> ops;
    ops.reserve(5000);

    bool updated = true;
    while (updated) {
        updated = false;
        for (int x = 0; x < N - 1; ++x) {
            for (int y = 0; y < N - 1; ++y) {
                bool b00 = dot[x][y];
                bool b10 = dot[x + 1][y];
                bool b11 = dot[x + 1][y + 1];
                bool b01 = dot[x][y + 1];
                int c = (int)b00 + (int)b10 + (int)b11 + (int)b01;
                if (c != 3) continue;

                int m = -1;
                if (!b00) m = 0;
                else if (!b10) m = 1;
                else if (!b11) m = 2;
                else m = 3;

                struct Pt { int x, y; };
                Pt v[4] = { {x, y}, {x + 1, y}, {x + 1, y + 1}, {x, y + 1} };
                Pt p1 = v[m];
                if (dot[p1.x][p1.y]) continue; // should not happen, but safe
                Pt p2 = v[(m + 1) % 4];
                Pt p3 = v[(m + 2) % 4];
                Pt p4 = v[(m + 3) % 4];

                long long e1 = edgeKey(p1.x, p1.y, p2.x, p2.y);
                long long e2 = edgeKey(p2.x, p2.y, p3.x, p3.y);
                long long e3 = edgeKey(p3.x, p3.y, p4.x, p4.y);
                long long e4 = edgeKey(p4.x, p4.y, p1.x, p1.y);

                if (edges.count(e1) || edges.count(e2) || edges.count(e3) || edges.count(e4))
                    continue;

                edges.insert(e1);
                edges.insert(e2);
                edges.insert(e3);
                edges.insert(e4);
                dot[p1.x][p1.y] = true;

                Op op;
                op.a[0] = p1.x; op.a[1] = p1.y;
                op.a[2] = p2.x; op.a[3] = p2.y;
                op.a[4] = p3.x; op.a[5] = p3.y;
                op.a[6] = p4.x; op.a[7] = p4.y;
                ops.push_back(op);

                updated = true;
            }
        }
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        for (int i = 0; i < 8; ++i) {
            if (i) cout << ' ';
            cout << op.a[i];
        }
        cout << '\n';
    }

    return 0;
}