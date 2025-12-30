#include <bits/stdc++.h>
using namespace std;

double BIG = 1000000000000.0;
int R = 10000;
int NN;

double query(double x, double y) {
    cout << fixed << setprecision(15);
    cout << "? " << x << " " << y << endl;
    double s;
    cin >> s;
    return s;
}

pair<double, double> get_far(double m) {
    double abs_m = fabs(m);
    double xx, yy;
    if (abs_m <= 1.0) {
        xx = BIG;
        yy = m * xx;
    } else {
        double sign_y = (m >= 0 ? 1.0 : -1.0);
        yy = sign_y * BIG;
        xx = yy / m;
    }
    return {xx, yy};
}

double get_g(double m) {
    auto [xf, yf] = get_far(m);
    double sf = query(xf, yf);
    double xn = xf * 0.5;
    double yn = yf * 0.5;
    double sn = query(xn, yn);
    return (sf - sn) / (xf - xn);
}

int main() {
    cin >> NN;
    int n = NN;

    // Initial queries for A, B, C
    double y1 = -BIG;
    double s1 = query(0.0, y1);
    double y2 = - (double)R - 1.0;
    double s2 = query(0.0, y2);
    double dy = -y1 - (-y2); // positive
    double ds = s1 - s2;
    double BB = ds / dy;
    double CC = s2 + BB * (-y2); // S = -B y + C , so C = S + B y  (y negative)

    double offset = 100.0;
    double x3 = 1e8 - offset;
    double s3 = query(x3, y1);
    double AA = (s3 - s1) / x3;

    // Now find the a_i , descending order
    vector<int> ais;
    double curr_B = BB;
    int curr_l = -R;
    int curr_r = R;
    for (int ii = 0; ii < n; ii++) {
        int lo = curr_l;
        int hi = curr_r;
        while (lo < hi) {
            int mid = lo + (hi - lo + 1) / 2;
            double mm = (double)mid + 0.5;
            double delta = 0.25;
            double mlo = mm - delta;
            double mhi = mm + delta;
            double g_lo = get_g(mlo);
            double g_hi = get_g(mhi);
            double gpr = (g_hi - g_lo) / (2.0 * delta);
            if (gpr < curr_B - 1e-9) {
                lo = mid;
            } else {
                hi = mid - 1;
            }
        }
        int cand = lo;
        // Verify with extra computation at cand + 0.5
        double mmv = (double)cand + 0.5;
        double delta = 0.25;
        double mlo_v = mmv - delta;
        double mhi_v = mmv + delta;
        double g_lo_v = get_g(mlo_v);
        double g_hi_v = get_g(mhi_v);
        double gpr_v = (g_hi_v - g_lo_v) / (2.0 * delta);
        if (gpr_v >= curr_B - 1e-9) {
            cand--;
            // recompute for cand
            mmv = (double)cand + 0.5;
            mlo_v = mmv - delta;
            mhi_v = mmv + delta;
            g_lo_v = get_g(mlo_v);
            g_hi_v = get_g(mhi_v);
            gpr_v = (g_hi_v - g_lo_v) / (2.0 * delta);
        }
        ais.push_back(cand);
        double aa = (double)cand;
        double dd = sqrt(aa * aa + 1.0);
        double ww = 1.0 / dd;
        curr_B -= ww;
        curr_r = cand - 1;
    }

    // Now ais has all a_i , sort ascending
    sort(ais.begin(), ais.end());
    vector<double> a_d(n);
    vector<double> d(n);
    for (int i = 0; i < n; i++) {
        a_d[i] = (double)ais[i];
        d[i] = sqrt(a_d[i] * a_d[i] + 1.0);
    }

    // Now query for partials
    vector<double> partial(n - 1);
    for (int interv = 0; interv < n - 1; interv++) {
        double mk = (a_d[interv] + a_d[interv + 1]) * 0.5;
        auto [xx, yy] = get_far(mk);
        double S = query(xx, yy);
        double gk = 0.0;
        for (int j = 0; j < n; j++) {
            gk += fabs(a_d[j] - mk) / d[j];
        }
        double ff = S - xx * gk;
        partial[interv] = (ff + CC) / 2.0;
    }

    // Now compute c
    vector<double> c(n);
    if (n == 1) {
        c[0] = CC;
    } else {
        c[0] = CC - partial[0];
        for (int i = 1; i < n - 1; i++) {
            c[i] = partial[i - 1] - partial[i];
        }
        c[n - 1] = partial[n - 2];
    }

    // Now b_i
    vector<long long> bs(n);
    for (int i = 0; i < n; i++) {
        double bi_d = c[i] * d[i];
        bs[i] = round(bi_d);
    }

    // Output
    cout << "!";
    for (int i = 0; i < n; i++) {
        cout << " " << ais[i];
    }
    for (int i = 0; i < n; i++) {
        cout << " " << bs[i];
    }
    cout << endl;

    return 0;
}