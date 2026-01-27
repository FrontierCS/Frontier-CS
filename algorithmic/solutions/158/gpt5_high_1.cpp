#include <bits/stdc++.h>
using namespace std;

static const int R = 10000;
static const int L = -R + 1; // -9999
static const int U = R - 1;  // 9999

struct Candidate {
    int V, H;
    vector<int> cx, cy;
    long long score;
};

static vector<int> xs, ys;
static vector<int> x_sorted, y_sorted;
static vector<int> availX, availY;
static int N, K;
static int a[11];

int clampi(int x, int lo, int hi){ return x<lo?lo:(x>hi?hi:x); }

int chooseNearest(const vector<int>& avail, vector<char>& used, double c0) {
    int n = (int)avail.size();
    int r = (int)(lower_bound(avail.begin(), avail.end(), (int)ceil(c0)) - avail.begin());
    int l = r - 1;
    const double INF = 1e100;
    while (true) {
        double dr = (r < n ? fabs((double)avail[r] - c0) : INF);
        double dl = (l >= 0 ? fabs((double)avail[l] - c0) : INF);
        if (dl <= dr) {
            if (l >= 0) {
                if (!used[l]) { used[l] = 1; return avail[l]; }
                --l;
            } else {
                if (r < n) {
                    if (!used[r]) { used[r] = 1; return avail[r]; }
                    ++r;
                } else break;
            }
        } else {
            if (r < n) {
                if (!used[r]) { used[r] = 1; return avail[r]; }
                ++r;
            } else {
                if (l >= 0) {
                    if (!used[l]) { used[l] = 1; return avail[l]; }
                    --l;
                } else break;
            }
        }
    }
    // Fallback (should not happen)
    for (int i = 0; i < n; ++i) if (!used[i]) { used[i] = 1; return avail[i]; }
    // As a last resort (cannot happen), return center
    return 0;
}

vector<int> genCutsAxisEqual(const vector<int>& avail, int cnt) {
    vector<int> cuts;
    cuts.reserve(cnt);
    vector<char> used(avail.size(), 0);
    double step = (double)(U - L + 1) / (cnt + 1);
    for (int j = 1; j <= cnt; ++j) {
        double c0 = L + step * j;
        int c = chooseNearest(avail, used, c0);
        cuts.push_back(c);
    }
    sort(cuts.begin(), cuts.end());
    return cuts;
}

vector<int> genCutsAxisQuantile(const vector<int>& avail, const vector<int>& sorted_coords, int cnt) {
    vector<int> cuts;
    cuts.reserve(cnt);
    vector<char> used(avail.size(), 0);
    int n = (int)sorted_coords.size();
    double step = (double)(U - L + 1) / (cnt + 1);
    for (int j = 1; j <= cnt; ++j) {
        int T = (long long)j * n / (cnt + 1);
        double c0;
        if (0 < T && T < n) {
            c0 = 0.5 * (sorted_coords[T - 1] + sorted_coords[T]);
        } else {
            c0 = L + step * j; // fallback to equal spacing near edges
        }
        c0 = clampi((int)round(c0), L, U);
        int c = chooseNearest(avail, used, c0);
        cuts.push_back(c);
    }
    sort(cuts.begin(), cuts.end());
    return cuts;
}

long long evaluateScore(const vector<int>& cx, const vector<int>& cy) {
    int V = (int)cx.size();
    int H = (int)cy.size();
    int cols = V + 1;
    int rows = H + 1;
    int M = cols * rows;
    vector<int> cnt(M, 0);
    // For binary search, ensure sorted
    // cx, cy already sorted
    for (int i = 0; i < N; ++i) {
        int ix = (int)(lower_bound(cx.begin(), cx.end(), xs[i]) - cx.begin()); // number of vertical cuts < x
        int iy = (int)(lower_bound(cy.begin(), cy.end(), ys[i]) - cy.begin()); // number of horizontal cuts < y
        int id = ix * rows + iy;
        cnt[id]++;
    }
    long long freq[11] = {0};
    for (int v : cnt) {
        if (1 <= v && v <= 10) freq[v]++;
    }
    long long sc = 0;
    for (int d = 1; d <= 10; ++d) sc += min<long long>(a[d], freq[d]);
    return sc;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> N >> K;
    for (int d = 1; d <= 10; ++d) cin >> a[d];
    xs.resize(N);
    ys.resize(N);
    for (int i = 0; i < N; ++i) {
        int xi, yi;
        cin >> xi >> yi;
        xs[i] = xi;
        ys[i] = yi;
    }
    x_sorted = xs;
    y_sorted = ys;
    sort(x_sorted.begin(), x_sorted.end());
    sort(y_sorted.begin(), y_sorted.end());

    // Build availability maps for x and y lines: integers in [L..U] not equal to any x or y respectively
    vector<char> usedXmap(U - L + 1, 0), usedYmap(U - L + 1, 0);
    for (int i = 0; i < N; ++i) {
        if (xs[i] >= L && xs[i] <= U) usedXmap[xs[i] - L] = 1;
        if (ys[i] >= L && ys[i] <= U) usedYmap[ys[i] - L] = 1;
    }
    for (int c = L; c <= U; ++c) if (!usedXmap[c - L]) availX.push_back(c);
    for (int c = L; c <= U; ++c) if (!usedYmap[c - L]) availY.push_back(c);

    // Expected-based selection of total number of cuts S
    auto fact = [&]() {
        static double f[21];
        static bool inited = false;
        if (!inited) {
            f[0] = 1.0;
            for (int i = 1; i <= 20; ++i) f[i] = f[i - 1] * i;
            inited = true;
        }
        return f;
    }();
    auto poissonP = [&](double lambda, int d) -> double {
        if (d < 0) return 0.0;
        double p0 = exp(-lambda);
        if (d == 0) return p0;
        double val = p0 * pow(lambda, d) / fact[d];
        return val;
    };

    int bestS = 0;
    double bestExpected = -1.0;
    for (int S = 0; S <= K; ++S) {
        int V = S / 2;
        int H = S - V;
        long long M = 1LL * (V + 1) * (H + 1);
        if (M <= 0) M = 1;
        double lambda = (double)N / (double)M;
        double sumExp = 0.0;
        for (int d = 1; d <= 10; ++d) {
            double ebd = (double)M * poissonP(lambda, d);
            sumExp += min((double)a[d], ebd);
        }
        if (sumExp > bestExpected + 1e-9 || (fabs(sumExp - bestExpected) <= 1e-9 && M > 1LL * ((bestS/2)+1) * ((bestS - bestS/2)+1))) {
            bestExpected = sumExp;
            bestS = S;
        }
    }

    // Evaluate actual scores around bestS
    int deltaS = 5;
    long long bestScore = -1;
    vector<int> bestCx, bestCy;
    int bestV = 0, bestH = 0;
    for (int S = max(0, bestS - deltaS); S <= min(K, bestS + deltaS); ++S) {
        for (int V = 0; V <= S; ++V) {
            int H = S - V;
            // Skip if not enough available positions (very unlikely)
            if ((int)availX.size() < V || (int)availY.size() < H) continue;

            // Variant 0: equal spacing
            vector<int> cx0 = genCutsAxisEqual(availX, V);
            vector<int> cy0 = genCutsAxisEqual(availY, H);
            long long sc0 = evaluateScore(cx0, cy0);
            if (sc0 > bestScore) {
                bestScore = sc0;
                bestCx = cx0;
                bestCy = cy0;
                bestV = V;
                bestH = H;
            }

            // Variant 1: quantile-based
            vector<int> cx1 = genCutsAxisQuantile(availX, x_sorted, V);
            vector<int> cy1 = genCutsAxisQuantile(availY, y_sorted, H);
            long long sc1 = evaluateScore(cx1, cy1);
            if (sc1 > bestScore) {
                bestScore = sc1;
                bestCx = cx1;
                bestCy = cy1;
                bestV = V;
                bestH = H;
            }
        }
    }

    // If everything failed (shouldn't), fallback to zero cuts
    if (bestScore < 0) {
        cout << 0 << "\n";
        return 0;
    }

    // Output lines
    int k = bestV + bestH;
    cout << k << "\n";
    // Vertical lines: x = c
    for (int c : bestCx) {
        long long px = c, py = -1000000000LL;
        long long qx = c, qy = 1000000000LL;
        cout << px << " " << py << " " << qx << " " << qy << "\n";
    }
    // Horizontal lines: y = c
    for (int c : bestCy) {
        long long px = -1000000000LL, py = c;
        long long qx = 1000000000LL, qy = c;
        cout << px << " " << py << " " << qx << " " << qy << "\n";
    }
    return 0;
}