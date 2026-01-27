#include <bits/stdc++.h>
using namespace std;

static const int64_t BOX = 100000;
static const int STEP = 199;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto query = [&](int x1, int y1, int x2, int y2)->double{
        cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << "\n";
        cout.flush();
        double resp;
        if(!(cin >> resp)) {
            exit(0);
        }
        return resp;
    };

    // Generate probe positions with step 199 to ensure at least one positive chord for r>=100
    vector<int> xs, ys;
    for (int x = 0; x <= BOX; x += STEP) xs.push_back(x);
    if (xs.back() != BOX) xs.push_back(BOX);
    for (int y = 0; y <= BOX; y += STEP) ys.push_back(y);
    if (ys.back() != BOX) ys.push_back(BOX);

    // Vertical scans to determine cx and r
    int nV = xs.size();
    vector<double> LV(nV, 0.0);
    for (int i = 0; i < nV; ++i) {
        LV[i] = query(xs[i], 0, xs[i], BOX);
    }
    int imax = 0;
    for (int i = 1; i < nV; ++i) if (LV[i] > LV[imax]) imax = i;
    int i2;
    if (imax == 0) i2 = 1;
    else if (imax == nV - 1) i2 = nV - 2;
    else i2 = (LV[imax - 1] > LV[imax + 1]) ? (imax - 1) : (imax + 1);

    double a0 = xs[imax], a1 = xs[i2];
    double L0 = LV[imax], L1 = LV[i2];
    // Use formula:
    // cx = [ (L0^2 - L1^2)/4 - (a1^2 - a0^2) ] / (2 (a0 - a1))
    double num = ((L0*L0 - L1*L1) / 4.0) - (a1*a1 - a0*a0);
    double den = 2.0 * (a0 - a1);
    double cx = num / den;
    double r2 = (L0*L0)/4.0 + (cx - a0)*(cx - a0);

    // Horizontal scans to determine cy
    int nH = ys.size();
    vector<double> LH(nH, 0.0);
    for (int i = 0; i < nH; ++i) {
        LH[i] = query(0, ys[i], BOX, ys[i]);
    }
    int jmax = 0;
    for (int i = 1; i < nH; ++i) if (LH[i] > LH[jmax]) jmax = i;
    int j2;
    if (jmax == 0) j2 = 1;
    else if (jmax == nH - 1) j2 = nH - 2;
    else j2 = (LH[jmax - 1] > LH[jmax + 1]) ? (jmax - 1) : (jmax + 1);

    double b0 = ys[jmax], b1 = ys[j2];
    double M0 = LH[jmax], M1 = LH[j2];
    // cy formula analogous:
    double numy = ((M0*M0 - M1*M1) / 4.0) - (b1*b1 - b0*b0);
    double deny = 2.0 * (b0 - b1);
    double cy = numy / deny;

    // r from r2 (vertical), but we can refine using horizontal largest as a sanity:
    // r2h = (M0^2)/4 + (cy - b0)^2
    // Take average to reduce numeric error
    double r2h = (M0*M0)/4.0 + (cy - b0)*(cy - b0);
    double r = sqrt(max(0.0, (r2 + r2h) * 0.5));

    long long xi = llround(cx);
    long long yi = llround(cy);
    long long ri = llround(r);

    cout << "answer " << xi << " " << yi << " " << ri << "\n";
    cout.flush();
    return 0;
}