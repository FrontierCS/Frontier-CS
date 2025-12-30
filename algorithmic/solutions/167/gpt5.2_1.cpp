#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
};
struct Rect {
    int x1, x2, y1, y2; // inclusive, must satisfy x1 < x2, y1 < y2
};

static inline int clampi(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static inline void normalize_rect(Rect &r, int MAXC = 100000) {
    r.x1 = clampi(r.x1, 0, MAXC);
    r.x2 = clampi(r.x2, 0, MAXC);
    if (r.x1 > r.x2) swap(r.x1, r.x2);
    if (r.x1 == r.x2) {
        if (r.x2 < MAXC) r.x2++;
        else r.x1--;
    }
    r.x1 = clampi(r.x1, 0, MAXC);
    r.x2 = clampi(r.x2, 0, MAXC);
    if (r.x1 == r.x2) { // extremely unlikely
        r.x1 = max(0, MAXC - 1);
        r.x2 = MAXC;
    }

    r.y1 = clampi(r.y1, 0, MAXC);
    r.y2 = clampi(r.y2, 0, MAXC);
    if (r.y1 > r.y2) swap(r.y1, r.y2);
    if (r.y1 == r.y2) {
        if (r.y2 < MAXC) r.y2++;
        else r.y1--;
    }
    r.y1 = clampi(r.y1, 0, MAXC);
    r.y2 = clampi(r.y2, 0, MAXC);
    if (r.y1 == r.y2) {
        r.y1 = max(0, MAXC - 1);
        r.y2 = MAXC;
    }

    if (r.x1 >= r.x2) {
        r.x1 = max(0, r.x2 - 1);
        if (r.x1 == r.x2) r.x2 = min(MAXC, r.x1 + 1);
    }
    if (r.y1 >= r.y2) {
        r.y1 = max(0, r.y2 - 1);
        if (r.y1 == r.y2) r.y2 = min(MAXC, r.y1 + 1);
    }
}

static inline int eval_rect(const Rect &r, const vector<Point> &mack, const vector<Point> &sard) {
    int a = 0, b = 0;
    for (const auto &p : mack) {
        if (r.x1 <= p.x && p.x <= r.x2 && r.y1 <= p.y && p.y <= r.y2) a++;
    }
    for (const auto &p : sard) {
        if (r.x1 <= p.x && p.x <= r.x2 && r.y1 <= p.y && p.y <= r.y2) b++;
    }
    return a - b;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<Point> mack(N), sard(N);
    for (int i = 0; i < 2 * N; i++) {
        int x, y;
        cin >> x >> y;
        if (i < N) mack[i] = {x, y};
        else sard[i - N] = {x, y};
    }

    const int MAXC = 100000;
    const int W = 400, H = 400;

    vector<int> xs(W + 1), ys(H + 1);
    for (int i = 0; i <= W; i++) xs[i] = (int)((long long)(MAXC + 1) * i / W);
    for (int i = 0; i <= H; i++) ys[i] = (int)((long long)(MAXC + 1) * i / H);

    auto xidx = [&](int x) -> int { return (int)((long long)x * W / (MAXC + 1)); };
    auto yidx = [&](int y) -> int { return (int)((long long)y * H / (MAXC + 1)); };

    vector<int> mat(W * H, 0);
    for (auto &p : mack) {
        int ix = xidx(p.x), iy = yidx(p.y);
        mat[iy * W + ix] += 1;
    }
    for (auto &p : sard) {
        int ix = xidx(p.x), iy = yidx(p.y);
        mat[iy * W + ix] -= 1;
    }

    // Max-sum sub-rectangle via O(H^2*W) using Kadane on columns.
    long long bestSum = LLONG_MIN;
    int bestTop = 0, bestBot = 0, bestL = 0, bestR = 0;
    vector<int> colSum(W);

    for (int top = 0; top < H; top++) {
        fill(colSum.begin(), colSum.end(), 0);
        for (int bot = top; bot < H; bot++) {
            const int rowOff = bot * W;
            for (int c = 0; c < W; c++) colSum[c] += mat[rowOff + c];

            long long cur = 0;
            int curL = 0;
            for (int c = 0; c < W; c++) {
                if (cur <= 0) {
                    cur = colSum[c];
                    curL = c;
                } else {
                    cur += colSum[c];
                }
                if (cur > bestSum) {
                    bestSum = cur;
                    bestTop = top;
                    bestBot = bot;
                    bestL = curL;
                    bestR = c;
                }
            }
        }
    }

    Rect fromGrid;
    fromGrid.x1 = xs[bestL];
    fromGrid.x2 = xs[bestR + 1] - 1;
    fromGrid.y1 = ys[bestTop];
    fromGrid.y2 = ys[bestBot + 1] - 1;
    normalize_rect(fromGrid, MAXC);

    Rect bestRect = {0, MAXC, 0, MAXC};
    int bestVal = eval_rect(bestRect, mack, sard);

    {
        int val = eval_rect(fromGrid, mack, sard);
        if (val > bestVal) {
            bestVal = val;
            bestRect = fromGrid;
        }
    }

    uint64_t seed = (uint64_t)chrono::steady_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);

    auto rand_int = [&](int lo, int hi) -> int {
        uniform_int_distribution<int> dist(lo, hi);
        return dist(rng);
    };

    auto make_rect_centered = [&](int cx, int cy, int w, int h) -> Rect {
        Rect r;
        int hw = w / 2;
        int hh = h / 2;
        r.x1 = cx - hw;
        r.x2 = cx + (w - hw - 1);
        r.y1 = cy - hh;
        r.y2 = cy + (h - hh - 1);
        normalize_rect(r, MAXC);
        return r;
    };

    auto start = chrono::steady_clock::now();
    const double TL = 1.85; // seconds

    while (true) {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (elapsed > TL) break;

        int mode = rand_int(0, 2);

        Rect cur;
        if (mode == 0) {
            const auto &p = mack[rand_int(0, N - 1)];
            int w = rand_int(400, 60000);
            int h = rand_int(400, 60000);
            int cx = p.x + rand_int(-2000, 2000);
            int cy = p.y + rand_int(-2000, 2000);
            cx = clampi(cx, 0, MAXC);
            cy = clampi(cy, 0, MAXC);
            cur = make_rect_centered(cx, cy, w, h);
        } else if (mode == 1) {
            int w = bestRect.x2 - bestRect.x1 + 1;
            int h = bestRect.y2 - bestRect.y1 + 1;
            int cx = (bestRect.x1 + bestRect.x2) / 2 + rand_int(-4000, 4000);
            int cy = (bestRect.y1 + bestRect.y2) / 2 + rand_int(-4000, 4000);
            w = clampi(w + rand_int(-8000, 8000), 200, 100001);
            h = clampi(h + rand_int(-8000, 8000), 200, 100001);
            cx = clampi(cx, 0, MAXC);
            cy = clampi(cy, 0, MAXC);
            cur = make_rect_centered(cx, cy, w, h);
        } else {
            // Use bounding box of 2 random mackerels with margin
            const auto &p1 = mack[rand_int(0, N - 1)];
            const auto &p2 = mack[rand_int(0, N - 1)];
            int x1 = min(p1.x, p2.x), x2 = max(p1.x, p2.x);
            int y1 = min(p1.y, p2.y), y2 = max(p1.y, p2.y);
            int mx = rand_int(0, 6000), my = rand_int(0, 6000);
            cur = {x1 - mx, x2 + mx, y1 - my, y2 + my};
            normalize_rect(cur, MAXC);
        }

        int curVal = eval_rect(cur, mack, sard);
        if (curVal > bestVal) {
            bestVal = curVal;
            bestRect = cur;
        }

        // Small hill-climb around current rectangle
        for (int it = 0; it < 20; it++) {
            Rect nxt = cur;
            int side = rand_int(0, 3);
            int delta = rand_int(-3000, 3000);
            if (side == 0) nxt.x1 += delta;
            else if (side == 1) nxt.x2 += delta;
            else if (side == 2) nxt.y1 += delta;
            else nxt.y2 += delta;
            normalize_rect(nxt, MAXC);

            int v = eval_rect(nxt, mack, sard);
            if (v >= curVal) {
                cur = nxt;
                curVal = v;
                if (curVal > bestVal) {
                    bestVal = curVal;
                    bestRect = cur;
                }
            }
        }
    }

    // Output as a simple rectangle polygon
    int m = 4;
    cout << m << "\n";
    cout << bestRect.x1 << " " << bestRect.y1 << "\n";
    cout << bestRect.x2 << " " << bestRect.y1 << "\n";
    cout << bestRect.x2 << " " << bestRect.y2 << "\n";
    cout << bestRect.x1 << " " << bestRect.y2 << "\n";
    return 0;
}