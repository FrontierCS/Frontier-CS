#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) return 0;
    vector<int> a(11);
    vector<int> targets;
    for (int d = 1; d <= 10; d++) {
        cin >> a[d];
        for (int i = 0; i < a[d]; i++) targets.push_back(d);
    }
    vector<pair<long long,long long>> pts(N);
    for (int i = 0; i < N; i++) {
        cin >> pts[i].first >> pts[i].second;
    }

    // Compute angles
    const long double PI = acosl(-1.0L);
    vector<pair<long double,int>> ang(N);
    for (int i = 0; i < N; i++) {
        long double th = atan2l((long double)pts[i].second, (long double)pts[i].first);
        if (th < 0) th += 2*PI;
        ang[i] = {th, i};
    }
    sort(ang.begin(), ang.end());

    // Find largest gap to start after it
    int sIndex = 0;
    if (N > 0) {
        long double maxGap = -1;
        for (int i = 0; i < N; i++) {
            long double a1 = ang[i].first;
            long double a2 = ang[(i+1)%N].first;
            long double gap = (i+1 < N) ? (a2 - a1) : (ang[0].first + 2*PI - a1);
            if (gap > maxGap) {
                maxGap = gap;
                sIndex = (i + 1) % N;
            }
        }
    }

    // Number of lines to use
    int L = min(K, (int)targets.size() + 1); // up to K, need +1 for leftover segment
    L = min(L, N == 0 ? 0 : N); // avoid placing more lines than points (optional safety)
    if (N == 0 || L <= 0) {
        cout << 0 << "\n";
        return 0;
    }

    vector<int> segSizes(L, 1);
    long long used = 0;
    for (int i = 0; i < L - 1; i++) {
        segSizes[i] = targets[i];
        used += segSizes[i];
    }
    segSizes[L - 1] = max<long long>(1, (long long)N - used); // ensure positive; there are enough points in this problem

    vector<array<long long,4>> lines;
    lines.reserve(L);

    long long M = 1000000000LL;
    long long pos = sIndex;
    for (int j = 0; j < L; j++) {
        int left = (int)((pos - 1 + N) % N);
        int right = (int)(pos % N);
        long double aL = ang[left].first;
        long double aR = ang[right].first;
        if (aR < aL) aR += 2*PI;
        long double phi = (aL + aR) / 2.0L;
        if (phi >= 2*PI) phi -= 2*PI;

        long double cx = cosl(phi);
        long double sy = sinl(phi);
        long long qx = llround(cx * (long double)M);
        long long qy = llround(sy * (long double)M);
        if (qx == 0 && qy == 0) qx = 1; // ensure distinct from (0,0)

        lines.push_back({0LL, 0LL, qx, qy});

        if (j < L - 1) {
            pos = (pos + segSizes[j]) % N;
        }
    }

    cout << (int)lines.size() << "\n";
    for (auto &ln : lines) {
        cout << ln[0] << " " << ln[1] << " " << ln[2] << " " << ln[3] << "\n";
    }
    return 0;
}