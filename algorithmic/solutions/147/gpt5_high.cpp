#include <bits/stdc++.h>
using namespace std;

struct Rect {
    int a, b, c, d; // [a,c) x [b,d)
};

static inline bool overlap1D(int a1, int b1, int a2, int b2) {
    return min(b1, b2) > max(a1, a2);
}

int allowedLeft(const vector<Rect>& R, int i) {
    const Rect &ri = R[i];
    int barrier = 0;
    for (int j = 0; j < (int)R.size(); ++j) if (j != i) {
        const Rect &rj = R[j];
        if (overlap1D(ri.b, ri.d, rj.b, rj.d) && rj.c <= ri.a) {
            barrier = max(barrier, rj.c);
        }
    }
    return ri.a - barrier;
}
int allowedRight(const vector<Rect>& R, int i) {
    const Rect &ri = R[i];
    int barrier = 10000;
    for (int j = 0; j < (int)R.size(); ++j) if (j != i) {
        const Rect &rj = R[j];
        if (overlap1D(ri.b, ri.d, rj.b, rj.d) && rj.a >= ri.c) {
            barrier = min(barrier, rj.a);
        }
    }
    return barrier - ri.c;
}
int allowedDown(const vector<Rect>& R, int i) {
    const Rect &ri = R[i];
    int barrier = 0;
    for (int j = 0; j < (int)R.size(); ++j) if (j != i) {
        const Rect &rj = R[j];
        if (overlap1D(ri.a, ri.c, rj.a, rj.c) && rj.d <= ri.b) {
            barrier = max(barrier, rj.d);
        }
    }
    return ri.b - barrier;
}
int allowedUp(const vector<Rect>& R, int i) {
    const Rect &ri = R[i];
    int barrier = 10000;
    for (int j = 0; j < (int)R.size(); ++j) if (j != i) {
        const Rect &rj = R[j];
        if (overlap1D(ri.a, ri.c, rj.a, rj.c) && rj.b >= ri.d) {
            barrier = min(barrier, rj.b);
        }
    }
    return barrier - ri.d;
}

void distributeAndExpandLR(vector<Rect>& R, int i, long long steps) {
    if (steps <= 0) return;
    int L = allowedLeft(R, i);
    int Rr = allowedRight(R, i);
    long long tot = min<long long>(steps, (long long)L + (long long)Rr);
    if (tot <= 0) return;
    // Distribute roughly evenly with preference to side with more room
    long long leftShare = min<long long>(L, tot / 2);
    long long rightShare = min<long long>(Rr, tot - leftShare);
    if (leftShare + rightShare < tot) {
        long long rem = tot - (leftShare + rightShare);
        long long canL = L - leftShare;
        long long giveL = min(canL, rem);
        leftShare += giveL;
        rem -= giveL;
        if (rem > 0) {
            long long canR = Rr - rightShare;
            long long giveR = min(canR, rem);
            rightShare += giveR;
            rem -= giveR;
        }
    }
    if (leftShare > 0) R[i].a -= (int)leftShare;
    if (rightShare > 0) R[i].c += (int)rightShare;
}

void distributeAndExpandUD(vector<Rect>& R, int i, long long steps) {
    if (steps <= 0) return;
    int D = allowedDown(R, i);
    int U = allowedUp(R, i);
    long long tot = min<long long>(steps, (long long)D + (long long)U);
    if (tot <= 0) return;
    long long downShare = min<long long>(D, tot / 2);
    long long upShare = min<long long>(U, tot - downShare);
    if (downShare + upShare < tot) {
        long long rem = tot - (downShare + upShare);
        long long canD = D - downShare;
        long long giveD = min(canD, rem);
        downShare += giveD;
        rem -= giveD;
        if (rem > 0) {
            long long canU = U - upShare;
            long long giveU = min(canU, rem);
            upShare += giveU;
            rem -= giveU;
        }
    }
    if (downShare > 0) R[i].b -= (int)downShare;
    if (upShare > 0) R[i].d += (int)upShare;
}

void expandRect(vector<Rect>& R, int i, long long target) {
    Rect &ri = R[i];
    // Phase 1: try to shape towards a square approx sqrt(target)
    int s = (int)floor(sqrt((long double)target));
    for (int iter = 0; iter < 2; ++iter) {
        long long area = 1LL * (ri.c - ri.a) * (ri.d - ri.b);
        if (area >= target) return;
        long long def = target - area;
        int h = ri.d - ri.b;
        int w = ri.c - ri.a;

        // Aim width towards s
        int L = allowedLeft(R, i);
        int Rr = allowedRight(R, i);
        int maxW = min(1 + L + Rr, s);
        if (maxW > w) {
            long long want = maxW - w;
            long long can = min(want, def / h);
            if (can > 0) {
                distributeAndExpandLR(R, i, can);
                area = 1LL * (ri.c - ri.a) * (ri.d - ri.b);
                def = target - area;
                if (def <= 0) return;
                h = ri.d - ri.b;
                w = ri.c - ri.a;
            }
        }

        // Aim height towards s
        int D = allowedDown(R, i);
        int U = allowedUp(R, i);
        int maxH = min(1 + D + U, s);
        if (maxH > h) {
            long long want = maxH - h;
            long long can = min(want, def / w);
            if (can > 0) {
                distributeAndExpandUD(R, i, can);
            }
        }
    }

    // Phase 2: fill remaining deficit greedily
    for (int iter = 0; iter < 1000; ++iter) {
        long long area = 1LL * (ri.c - ri.a) * (ri.d - ri.b);
        if (area >= target) break;
        long long def = target - area;
        int h = ri.d - ri.b;
        int w = ri.c - ri.a;

        int L = allowedLeft(R, i);
        int Rr = allowedRight(R, i);
        int D = allowedDown(R, i);
        int U = allowedUp(R, i);

        long long stepsLR = min<long long>((long long)L + (long long)Rr, def / max(1, h));
        long long stepsUD = min<long long>((long long)D + (long long)U, def / max(1, w));

        if (stepsLR <= 0 && stepsUD <= 0) break;

        if (stepsLR >= stepsUD) {
            if (stepsLR > 0) distributeAndExpandLR(R, i, stepsLR);
        } else {
            if (stepsUD > 0) distributeAndExpandUD(R, i, stepsUD);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    struct Company { int x, y; long long r; };
    vector<Company> comp(n);
    for (int i = 0; i < n; ++i) {
        cin >> comp[i].x >> comp[i].y >> comp[i].r;
    }

    vector<Rect> rects(n);
    for (int i = 0; i < n; ++i) {
        int x = comp[i].x, y = comp[i].y;
        rects[i] = Rect{x, y, x + 1, y + 1};
    }

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        return comp[a].r > comp[b].r; // larger first
    });

    for (int idx : order) {
        expandRect(rects, idx, comp[idx].r);
    }

    for (int i = 0; i < n; ++i) {
        // Clamp for safety
        rects[i].a = max(0, min(10000, rects[i].a));
        rects[i].b = max(0, min(10000, rects[i].b));
        rects[i].c = max(0, min(10000, rects[i].c));
        rects[i].d = max(0, min(10000, rects[i].d));
        if (rects[i].a >= rects[i].c) rects[i].c = min(10000, rects[i].a + 1);
        if (rects[i].b >= rects[i].d) rects[i].d = min(10000, rects[i].b + 1);
        cout << rects[i].a << ' ' << rects[i].b << ' ' << rects[i].c << ' ' << rects[i].d << '\n';
    }

    return 0;
}