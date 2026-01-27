#include <bits/stdc++.h>
using namespace std;

struct P3i {
    int x, y, z;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    // Generate FCC lattice candidates: points (i,j,k) with i+j+k even, inside sphere of radius R
    auto generateCandidates = [](int R) {
        vector<P3i> pts;
        int R2 = R * R;
        for (int i = -R; i <= R; ++i) {
            int i2 = i * i;
            for (int j = -R; j <= R; ++j) {
                int j2 = j * j;
                int rem2 = R2 - i2 - j2;
                if (rem2 < 0) continue;
                int kMax = (int)floor(sqrt((double)rem2) + 1e-12);
                for (int k = -kMax; k <= kMax; ++k) {
                    if (((i + j + k) & 1) == 0) {
                        pts.push_back({i, j, k});
                    }
                }
            }
        }
        return pts;
    };

    int R = 0;
    vector<P3i> candidates;
    while (true) {
        candidates = generateCandidates(R);
        if ((int)candidates.size() >= n) break;
        ++R;
    }

    int m = (int)candidates.size();

    // Farthest point sampling on integer lattice (distance squared, unscaled)
    vector<char> picked(m, false);
    vector<int> selected;
    selected.reserve(n);
    vector<int> idx(m);
    for (int i = 0; i < m; ++i) idx[i] = i;

    auto sqr = [](long long v) { return v * v; };

    // pick first as farthest from origin (max norm)
    int id0 = -1;
    int bestD2 = -1;
    for (int i = 0; i < m; ++i) {
        int d2 = candidates[i].x * candidates[i].x + candidates[i].y * candidates[i].y + candidates[i].z * candidates[i].z;
        if (d2 > bestD2) {
            bestD2 = d2;
            id0 = i;
        }
    }
    picked[id0] = true;
    selected.push_back(id0);

    vector<int> mind2(m, INT_MAX);
    // initialize mind2 with distances to first point
    {
        const auto &p = candidates[id0];
        for (int j = 0; j < m; ++j) if (!picked[j]) {
            long long dx = candidates[j].x - p.x;
            long long dy = candidates[j].y - p.y;
            long long dz = candidates[j].z - p.z;
            int d2 = (int)(dx*dx + dy*dy + dz*dz);
            mind2[j] = d2;
        }
    }

    while ((int)selected.size() < n) {
        // find not picked point with maximum mind2
        int next = -1;
        int best = -1;
        for (int j = 0; j < m; ++j) if (!picked[j]) {
            if (mind2[j] > best) {
                best = mind2[j];
                next = j;
            }
        }
        if (next == -1) break; // shouldn't happen
        picked[next] = true;
        selected.push_back(next);

        const auto &p = candidates[next];
        for (int j = 0; j < m; ++j) if (!picked[j]) {
            long long dx = candidates[j].x - p.x;
            long long dy = candidates[j].y - p.y;
            long long dz = candidates[j].z - p.z;
            int d2 = (int)(dx*dx + dy*dy + dz*dz);
            if (d2 < mind2[j]) mind2[j] = d2;
        }
    }

    // Scale by the maximum radius among selected points to fit exactly in the unit sphere
    int maxNorm2 = 0;
    for (int idxSel : selected) {
        const auto &p = candidates[idxSel];
        int d2 = p.x * p.x + p.y * p.y + p.z * p.z;
        if (d2 > maxNorm2) maxNorm2 = d2;
    }
    double scale = 1.0 / sqrt((double)maxNorm2);

    vector<array<double,3>> pts;
    pts.reserve(n);
    for (int idxSel : selected) {
        const auto &p = candidates[idxSel];
        double x = p.x * scale;
        double y = p.y * scale;
        double z = p.z * scale;
        if (fabs(x) < 1e-15) x = 0.0;
        if (fabs(y) < 1e-15) y = 0.0;
        if (fabs(z) < 1e-15) z = 0.0;
        pts.push_back({x, y, z});
    }

    // Compute actual minimum pairwise distance on the produced (scaled) points
    double minD2 = 1e300;
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            double dx = pts[i][0] - pts[j][0];
            double dy = pts[i][1] - pts[j][1];
            double dz = pts[i][2] - pts[j][2];
            double d2 = dx*dx + dy*dy + dz*dz;
            if (d2 < minD2) minD2 = d2;
        }
    }
    double minDist = sqrt(minD2);

    cout.setf(std::ios::fixed);
    cout << setprecision(12) << minDist << "\n";
    for (int i = 0; i < n; ++i) {
        cout << setprecision(12) << pts[i][0] << " " << pts[i][1] << " " << pts[i][2] << "\n";
    }

    return 0;
}