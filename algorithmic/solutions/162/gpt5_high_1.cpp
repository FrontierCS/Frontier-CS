#include <bits/stdc++.h>
using namespace std;

struct Pos {
    int x, y;
    inline bool operator==(const Pos& other) const { return x == other.x && y == other.y; }
};

struct Edge {
    Pos parent;
    Pos child;
};

static const int N = 30;
int b[N][N];

struct SwapOp {
    int x1, y1, x2, y2;
};

inline void add_edge_unique(Edge* arr, int &m, const Pos& parent, const Pos& child) {
    for (int i = 0; i < m; ++i) {
        if (arr[i].parent.x == parent.x && arr[i].parent.y == parent.y &&
            arr[i].child.x == child.x && arr[i].child.y == child.y) return;
    }
    arr[m++] = {parent, child};
}

inline void collect_incident_edges(const Pos& v, Edge* arr, int &m) {
    int x = v.x, y = v.y;
    if (x < N - 1) {
        add_edge_unique(arr, m, v, Pos{x + 1, y});
        add_edge_unique(arr, m, v, Pos{x + 1, y + 1});
    }
    if (x > 0) {
        if (y - 1 >= 0) add_edge_unique(arr, m, Pos{x - 1, y - 1}, v);
        if (y <= x - 1) add_edge_unique(arr, m, Pos{x - 1, y}, v);
    }
}

inline int get_val_after(const Pos& w, const Pos& p, const Pos& q, int vp, int vq) {
    if (w.x == p.x && w.y == p.y) return vq;
    if (w.x == q.x && w.y == q.y) return vp;
    return b[w.x][w.y];
}

inline int delta_swap(const Pos& p, const Pos& q) {
    Edge edges[12];
    int m = 0;
    collect_incident_edges(p, edges, m);
    collect_incident_edges(q, edges, m);
    int vp = b[p.x][p.y], vq = b[q.x][q.y];

    int e_old = 0, e_new = 0;
    for (int i = 0; i < m; ++i) {
        const Pos& par = edges[i].parent;
        const Pos& chi = edges[i].child;
        int vp_old = b[par.x][par.y];
        int vc_old = b[chi.x][chi.y];
        if (vp_old > vc_old) ++e_old;

        int vp_new = get_val_after(par, p, q, vp, vq);
        int vc_new = get_val_after(chi, p, q, vp, vq);
        if (vp_new > vc_new) ++e_new;
    }
    return e_old - e_new;
}

inline void do_swap(Pos p, Pos q, vector<SwapOp>& ops) {
    swap(b[p.x][p.y], b[q.x][q.y]);
    ops.push_back({p.x, p.y, q.x, q.y});
}

inline int count_violations() {
    int E = 0;
    for (int x = 0; x < N - 1; ++x) {
        for (int y = 0; y <= x; ++y) {
            int v = b[x][y];
            if (v > b[x + 1][y]) ++E;
            if (v > b[x + 1][y + 1]) ++E;
        }
    }
    return E;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            cin >> b[x][y];
        }
    }

    vector<SwapOp> ops;
    ops.reserve(10000);

    // Precompute edge lists
    vector<pair<Pos, Pos>> edgesDown;
    edgesDown.reserve(N * (N - 1));
    for (int x = 0; x < N - 1; ++x) {
        for (int y = 0; y <= x; ++y) {
            edgesDown.push_back({Pos{x, y}, Pos{x + 1, y}});
            edgesDown.push_back({Pos{x, y}, Pos{x + 1, y + 1}});
        }
    }
    vector<pair<Pos, Pos>> edgesHoriz;
    edgesHoriz.reserve(N * (N - 1) / 2);
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y < x; ++y) {
            edgesHoriz.push_back({Pos{x, y}, Pos{x, y + 1}});
        }
    }

    const int KMAX = 10000;
    const int BUDGET1 = 8000;

    // Stage 1: Sink larger values down like heapify (greedy)
    for (int x = 0; x < N - 1 && (int)ops.size() < BUDGET1; ++x) {
        for (int y = 0; y <= x && (int)ops.size() < BUDGET1; ++y) {
            int cx = x, cy = y;
            while (cx < N - 1 && (int)ops.size() < BUDGET1) {
                int v = b[cx][cy];
                int c1 = b[cx + 1][cy];
                int c2 = b[cx + 1][cy + 1];
                if (v <= c1 && v <= c2) break;
                if (c1 <= c2) {
                    do_swap(Pos{cx, cy}, Pos{cx + 1, cy}, ops);
                    ++cx; // cy unchanged
                } else {
                    do_swap(Pos{cx, cy}, Pos{cx + 1, cy + 1}, ops);
                    ++cx;
                    ++cy;
                }
            }
        }
    }

    // Stage 2: Local hill-climbing on violations
    while ((int)ops.size() < KMAX) {
        int bestDelta = 0;
        Pos bp{ -1, -1 }, bq{ -1, -1 };

        // Consider only violating parent-child pairs first (both diagonals)
        for (const auto& e : edgesDown) {
            const Pos& p = e.first;
            const Pos& q = e.second;
            if (b[p.x][p.y] > b[q.x][q.y]) {
                int d = delta_swap(p, q);
                if (d > bestDelta) {
                    bestDelta = d;
                    bp = p;
                    bq = q;
                }
            }
        }

        if (bestDelta <= 0) {
            // Consider horizontal neighbors
            for (const auto& e : edgesHoriz) {
                const Pos& p = e.first;
                const Pos& q = e.second;
                int d = delta_swap(p, q);
                if (d > bestDelta) {
                    bestDelta = d;
                    bp = p;
                    bq = q;
                }
            }
        }

        if (bestDelta <= 0) break; // no improving move

        do_swap(bp, bq, ops);
        if ((int)ops.size() >= KMAX) break;
    }

    // Output
    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op.x1 << ' ' << op.y1 << ' ' << op.x2 << ' ' << op.y2 << '\n';
    }
    return 0;
}