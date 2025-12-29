#include <bits/stdc++.h>
using namespace std;

struct Rect {
    int a, b, c, d;
};

struct Split {
    bool ok = false;
    bool vertical = true;
    int cut = -1;
    vector<int> left, right;
    long double score = 1e100L;
};

static inline long long isum(const vector<long long>& r, const vector<int>& ids) {
    long long s = 0;
    for (int id : ids) s += r[id];
    return s;
}

Split compute_vertical(const vector<int>& ids, int lx, int ly, int rx, int ry,
                       const vector<int>& x, const vector<int>& y, const vector<long long>& r) {
    Split best;
    best.vertical = true;
    int W = rx - lx, H = ry - ly;
    if (W <= 1) return best;

    vector<int> ord = ids;
    sort(ord.begin(), ord.end(), [&](int a, int b) {
        if (x[a] != x[b]) return x[a] < x[b];
        return y[a] < y[b];
    });

    const int m = (int)ord.size();
    vector<long long> pref(m + 1, 0);
    for (int i = 0; i < m; i++) pref[i + 1] = pref[i] + r[ord[i]];
    long long totalR = pref[m];
    long long A = 1LL * W * H;

    for (int k = 1; k < m; k++) {
        int xL = x[ord[k - 1]];
        int xR = x[ord[k]];
        int lo = max(lx + 1, xL + 1);
        int hi = min(rx - 1, xR);
        if (lo > hi) continue;

        long long sumL = pref[k];

        long long targetW = (long long)(((__int128)W * sumL + totalR / 2) / totalR);
        int cand = lx + (int)targetW;
        if (cand < lo) cand = lo;
        if (cand > hi) cand = hi;

        long long actualL = 1LL * (cand - lx) * H;
        long double desiredL = (long double)A * (long double)sumL / (long double)totalR;
        long double diff = fabsl((long double)actualL - desiredL) / (long double)A;
        long double balance = fabsl((long double)sumL * 2.0L - (long double)totalR) / (long double)totalR;
        long double score = diff + 0.02L * balance;

        if (score < best.score) {
            best.ok = true;
            best.score = score;
            best.cut = cand;
            best.left.assign(ord.begin(), ord.begin() + k);
            best.right.assign(ord.begin() + k, ord.end());
        }
    }
    return best;
}

Split compute_horizontal(const vector<int>& ids, int lx, int ly, int rx, int ry,
                         const vector<int>& x, const vector<int>& y, const vector<long long>& r) {
    Split best;
    best.vertical = false;
    int W = rx - lx, H = ry - ly;
    if (H <= 1) return best;

    vector<int> ord = ids;
    sort(ord.begin(), ord.end(), [&](int a, int b) {
        if (y[a] != y[b]) return y[a] < y[b];
        return x[a] < x[b];
    });

    const int m = (int)ord.size();
    vector<long long> pref(m + 1, 0);
    for (int i = 0; i < m; i++) pref[i + 1] = pref[i] + r[ord[i]];
    long long totalR = pref[m];
    long long A = 1LL * W * H;

    for (int k = 1; k < m; k++) {
        int yL = y[ord[k - 1]];
        int yR = y[ord[k]];
        int lo = max(ly + 1, yL + 1);
        int hi = min(ry - 1, yR);
        if (lo > hi) continue;

        long long sumL = pref[k];

        long long targetH = (long long)(((__int128)H * sumL + totalR / 2) / totalR);
        int cand = ly + (int)targetH;
        if (cand < lo) cand = lo;
        if (cand > hi) cand = hi;

        long long actualL = 1LL * W * (cand - ly);
        long double desiredL = (long double)A * (long double)sumL / (long double)totalR;
        long double diff = fabsl((long double)actualL - desiredL) / (long double)A;
        long double balance = fabsl((long double)sumL * 2.0L - (long double)totalR) / (long double)totalR;
        long double score = diff + 0.02L * balance;

        if (score < best.score) {
            best.ok = true;
            best.score = score;
            best.cut = cand;
            best.left.assign(ord.begin(), ord.begin() + k);
            best.right.assign(ord.begin() + k, ord.end());
        }
    }
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> x(n), y(n);
    vector<long long> r(n);
    for (int i = 0; i < n; i++) cin >> x[i] >> y[i] >> r[i];

    vector<Rect> ans(n);

    function<void(const vector<int>&, int, int, int, int)> solve =
        [&](const vector<int>& ids, int lx, int ly, int rx, int ry) {
            if (ids.size() == 1) {
                int id = ids[0];
                ans[id] = Rect{lx, ly, rx, ry};
                return;
            }

            Split sv = compute_vertical(ids, lx, ly, rx, ry, x, y, r);
            Split sh = compute_horizontal(ids, lx, ly, rx, ry, x, y, r);

            Split chosen;
            if (sv.ok && sh.ok) {
                // Prefer the smaller score; tie-break by larger region dimension
                if (sv.score < sh.score) chosen = sv;
                else if (sh.score < sv.score) chosen = sh;
                else {
                    int W = rx - lx, H = ry - ly;
                    chosen = (W >= H) ? sv : sh;
                }
            } else if (sv.ok) chosen = sv;
            else if (sh.ok) chosen = sh;
            else {
                // Should not happen; fallback: split by count in a feasible direction if possible.
                int W = rx - lx, H = ry - ly;
                if (W > 1) {
                    vector<int> ord = ids;
                    sort(ord.begin(), ord.end(), [&](int a, int b) {
                        if (x[a] != x[b]) return x[a] < x[b];
                        return y[a] < y[b];
                    });
                    int m = (int)ord.size();
                    int k = m / 2;
                    int xL = x[ord[k - 1]];
                    int xR = x[ord[k]];
                    int lo = max(lx + 1, xL + 1);
                    int hi = min(rx - 1, xR);
                    int cut = (lo <= hi) ? lo : (lx + rx) / 2;
                    if (cut <= lx) cut = lx + 1;
                    if (cut >= rx) cut = rx - 1;
                    vector<int> left(ord.begin(), ord.begin() + k), right(ord.begin() + k, ord.end());
                    solve(left, lx, ly, cut, ry);
                    solve(right, cut, ly, rx, ry);
                } else {
                    vector<int> ord = ids;
                    sort(ord.begin(), ord.end(), [&](int a, int b) {
                        if (y[a] != y[b]) return y[a] < y[b];
                        return x[a] < x[b];
                    });
                    int m = (int)ord.size();
                    int k = m / 2;
                    int yL = y[ord[k - 1]];
                    int yR = y[ord[k]];
                    int lo = max(ly + 1, yL + 1);
                    int hi = min(ry - 1, yR);
                    int cut = (lo <= hi) ? lo : (ly + ry) / 2;
                    if (cut <= ly) cut = ly + 1;
                    if (cut >= ry) cut = ry - 1;
                    vector<int> left(ord.begin(), ord.begin() + k), right(ord.begin() + k, ord.end());
                    solve(left, lx, ly, rx, cut);
                    solve(right, lx, cut, rx, ry);
                }
                return;
            }

            if (chosen.vertical) {
                int cut = chosen.cut;
                solve(chosen.left, lx, ly, cut, ry);
                solve(chosen.right, cut, ly, rx, ry);
            } else {
                int cut = chosen.cut;
                solve(chosen.left, lx, ly, rx, cut);
                solve(chosen.right, lx, cut, rx, ry);
            }
        };

    vector<int> all(n);
    iota(all.begin(), all.end(), 0);
    solve(all, 0, 0, 10000, 10000);

    for (int i = 0; i < n; i++) {
        cout << ans[i].a << ' ' << ans[i].b << ' ' << ans[i].c << ' ' << ans[i].d << "\n";
    }
    return 0;
}