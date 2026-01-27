#include <bits/stdc++.h>
using namespace std;

static const int N = 100000;
static const int STEP = 200;
static const double EPS = 1e-7;

double query_segment(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    double res;
    if (!(cin >> res)) {
        // If input fails, terminate.
        exit(0);
    }
    return res;
}

double query_vertical_full(int x) {
    return query_segment(x, 0, x, N);
}

double query_vertical_partial(int x, int y1, int y2) {
    return query_segment(x, y1, x, y2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // 1) Vertical scan to find one intersecting vertical line
    int x1 = -1;
    double L1 = 0.0;
    for (int x = 0; x <= N; x += STEP) {
        double L = query_vertical_full(x);
        if (L > EPS) {
            x1 = x;
            L1 = L;
            break;
        }
    }
    if (x1 == -1) {
        // As a fallback (shouldn't happen with STEP=200 and R>=100), try shifted scan
        for (int x = STEP/2; x <= N; x += STEP) {
            double L = query_vertical_full(x);
            if (L > EPS) {
                x1 = x;
                L1 = L;
                break;
            }
        }
        if (x1 == -1) {
            // If still not found, terminate
            // (In valid scenarios, this should not happen)
            return 0;
        }
    }

    // 2) Find a second intersecting vertical line near x1
    int x2 = -1;
    double L2 = 0.0;
    int step = STEP;
    while (step >= 1 && x2 == -1) {
        // Try x1 + step
        int xt = x1 + step;
        if (xt <= N) {
            double L = query_vertical_full(xt);
            if (L > EPS) {
                x2 = xt;
                L2 = L;
                break;
            }
        }
        // Try x1 - step
        xt = x1 - step;
        if (xt >= 0) {
            double L = query_vertical_full(xt);
            if (L > EPS) {
                x2 = xt;
                L2 = L;
                break;
            }
        }
        step /= 2;
    }
    if (x2 == -1) {
        // As ultimate fallback, try nearby integers
        for (int dx = 1; dx <= STEP && x2 == -1; ++dx) {
            if (x1 + dx <= N) {
                double L = query_vertical_full(x1 + dx);
                if (L > EPS) { x2 = x1 + dx; L2 = L; break; }
            }
            if (x1 - dx >= 0) {
                double L = query_vertical_full(x1 - dx);
                if (L > EPS) { x2 = x1 - dx; L2 = L; break; }
            }
        }
        if (x2 == -1) return 0;
    }

    // 3) Compute cx from two vertical chords
    // cx = [x1^2 - x2^2 + (L1^2 - L2^2)/4] / [2 (x1 - x2)]
    auto sq = [](double v){ return v*v; };
    double num = (double)x1*(double)x1 - (double)x2*(double)x2 + (sq(L1) - sq(L2))/4.0;
    double den = 2.0 * ((double)x1 - (double)x2);
    double cx = num / den;

    // 4) Compute R^2 using one of the chords
    double R2 = sq((double)x1 - cx) + sq(L1/2.0);
    double R = sqrt(max(0.0, R2));

    // 5) Find cy by binary searching bottom boundary on vertical line x1
    // Intersection along this line is [cy - h1, cy + h1], where h1 = L1/2
    double h1 = L1 / 2.0;
    int low = 0, high = N;
    while (low < high) {
        int mid = (low + high) / 2;
        double LM = query_vertical_partial(x1, 0, mid);
        if (LM > EPS) high = mid;
        else low = mid + 1;
    }
    // Now low is the smallest integer m such that overlap with [0, m] is > 0
    double Llow = query_vertical_partial(x1, 0, low);
    double yb = (double)low - Llow; // y_b = low - overlap length
    double cy = yb + h1;

    // Round to integers
    long long cx_i = llround(cx);
    long long cy_i = llround(cy);
    long long R_i  = llround(R);

    // Output the answer
    cout << "answer " << cx_i << " " << cy_i << " " << R_i << endl;
    cout.flush();

    return 0;
}