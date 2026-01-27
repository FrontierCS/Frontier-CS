#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }
    vector<int> a(11);
    for (int i = 1; i <= 10; ++i) cin >> a[i];
    vector<pair<int,int>> pts(N);
    for (int i = 0; i < N; ++i) cin >> pts[i].first >> pts[i].second;

    // Parameters
    const long long LIM = 1000000000LL;
    const long long L = 900000000LL; // length scale for endpoints to stay within [-1e9, 1e9]
    const int R = 10000;             // cake radius
    const int T = 8000;              // max offset from origin to ensure line crosses the cake

    int k = K;
    cout << k << '\n';

    // RNG for slight randomization
    unsigned long long seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= 0x9e3779b97f4a7c15ULL;
    std::mt19937_64 rng(seed);
    long double PI = acosl(-1.0L);

    // Distributions
    std::uniform_int_distribution<int> tDist(-T, T);
    // Jitter up to roughly 45% of the spacing between consecutive base angles
    long double baseSpacing = PI / max(1, k);
    long double jitterAmp = baseSpacing * 0.45L;
    std::uniform_real_distribution<long double> jitterDist(-jitterAmp, jitterAmp);

    for (int i = 0; i < k; ++i) {
        long double baseTheta = (long double)i * PI / (long double)k;
        long double theta = baseTheta + jitterDist(rng);
        // Normalize theta to [0, PI)
        while (theta < 0) theta += PI;
        while (theta >= PI) theta -= PI;

        long double c = cosl(theta);
        long double s = sinl(theta);

        // Normal and direction vectors
        long double nx = c, ny = s;
        long double vx = -s, vy = c;

        int t = tDist(rng);

        long long bx = llround(nx * (long double)t);
        long long by = llround(ny * (long double)t);
        long long dx = llround(vx * (long double)L);
        long long dy = llround(vy * (long double)L);

        long long x1 = bx + dx;
        long long y1 = by + dy;
        long long x2 = bx - dx;
        long long y2 = by - dy;

        // Ensure points are within bounds just in case (should usually be fine with chosen L and t)
        x1 = max(-LIM, min(LIM, x1));
        y1 = max(-LIM, min(LIM, y1));
        x2 = max(-LIM, min(LIM, x2));
        y2 = max(-LIM, min(LIM, y2));

        if (x1 == x2 && y1 == y2) {
            if (x1 < LIM) x1++;
            else x2--;
        }

        cout << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << '\n';
    }

    return 0;
}