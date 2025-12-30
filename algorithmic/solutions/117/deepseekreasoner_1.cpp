#include <bits/stdc++.h>
using namespace std;

typedef long long ll;
typedef long double ld;

const ld EPS = 1e-7;
const ld DERIV_EPS = 1e-5;
const ld BREAK_THRESH = 0.5;
const int X_MIN = -10000;
const int X_MAX = 10000;
const int Y_MIN = -10000;
const int Y_MAX = 10000;
const int STEP_X = 5;               // step for coarse scan in x
const int STEP_Y = 20;              // step for coarse scan in y for horizontal lines
const int MAX_ITER = 50;            // max binary search iterations

int n;
map<pair<ld, ld>, ld> cache;

ld query(ld x, ld y) {
    auto key = make_pair(x, y);
    if (cache.count(key)) return cache[key];
    cout << "? " << fixed << setprecision(10) << x << " " << y << endl;
    ld res;
    cin >> res;
    cache[key] = res;
    return res;
}

struct BreakInfo {
    ld x;      // breakpoint coordinate
    ld jump;   // jump in derivative (2|c_i|)
    BreakInfo(ld x_ = 0, ld jump_ = 0) : x(x_), jump(jump_) {}
};

// Find a breakpoint in S(x, y) for x in [xl, xr], assuming exactly one.
BreakInfo find_breakpoint(ld xl, ld xr, ld y) {
    ld fl = query(xl, y);
    ld fr = query(xr, y);
    for (int iter = 0; iter < MAX_ITER && xr - xl > EPS; ++iter) {
        ld xm = (xl + xr) / 2;
        ld fm = query(xm, y);
        ld s1 = (fm - fl) / (xm - xl);
        ld s2 = (fr - fm) / (xr - xm);
        if (s1 + EPS < s2) {          // breakpoint is to the right of xm
            xl = xm;
            fl = fm;
        } else if (s1 > s2 + EPS) {   // breakpoint is to the left of xm
            xr = xm;
            fr = fm;
        } else {
            break;  // slopes are equal => no breakpoint inside (or exactly at xm)
        }
    }
    ld x0 = (xl + xr) / 2;
    // compute jump using central difference with small offset
    ld delta = DERIV_EPS;
    ld fleft = query(x0 - delta, y);
    ld fright = query(x0 + delta, y);
    ld f0 = query(x0, y);
    ld left_deriv = (f0 - fleft) / delta;
    ld right_deriv = (fright - f0) / delta;
    ld jump = right_deriv - left_deriv;
    return BreakInfo(x0, jump);
}

// Scan along a horizontal line y = y0 to find all breakpoints.
vector<BreakInfo> scan_y(ld y0) {
    vector<ld> xs, vals;
    for (int x = X_MIN; x <= X_MAX; x += STEP_X) {
        ld val = query(x, y0);
        xs.push_back(x);
        vals.push_back(val);
    }
    int m = xs.size();
    vector<ld> diffs(m-1);
    for (int i = 0; i < m-1; ++i) {
        diffs[i] = (vals[i+1] - vals[i]) / STEP_X;
    }
    vector<BreakInfo> breaks;
    for (int i = 1; i < m-1; ++i) {
        if (fabs(diffs[i] - diffs[i-1]) > BREAK_THRESH) {
            // there is a breakpoint between xs[i-1] and xs[i+1]
            ld xl = xs[i-1];
            ld xr = xs[i+1];
            BreakInfo info = find_breakpoint(xl, xr, y0);
            breaks.push_back(info);
        }
    }
    return breaks;
}

// Distance from point (x,y) to line y = a x + b.
ld line_dist(ld a, ld b, ld x, ld y) {
    return fabs(a * x - y + b) / sqrt(a * a + 1);
}

int main() {
    cin >> n;
    cache.clear();

    // Step 1: scan y = 0
    vector<BreakInfo> breaks0 = scan_y(0);
    // Step 2: scan y = 1
    vector<BreakInfo> breaks1 = scan_y(1);

    // Match breakpoints by jump magnitude
    sort(breaks0.begin(), breaks0.end(), [](const BreakInfo& A, const BreakInfo& B) {
        return A.jump < B.jump;
    });
    sort(breaks1.begin(), breaks1.end(), [](const BreakInfo& A, const BreakInfo& B) {
        return A.jump < B.jump;
    });

    vector<pair<int, int>> lines; // (a, b) for non-horizontal lines
    int k = min(breaks0.size(), breaks1.size());
    for (int i = 0; i < k; ++i) {
        ld x0 = breaks0[i].x;
        ld x1 = breaks1[i].x;
        ld a = 1.0 / (x1 - x0);   // because (x0,0) and (x1,1) lie on the line
        ld b = -a * x0;
        // round to nearest integer (should be exact)
        int a_int = (int)round(a);
        int b_int = (int)round(b);
        // sanity check
        if (abs(a_int) <= 10000 && abs(b_int) <= 10000) {
            lines.emplace_back(a_int, b_int);
        }
    }

    // Step 3: recover horizontal lines (a = 0)
    // We'll sample S(0, y) and subtract contributions from known lines.
    vector<ld> ys, res_vals;
    for (int y = Y_MIN; y <= Y_MAX; y += STEP_Y) {
        ld total = query(0, y);
        ld known_sum = 0;
        for (auto& line : lines) {
            known_sum += line_dist(line.first, line.second, 0, y);
        }
        ld residual = total - known_sum;
        ys.push_back(y);
        res_vals.push_back(residual);
    }
    int m = ys.size();
    vector<ld> diffs(m-1);
    for (int i = 0; i < m-1; ++i) {
        diffs[i] = (res_vals[i+1] - res_vals[i]) / STEP_Y;
    }
    vector<int> horizontal_bs;
    for (int i = 1; i < m-1; ++i) {
        if (fabs(diffs[i] - diffs[i-1]) > BREAK_THRESH) {
            // there is a breakpoint between ys[i-1] and ys[i+1]
            ld yl = ys[i-1];
            ld yr = ys[i+1];
            // binary search for breakpoint in residual function
            ld fl = res_vals[i-1];
            ld fr = res_vals[i+1];
            for (int iter = 0; iter < MAX_ITER && yr - yl > EPS; ++iter) {
                ld ym = (yl + yr) / 2;
                // need to query residual at ym
                ld total = query(0, ym);
                ld known_sum = 0;
                for (auto& line : lines) {
                    known_sum += line_dist(line.first, line.second, 0, ym);
                }
                ld fm = total - known_sum;
                ld s1 = (fm - fl) / (ym - yl);
                ld s2 = (fr - fm) / (yr - ym);
                if (s1 + EPS < s2) {
                    yl = ym;
                    fl = fm;
                } else if (s1 > s2 + EPS) {
                    yr = ym;
                    fr = fm;
                } else {
                    break;
                }
            }
            ld y0 = (yl + yr) / 2;
            int b_int = (int)round(y0);
            horizontal_bs.push_back(b_int);
        }
    }

    // Combine all lines
    vector<pair<int, int>> all_lines = lines;
    for (int b : horizontal_bs) {
        all_lines.emplace_back(0, b);
    }

    // If we have more than n lines, keep only the first n (should not happen).
    // If we have less, we might have missed some; but we assume we found all.
    all_lines.resize(n);

    // Output answer
    cout << "!";
    for (auto& line : all_lines) {
        cout << " " << line.first;
    }
    for (auto& line : all_lines) {
        cout << " " << line.second;
    }
    cout << endl;

    return 0;
}