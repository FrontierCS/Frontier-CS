#include <bits/stdc++.h>
using namespace std;

static const int N = 100000;
static const double EPS_POS  = 1e-4;
static const double EPS_ZERO = 1e-4;
static const double EPS_FULL = 1e-4;

struct Interactor {
    int qcnt = 0;

    double ask(int x1, int y1, int x2, int y2) {
        cout << "query " << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << '\n';
        cout.flush();

        string s;
        if (!(cin >> s)) exit(0);
        double v = stod(s);
        if (v < -0.5) exit(0); // judge typically returns -1 on error
        ++qcnt;
        return v;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Interactor it;

    vector<double> fullCache(N + 1, 0.0);
    vector<char> fullVis(N + 1, 0);

    auto fullVertical = [&](int x) -> double {
        if (fullVis[x]) return fullCache[x];
        double v = it.ask(x, 0, x, N);
        fullVis[x] = 1;
        fullCache[x] = v;
        return v;
    };

    auto isPosX = [&](int x) -> bool {
        return fullVertical(x) > EPS_POS;
    };

    // Step < 200 to guarantee hitting the interior for r >= 100.
    const int STEP = 199;

    int x_in = -1;
    for (int x = 0; x <= N; x += STEP) {
        if (isPosX(x)) {
            x_in = x;
            break;
        }
    }
    if (x_in == -1) {
        // Should not happen, but try a fallback scan with offset.
        for (int x = STEP / 2; x <= N; x += STEP) {
            if (isPosX(x)) {
                x_in = x;
                break;
            }
        }
    }
    if (x_in == -1) exit(0);

    // Find left boundary xL = cx - r: last x in [0, x_in] with isPosX(x) == false.
    int l = 0, r = x_in;
    while (l < r) {
        int mid = (l + r + 1) / 2;
        if (!isPosX(mid)) l = mid;
        else r = mid - 1;
    }
    int xL = l;

    // Find right boundary xR = cx + r: first x in [x_in, N] with isPosX(x) == false.
    l = x_in, r = N;
    while (l < r) {
        int mid = (l + r) / 2;
        if (isPosX(mid)) l = mid + 1;
        else r = mid;
    }
    int xR = l;

    int cx = (xL + xR) / 2;
    int rad = (xR - xL) / 2;

    // Now determine cy using prefix queries on the vertical line x = cx.
    vector<double> prefCache(N + 1, 0.0);
    vector<char> prefVis(N + 1, 0);

    auto pref = [&](int y) -> double {
        if (y <= 0) return 0.0;
        if (y > N) y = N;
        if (prefVis[y]) return prefCache[y];
        double v = it.ask(cx, 0, cx, y);
        prefVis[y] = 1;
        prefCache[y] = v;
        return v;
    };

    // Lower boundary yA = cy - r: largest y with pref(y) == 0.
    int yl = 0, yr = N;
    while (yl < yr) {
        int mid = (yl + yr + 1) / 2;
        if (pref(mid) <= EPS_ZERO) yl = mid;
        else yr = mid - 1;
    }
    int yA = yl;

    // Upper boundary yB = cy + r: smallest y with pref(y) == 2r.
    double target = 2.0 * rad;
    yl = 0; yr = N;
    while (yl < yr) {
        int mid = (yl + yr) / 2;
        if (pref(mid) >= target - EPS_FULL) yr = mid;
        else yl = mid + 1;
    }
    int yB = yl;

    int cy = (yA + yB) / 2;

    cout << "answer " << cx << ' ' << cy << ' ' << rad << '\n';
    cout.flush();
    return 0;
}