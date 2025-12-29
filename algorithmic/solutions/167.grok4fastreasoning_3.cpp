#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y, v, yr;
};

struct Node {
    int total, pref, suff, sub, time;
};

int count_mack(int xl, int xr, int yl, int yr, const vector<pair<int, int>>& mackk) {
    int cnt = 0;
    for (auto& p : mackk) {
        int xx = p.first, yy = p.second;
        if (xx >= xl && xx <= xr && yy >= yl && yy <= yr) ++cnt;
    }
    return cnt;
}

int count_sard(int xl, int xr, int yl, int yr, const vector<pair<int, int>>& sardd) {
    int cnt = 0;
    for (auto& p : sardd) {
        int xx = p.first, yy = p.second;
        if (xx >= xl && xx <= xr && yy >= yl && yy <= yr) ++cnt;
    }
    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    cin >> N;
    vector<pair<int, int>> points(2 * N);
    for (int i = 0; i < 2 * N; ++i) {
        cin >> points[i].first >> points[i].second;
    }
    vector<pair<int, int>> mack(N), sard(N);
    for (int i = 0; i < N; ++i) mack[i] = points[i];
    for (int i = 0; i < N; ++i) sard[i] = points[N + i];
    vector<Point> allp(2 * N);
    for (int i = 0; i < N; ++i) {
        allp[i].x = mack[i].first;
        allp[i].y = mack[i].second;
        allp[i].v = 1;
    }
    for (int i = 0; i < N; ++i) {
        allp[N + i].x = sard[i].first;
        allp[N + i].y = sard[i].second;
        allp[N + i].v = -1;
    }
    sort(allp.begin(), allp.end(), [](const Point& a, const Point& b) {
        return a.x < b.x || (a.x == b.x && a.y < b.y);
    });
    set<int> yset;
    for (auto& p : allp) yset.insert(p.y);
    vector<int> Y(yset.begin(), yset.end());
    int K = Y.size();
    auto get_yr = [&](int yy) -> int {
        return lower_bound(Y.begin(), Y.end(), yy) - Y.begin() + 1;
    };
    for (auto& p : allp) p.yr = get_yr(p.y);
    vector<Node> tree(4 * (K + 5));
    int global_ver = -1;
    auto update_func = [&](auto&& self, int pos, int addval, int curver, int node, int nl, int nr) -> void {
        if (nl == nr) {
            int curr = (tree[node].time >= curver ? tree[node].total : 0);
            int newt = curr + addval;
            tree[node].total = newt;
            tree[node].pref = newt;
            tree[node].suff = newt;
            tree[node].sub = newt;
            tree[node].time = curver;
            return;
        }
        int mid = (nl + nr) / 2;
        if (pos <= mid) self(self, pos, addval, curver, node * 2, nl, mid);
        else self(self, pos, addval, curver, node * 2 + 1, mid + 1, nr);
        Node le, ri;
        bool lvalid = (tree[node * 2].time >= curver);
        if (lvalid) {
            le.total = tree[node * 2].total;
            le.pref = tree[node * 2].pref;
            le.suff = tree[node * 2].suff;
            le.sub = tree[node * 2].sub;
        } else {
            le.total = 0; le.pref = 0; le.suff = 0; le.sub = 0;
        }
        bool rvalid = (tree[node * 2 + 1].time >= curver);
        if (rvalid) {
            ri.total = tree[node * 2 + 1].total;
            ri.pref = tree[node * 2 + 1].pref;
            ri.suff = tree[node * 2 + 1].suff;
            ri.sub = tree[node * 2 + 1].sub;
        } else {
            ri.total = 0; ri.pref = 0; ri.suff = 0; ri.sub = 0;
        }
        Node res;
        res.total = le.total + ri.total;
        res.pref = max(le.pref, le.total + ri.pref);
        res.suff = max(ri.suff, ri.total + le.suff);
        res.sub = max({le.sub, ri.sub, le.suff + ri.pref});
        tree[node].total = res.total;
        tree[node].pref = res.pref;
        tree[node].suff = res.suff;
        tree[node].sub = res.sub;
        tree[node].time = curver;
    };
    int max_rect_profit = 0;
    int bestL = -1, bestR = -1;
    global_ver = 0;
    for (int L = 0; L < 2 * N; ++L) {
        ++global_ver;
        for (int R = L; R < 2 * N; ++R) {
            update_func(update_func, allp[R].yr, allp[R].v, global_ver, 1, 1, K);
            int cursub = (tree[1].time >= global_ver ? tree[1].sub : 0);
            int prof = max(0, cursub);
            if (prof > max_rect_profit) {
                max_rect_profit = prof;
                bestL = L;
                bestR = R;
            }
        }
    }
    bool use_rect = false;
    int rect_xl = 0, rect_xr = 0, rect_yl = 0, rect_yr = 0;
    int rect_profit = 0;
    if (bestL != -1 && max_rect_profit > 0) {
        vector<pair<int, int>> range_points;
        for (int i = bestL; i <= bestR; ++i) {
            range_points.emplace_back(allp[i].y, allp[i].v);
        }
        sort(range_points.begin(), range_points.end());
        int nnum = range_points.size();
        vector<int> pref(nnum + 1, 0);
        for (int i = 1; i <= nnum; ++i) {
            pref[i] = pref[i - 1] + range_points[i - 1].second;
        }
        int maxsub = INT_MIN / 2;
        int bs = -1, be = -1;
        for (int i = 0; i < nnum; ++i) {
            for (int j = i; j < nnum; ++j) {
                int s = pref[j + 1] - pref[i];
                if (s > maxsub) {
                    maxsub = s;
                    bs = i;
                    be = j;
                }
            }
        }
        rect_profit = max(0, maxsub);
        if (rect_profit > 0 && bs <= be && nnum > 0) {
            rect_yl = range_points[bs].first;
            rect_yr = range_points[be].first;
            rect_xl = allp[bestL].x;
            rect_xr = allp[bestR].x;
            if (rect_xl < rect_xr && rect_yl < rect_yr) {
                use_rect = true;
            }
        }
    }
    struct Rectt {
        int xl, xr, yl, yr, profit;
    };
    int max_single = INT_MIN / 2;
    Rectt best_small = {0, 1, 0, 1, 0};
    for (auto& pm : mack) {
        int px = pm.first, py = pm.second;
        vector<pair<int, int>> dirs = {{0, 1}, {0, -1}, {-1, 0}, {-1, -1}};
        for (auto& d : dirs) {
            int dx = d.first, dy = d.second;
            int nxl = px + dx, nxr = px + (dx >= 0 ? 1 : 0);
            int nyl = py + dy, nyr = py + (dy >= 0 ? 1 : 0);
            if (nxl < 0 || nxr > 100000 || nyl < 0 || nyr > 100000) continue;
            if (nxl >= nxr || nyl >= nyr) continue;
            int aa = count_mack(nxl, nxr, nyl, nyr, mack);
            int bb = count_sard(nxl, nxr, nyl, nyr, sard);
            int pr = aa - bb;
            if (pr > max_single) {
                max_single = pr;
                best_small = {nxl, nxr, nyl, nyr, pr};
            }
        }
    }
    int exl = 99999, exr = 100000, eyl = 99999, eyr = 100000;
    int ea = count_mack(exl, exr, eyl, eyr, mack);
    int eb = count_sard(exl, exr, eyl, eyr, sard);
    int empty_profit = ea - eb;
    Rectt chosen;
    int final_p = 0;
    if (use_rect && rect_profit >= max( max_single, empty_profit )) {
        chosen = {rect_xl, rect_xr, rect_yl, rect_yr, rect_profit};
        final_p = rect_profit;
    } else if (max_single >= max(0, empty_profit)) {
        chosen = best_small;
        final_p = max_single;
    } else {
        chosen = {exl, exr, eyl, eyr, empty_profit};
        final_p = empty_profit;
    }
    cout << 4 << '\n';
    cout << chosen.xl << " " << chosen.yl << '\n';
    cout << chosen.xr << " " << chosen.yl << '\n';
    cout << chosen.xr << " " << chosen.yr << '\n';
    cout << chosen.xl << " " << chosen.yr << '\n';
    return 0;
}