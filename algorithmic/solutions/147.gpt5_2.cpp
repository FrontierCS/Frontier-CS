#include <bits/stdc++.h>
using namespace std;

struct Company {
    int idx;
    int x, y;
    long long r;
};

struct Group {
    int X; // unique x coordinate
    vector<int> members; // original indices sorted by y
    vector<int> yvals;   // y coordinates sorted
    vector<int> h;       // horizontal boundaries between members (size m-1)
    vector<int> heights; // heights per member (size m)
    int wmin = 1, wmax = 1; // allowed width range for this stripe
    vector<double> cost; // precomputed cost per width (index by w - wmin)
};

static inline double costFunc(long long rVal, long long sVal) {
    long long a = rVal < sVal ? rVal : sVal;
    long long b = rVal > sVal ? rVal : sVal;
    double ratio = 1.0 - (double)a / (double)b;
    return ratio * ratio;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<Company> comps(n);
    for (int i = 0; i < n; ++i) {
        cin >> comps[i].x >> comps[i].y >> comps[i].r;
        comps[i].idx = i;
    }

    // Sort companies by x then by y
    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b){
        if (comps[a].x != comps[b].x) return comps[a].x < comps[b].x;
        return comps[a].y < comps[b].y;
    });

    // Build groups by unique x
    vector<Group> groups;
    for (int id : ord) {
        if (groups.empty() || groups.back().X != comps[id].x) {
            Group g;
            g.X = comps[id].x;
            groups.push_back(move(g));
        }
        groups.back().members.push_back(id);
    }

    int M = (int)groups.size();

    // For each group, sort members by y and compute fixed horizontal boundaries (midpoints)
    for (int gi = 0; gi < M; ++gi) {
        Group &g = groups[gi];
        vector<pair<int,int>> arr;
        arr.reserve(g.members.size());
        for (int id : g.members) arr.push_back({comps[id].y, id});
        sort(arr.begin(), arr.end());
        g.members.clear();
        g.yvals.clear();
        for (auto &p : arr) {
            g.yvals.push_back(p.first);
            g.members.push_back(p.second);
        }
        int m = (int)g.members.size();
        g.h.clear();
        g.heights.clear();
        if (m == 1) {
            g.heights.push_back(10000);
        } else {
            g.h.resize(m - 1);
            for (int k = 1; k <= m - 1; ++k) {
                int y1 = g.yvals[k - 1];
                int y2 = g.yvals[k];
                int hk = (y1 + y2 + 1) / 2;
                if (hk < y1 + 1) hk = y1 + 1;
                if (hk > y2) hk = y2;
                g.h[k - 1] = hk;
            }
            // compute heights from boundaries
            g.heights.resize(m);
            g.heights[0] = g.h[0] - 0;
            for (int k = 1; k <= m - 2; ++k) {
                g.heights[k] = g.h[k] - g.h[k - 1];
            }
            g.heights[m - 1] = 10000 - g.h[m - 2];
        }
    }

    // Unique X list
    vector<int> Xs(M);
    for (int i = 0; i < M; ++i) Xs[i] = groups[i].X;

    // Compute width ranges per group
    if (M == 1) {
        groups[0].wmin = 10000;
        groups[0].wmax = 10000;
    } else {
        for (int j = 0; j < M; ++j) {
            if (j == 0) {
                groups[j].wmin = Xs[0] + 1;
                groups[j].wmax = Xs[1];
            } else if (j == M - 1) {
                groups[j].wmin = 10000 - Xs[M - 1];
                groups[j].wmax = 10000 - (Xs[M - 2] + 1);
            } else {
                groups[j].wmin = 1;
                groups[j].wmax = Xs[j + 1] - Xs[j - 1] - 1;
            }
            if (groups[j].wmin < 1) groups[j].wmin = 1;
            if (groups[j].wmax < groups[j].wmin) groups[j].wmax = groups[j].wmin;
        }
    }

    // Precompute cost per group for all widths in its possible range, using fixed heights
    for (int j = 0; j < M; ++j) {
        Group &g = groups[j];
        int wmin = g.wmin, wmax = g.wmax;
        int len = wmax - wmin + 1;
        g.cost.assign(len, 0.0);
        for (int w = wmin; w <= wmax; ++w) {
            double sumCost = 0.0;
            for (int t = 0; t < (int)g.members.size(); ++t) {
                long long s = 1LL * w * g.heights[t];
                sumCost += costFunc(comps[g.members[t]].r, s);
            }
            g.cost[w - wmin] = sumCost;
        }
    }

    // Vertical DP across groups to choose boundaries
    vector<int> L, R;
    vector<int> rangeLen;
    if (M >= 2) {
        L.resize(M, 0);
        R.resize(M, 0);
        rangeLen.resize(M, 0);
        for (int k = 1; k <= M - 1; ++k) {
            L[k] = Xs[k - 1] + 1;
            R[k] = Xs[k];
            rangeLen[k] = R[k] - L[k] + 1;
        }
    }

    vector<int> boundaries; // b_k for k=1..M-1 (size M-1)
    if (M == 1) {
        boundaries.clear();
    } else {
        const double INF = 1e100;
        vector<double> dpPrev(rangeLen[1], INF), dpCurr;
        vector<vector<int>> parent(M); // parent[k][xiIndex] = yiIndex for k=2..M-1
        // Base step k=1: dp for first boundary b1
        for (int xi = 0; xi < rangeLen[1]; ++xi) {
            int xVal = L[1] + xi;
            int w0 = xVal; // w for group 0
            dpPrev[xi] = groups[0].cost[w0 - groups[0].wmin];
        }
        // Subsequent steps k = 2..M-1
        for (int k = 2; k <= M - 1; ++k) {
            dpCurr.assign(rangeLen[k], INF);
            parent[k].assign(rangeLen[k], -1);
            // group j = k-1
            Group &gj = groups[k - 1];
            int wmin = gj.wmin;
            for (int xi = 0; xi < rangeLen[k]; ++xi) {
                int xVal = L[k] + xi;
                double best = INF;
                int bestY = -1;
                for (int yi = 0; yi < rangeLen[k - 1]; ++yi) {
                    int yVal = L[k - 1] + yi;
                    int w = xVal - yVal;
                    // w should be within [wmin, wmax] by construction, but clamp check
                    if (w < gj.wmin || w > gj.wmax) continue;
                    double c = dpPrev[yi] + gj.cost[w - wmin];
                    if (c < best) {
                        best = c;
                        bestY = yi;
                    }
                }
                dpCurr[xi] = best;
                parent[k][xi] = bestY;
            }
            dpPrev.swap(dpCurr);
        }
        // Final selection includes last group's width w_last = 10000 - b_{M-1}
        double bestAll = INF;
        int bestXidx = -1;
        Group &gLast = groups[M - 1];
        for (int xi = 0; xi < rangeLen[M - 1]; ++xi) {
            int xVal = L[M - 1] + xi;
            int wLast = 10000 - xVal;
            if (wLast < gLast.wmin || wLast > gLast.wmax) continue;
            double c = dpPrev[xi] + gLast.cost[wLast - gLast.wmin];
            if (c < bestAll) {
                bestAll = c;
                bestXidx = xi;
            }
        }
        // Reconstruct boundaries
        boundaries.assign(M - 1, 0);
        int idx = bestXidx;
        boundaries[M - 2] = L[M - 1] + idx; // b_{M-1}
        for (int k = M - 1; k >= 2; --k) {
            int pidx = parent[k][idx];
            boundaries[k - 2] = L[k - 1] + pidx; // b_{k-1}
            idx = pidx;
        }
    }

    // Prepare final rectangles for each company
    vector<int> a(n), b(n), c(n), d(n);
    auto set_rect_group = [&](int gi, int left, int right) {
        Group &g = groups[gi];
        int m = (int)g.members.size();
        if (m == 1) {
            int id = g.members[0];
            a[id] = left;
            b[id] = 0;
            c[id] = right;
            d[id] = 10000;
        } else {
            // Y boundaries from h
            for (int t = 0; t < m; ++t) {
                int bottom = (t == 0 ? 0 : g.h[t - 1]);
                int top = (t == m - 1 ? 10000 : g.h[t]);
                int id = g.members[t];
                a[id] = left;
                b[id] = bottom;
                c[id] = right;
                d[id] = top;
            }
        }
    };

    if (M == 1) {
        set_rect_group(0, 0, 10000);
    } else {
        // compute stripe bounds per group using boundaries
        // Group 0: [0, b1]
        set_rect_group(0, 0, boundaries[0]);
        for (int j = 1; j <= M - 2; ++j) {
            set_rect_group(j, boundaries[j - 1], boundaries[j]);
        }
        // Last group: [b_{M-1}, 10000]
        set_rect_group(M - 1, boundaries[M - 2], 10000);
    }

    // Output rectangles in original company order
    for (int i = 0; i < n; ++i) {
        cout << a[i] << ' ' << b[i] << ' ' << c[i] << ' ' << d[i] << '\n';
    }
    return 0;
}