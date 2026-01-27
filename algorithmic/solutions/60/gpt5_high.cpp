#include <bits/stdc++.h>
using namespace std;

static const int BOX = 100000;
static const int STEP = 199;
static const double EPS = 1e-9;

double querySegment(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    double L;
    if (!(cin >> L)) {
        exit(0);
    }
    return L;
}

double queryVertical(int x) {
    return querySegment(x, 0, x, BOX);
}

double queryHorizontal(int y) {
    return querySegment(0, y, BOX, y);
}

pair<int,double> findInsideVertical() {
    for (int x = 0; x <= BOX; x += STEP) {
        double L = queryVertical(x);
        if (L > EPS) return {x, L};
    }
    return {-1, 0.0};
}

pair<int,double> findInsideHorizontal() {
    for (int y = 0; y <= BOX; y += STEP) {
        double L = queryHorizontal(y);
        if (L > EPS) return {y, L};
    }
    return {-1, 0.0};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Find two vertical chords
    auto v1 = findInsideVertical();
    if (v1.first == -1) {
        cout << "answer 0 0 100" << endl;
        cout.flush();
        return 0;
    }
    int x1 = v1.first;
    double Lx1 = v1.second;

    int x2 = -1;
    double Lx2 = 0.0;
    if (x1 + 1 <= BOX) {
        Lx2 = queryVertical(x1 + 1);
        if (Lx2 > EPS) x2 = x1 + 1;
    }
    if (x2 == -1 && x1 - 1 >= 0) {
        double t = queryVertical(x1 - 1);
        if (t > EPS) { x2 = x1 - 1; Lx2 = t; }
    }
    if (x2 == -1) {
        for (int dx = 2; dx <= 100; ++dx) {
            if (x1 + dx <= BOX) {
                double t = queryVertical(x1 + dx);
                if (t > EPS) { x2 = x1 + dx; Lx2 = t; break; }
            }
            if (x1 - dx >= 0) {
                double t = queryVertical(x1 - dx);
                if (t > EPS) { x2 = x1 - dx; Lx2 = t; break; }
            }
        }
    }

    double cx = 0.0;
    if (x2 != -1) {
        double c1 = x1, c2 = x2;
        double term = ( (c1*c1 - c2*c2) - (Lx2*Lx2 - Lx1*Lx1)/4.0 );
        double denom = 2.0 * (c1 - c2);
        cx = term / denom;
    } else {
        // Fallback (should not happen)
        cx = x1;
    }

    double r = sqrt(max(0.0, (x1 - cx)*(x1 - cx) + (Lx1/2.0)*(Lx1/2.0)));

    // Find two horizontal chords
    auto h1 = findInsideHorizontal();
    if (h1.first == -1) {
        cout << "answer " << (long long)llround(cx) << " " << 0 << " " << (long long)llround(r) << endl;
        cout.flush();
        return 0;
    }
    int y1 = h1.first;
    double Ly1 = h1.second;

    int y2 = -1;
    double Ly2 = 0.0;
    if (y1 + 1 <= BOX) {
        Ly2 = queryHorizontal(y1 + 1);
        if (Ly2 > EPS) y2 = y1 + 1;
    }
    if (y2 == -1 && y1 - 1 >= 0) {
        double t = queryHorizontal(y1 - 1);
        if (t > EPS) { y2 = y1 - 1; Ly2 = t; }
    }
    if (y2 == -1) {
        for (int dy = 2; dy <= 100; ++dy) {
            if (y1 + dy <= BOX) {
                double t = queryHorizontal(y1 + dy);
                if (t > EPS) { y2 = y1 + dy; Ly2 = t; break; }
            }
            if (y1 - dy >= 0) {
                double t = queryHorizontal(y1 - dy);
                if (t > EPS) { y2 = y1 - dy; Ly2 = t; break; }
            }
        }
    }

    double cy = 0.0;
    if (y2 != -1) {
        double c1 = y1, c2 = y2;
        double term = ( (c1*c1 - c2*c2) - (Ly2*Ly2 - Ly1*Ly1)/4.0 );
        double denom = 2.0 * (c1 - c2);
        cy = term / denom;
    } else {
        // Fallback (should not happen)
        cy = y1;
    }

    long long CX = llround(cx);
    long long CY = llround(cy);
    long long R = llround(r);

    cout << "answer " << CX << " " << CY << " " << R << endl;
    cout.flush();
    return 0;
}