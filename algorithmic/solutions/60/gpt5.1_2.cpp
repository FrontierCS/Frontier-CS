#include <bits/stdc++.h>
using namespace std;

const int MAX_COORD = 100000;

vector<double> vLen(MAX_COORD + 1, -1.0);
vector<double> hLen(MAX_COORD + 1, -1.0);

double queryVertical(int x) {
    if (vLen[x] >= -0.5) return vLen[x];
    cout << "query " << x << " 0 " << x << " " << MAX_COORD << endl;
    cout.flush();
    double res;
    if (!(cin >> res)) exit(0);
    vLen[x] = res;
    return res;
}

double queryHorizontal(int y) {
    if (hLen[y] >= -0.5) return hLen[y];
    cout << "query 0 " << y << " " << MAX_COORD << " " << y << endl;
    cout.flush();
    double res;
    if (!(cin >> res)) exit(0);
    hLen[y] = res;
    return res;
}

int findCenterX() {
    int l = 0, r = MAX_COORD;
    while (r - l > 3) {
        int m1 = l + (r - l) / 3;
        int m2 = r - (r - l) / 3;
        double f1 = queryVertical(m1);
        double f2 = queryVertical(m2);
        if (f1 < f2) {
            l = m1;
        } else {
            r = m2;
        }
    }
    int best = l;
    double bestVal = queryVertical(l);
    for (int i = l + 1; i <= r; ++i) {
        double val = queryVertical(i);
        if (val > bestVal) {
            bestVal = val;
            best = i;
        }
    }
    return best;
}

int findCenterY() {
    int l = 0, r = MAX_COORD;
    while (r - l > 3) {
        int m1 = l + (r - l) / 3;
        int m2 = r - (r - l) / 3;
        double f1 = queryHorizontal(m1);
        double f2 = queryHorizontal(m2);
        if (f1 < f2) {
            l = m1;
        } else {
            r = m2;
        }
    }
    int best = l;
    double bestVal = queryHorizontal(l);
    for (int i = l + 1; i <= r; ++i) {
        double val = queryHorizontal(i);
        if (val > bestVal) {
            bestVal = val;
            best = i;
        }
    }
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int cx = findCenterX();
    double Lv = queryVertical(cx);
    int r = (int)llround(Lv / 2.0);

    int cy = findCenterY();
    double Lh = queryHorizontal(cy);
    int r2 = (int)llround(Lh / 2.0);
    if (abs(r2 - r) > 1) {
        // In case of rare rounding mismatch, average them.
        r = (r + r2) / 2;
    }

    cout << "answer " << cx << " " << cy << " " << r << endl;
    cout.flush();
    return 0;
}