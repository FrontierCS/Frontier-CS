#include <bits/stdc++.h>
using namespace std;

static inline long long pack(int x, int y) {
    return ( (long long)x << 20 ) | (long long)y;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<pair<int,int>> mac(N), sar(N);
    unordered_set<long long> setM, setS, setAll;
    setM.reserve(N * 2);
    setS.reserve(N * 2);
    setAll.reserve(N * 4);
    setM.max_load_factor(0.7);
    setS.max_load_factor(0.7);
    setAll.max_load_factor(0.7);

    for (int i = 0; i < N; ++i) {
        int x, y; cin >> x >> y;
        mac[i] = {x, y};
        long long k = pack(x, y);
        setM.insert(k);
        setAll.insert(k);
    }
    for (int i = 0; i < N; ++i) {
        int x, y; cin >> x >> y;
        sar[i] = {x, y};
        long long k = pack(x, y);
        setS.insert(k);
        setAll.insert(k);
    }

    int bestVal = INT_MIN;
    int bx0 = 0, by0 = 0, bx1 = 1, by1 = 1;

    // Try 1x1 rectangles anchored at each mackerel point (four orientations)
    for (int i = 0; i < N; ++i) {
        int x = mac[i].first;
        int y = mac[i].second;
        for (int j = 0; j < 4; ++j) {
            int x0 = (j == 0 || j == 2) ? x : x - 1;
            int y0 = (j == 0 || j == 1) ? y : y - 1;
            int x1 = x0 + 1;
            int y1 = y0 + 1;
            if (x0 < 0 || y0 < 0 || x1 > 100000 || y1 > 100000) continue;

            int xs[4] = {x0, x1, x1, x0};
            int ys[4] = {y0, y0, y1, y1};
            int cm = 0, cs = 0;
            for (int k = 0; k < 4; ++k) {
                long long kk = pack(xs[k], ys[k]);
                if (setM.find(kk) != setM.end()) cm++;
                if (setS.find(kk) != setS.end()) cs++;
            }
            int val = cm - cs;
            if (val > bestVal) {
                bestVal = val;
                bx0 = x0; by0 = y0; bx1 = x1; by1 = y1;
            }
        }
    }

    // If no positive rectangle found, find an empty 1x1 cell with no points on the four corners
    if (bestVal <= 0) {
        bool found = false;
        for (int y = 0; y <= 1000 && !found; ++y) {
            for (int x = 0; x <= 1000 && !found; ++x) {
                if (x + 1 > 100000 || y + 1 > 100000) continue;
                long long k1 = pack(x, y);
                long long k2 = pack(x + 1, y);
                long long k3 = pack(x + 1, y + 1);
                long long k4 = pack(x, y + 1);
                if (setAll.find(k1) == setAll.end() &&
                    setAll.find(k2) == setAll.end() &&
                    setAll.find(k3) == setAll.end() &&
                    setAll.find(k4) == setAll.end()) {
                    bx0 = x; by0 = y; bx1 = x + 1; by1 = y + 1;
                    found = true;
                }
            }
        }
        if (!found) {
            // As an extremely unlikely fallback, scan a sparser grid
            for (int y = 0; y <= 100000 - 1 && !found; y += 137) {
                for (int x = 0; x <= 100000 - 1 && !found; x += 139) {
                    if (x + 1 > 100000 || y + 1 > 100000) continue;
                    long long k1 = pack(x, y);
                    long long k2 = pack(x + 1, y);
                    long long k3 = pack(x + 1, y + 1);
                    long long k4 = pack(x, y + 1);
                    if (setAll.find(k1) == setAll.end() &&
                        setAll.find(k2) == setAll.end() &&
                        setAll.find(k3) == setAll.end() &&
                        setAll.find(k4) == setAll.end()) {
                        bx0 = x; by0 = y; bx1 = x + 1; by1 = y + 1;
                        found = true;
                    }
                }
            }
            // If still not found (virtually impossible), just place at (0,0) ensuring inside bounds
            if (!found) {
                bx0 = 0; by0 = 0; bx1 = 1; by1 = 1;
            }
        }
    }

    cout << 4 << '\n';
    cout << bx0 << ' ' << by0 << '\n';
    cout << bx1 << ' ' << by0 << '\n';
    cout << bx1 << ' ' << by1 << '\n';
    cout << bx0 << ' ' << by1 << '\n';
    return 0;
}