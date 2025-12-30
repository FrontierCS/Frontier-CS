#include <bits/stdc++.h>
using namespace std;

static inline uint64_t packKey(int x, int y) {
    return (uint64_t(x) << 17) | uint64_t(y);
}

struct BestRect {
    int x1=0, x2=1, y1=0, y2=1;
    int diff = INT_MIN;
    int a = 0, b = 0;
    int perim = INT_MAX;
};

static inline int clampi(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static inline bool fixInterval(int &l, int &r, int lo=0, int hi=100000) {
    l = clampi(l, lo, hi);
    r = clampi(r, lo, hi);
    if (l > r) swap(l, r);
    if (l == r) {
        if (r < hi) r++;
        else if (l > lo) l--;
        else return false;
    }
    if (l >= r) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    int M = 2 * N;
    vector<int> xs(M), ys(M), wt(M);

    unordered_map<uint64_t, int> mp;
    mp.reserve((size_t)M * 2);

    for (int i = 0; i < M; i++) {
        cin >> xs[i] >> ys[i];
        wt[i] = (i < N ? 1 : -1);
        mp[packKey(xs[i], ys[i])] = wt[i];
    }

    auto evalRectFull = [&](int x1, int x2, int y1, int y2, int &diff, int &a, int &b) {
        diff = 0; a = 0; b = 0;
        for (int i = 0; i < M; i++) {
            int x = xs[i], y = ys[i];
            if (x1 <= x && x <= x2 && y1 <= y && y <= y2) {
                if (wt[i] == 1) { a++; diff++; }
                else { b++; diff--; }
            }
        }
    };

    BestRect best;

    auto consider = [&](int x1, int x2, int y1, int y2, bool fastUnit=false,
                        int preDiff=0, int preA=0, int preB=0) {
        if (!fixInterval(x1, x2) || !fixInterval(y1, y2)) return;
        int perim = 2 * ((x2 - x1) + (y2 - y1));
        if (perim > 400000) return;

        int diff, a, b;
        if (fastUnit) {
            diff = preDiff; a = preA; b = preB;
        } else {
            evalRectFull(x1, x2, y1, y2, diff, a, b);
        }

        if (diff > best.diff ||
            (diff == best.diff && b < best.b) ||
            (diff == best.diff && b == best.b && perim < best.perim)) {
            best.x1 = x1; best.x2 = x2; best.y1 = y1; best.y2 = y2;
            best.diff = diff; best.a = a; best.b = b; best.perim = perim;
        }
    };

    // Baselines
    consider(0, 100000, 0, 100000);

    // RNG
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (seed << 7) ^ (seed >> 9) ^ 0x9e3779b97f4a7c15ULL;
    mt19937 rng((uint32_t)seed);
    uniform_int_distribution<int> uniCoord(0, 100000);
    uniform_int_distribution<int> uni01(0, 1);

    // Try unit squares around each mackerel (fast O(1) check using map).
    for (int i = 0; i < N; i++) {
        int x = xs[i], y = ys[i];
        for (int dx = 0; dx <= 1; dx++) {
            int x1 = x - dx, x2 = x1 + 1;
            if (x1 < 0 || x2 > 100000) continue;
            for (int dy = 0; dy <= 1; dy++) {
                int y1 = y - dy, y2 = y1 + 1;
                if (y1 < 0 || y2 > 100000) continue;

                int a = 0, b = 0, diff = 0;
                for (int xx : {x1, x2}) for (int yy : {y1, y2}) {
                    auto it = mp.find(packKey(xx, yy));
                    if (it == mp.end()) continue;
                    if (it->second == 1) { a++; diff++; }
                    else { b++; diff--; }
                }
                consider(x1, x2, y1, y2, true, diff, a, b);
            }
        }
    }

    // Find an empty unit square (guarantees diff=0, b=0) as a safe fallback.
    for (int t = 0; t < 20000; t++) {
        int x0 = uniform_int_distribution<int>(0, 99999)(rng);
        int y0 = uniform_int_distribution<int>(0, 99999)(rng);
        bool ok = true;
        for (int xx : {x0, x0 + 1}) for (int yy : {y0, y0 + 1}) {
            if (mp.find(packKey(xx, yy)) != mp.end()) { ok = false; break; }
        }
        if (ok) {
            consider(x0, x0 + 1, y0, y0 + 1, true, 0, 0, 0);
            break;
        }
    }

    // Centered rectangles around sampled mackerels with various sizes.
    vector<int> sizes = {20, 50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600};
    int sampleCnt = min(N, 300);
    for (int s = 0; s < sampleCnt; s++) {
        int i = uniform_int_distribution<int>(0, N - 1)(rng);
        int cx = xs[i], cy = ys[i];
        for (int d : sizes) {
            int x1 = cx - d, x2 = cx + d;
            int y1 = cy - d, y2 = cy + d;
            consider(x1, x2, y1, y2);
        }
    }

    // Time-bounded random search
    auto t0 = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85; // seconds
    auto elapsedSec = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - t0).count();
    };

    uniform_int_distribution<int> uniPad(0, 5000);
    uniform_int_distribution<int> uniPick(0, M - 1);

    while (elapsedSec() < TIME_LIMIT) {
        int xa = (uni01(rng) ? xs[uniPick(rng)] : uniCoord(rng));
        int xb = (uni01(rng) ? xs[uniPick(rng)] : uniCoord(rng));
        int ya = (uni01(rng) ? ys[uniPick(rng)] : uniCoord(rng));
        int yb = (uni01(rng) ? ys[uniPick(rng)] : uniCoord(rng));

        int l = min(xa, xb), r = max(xa, xb);
        int dL = uniPad(rng), dR = uniPad(rng);
        l -= dL; r += dR;

        int btm = min(ya, yb), top = max(ya, yb);
        int dB = uniPad(rng), dT = uniPad(rng);
        btm -= dB; top += dT;

        consider(l, r, btm, top);
    }

    // Output the best rectangle as a simple orthogonal polygon (4 vertices).
    cout << 4 << "\n";
    cout << best.x1 << " " << best.y1 << "\n";
    cout << best.x2 << " " << best.y1 << "\n";
    cout << best.x2 << " " << best.y2 << "\n";
    cout << best.x1 << " " << best.y2 << "\n";
    return 0;
}