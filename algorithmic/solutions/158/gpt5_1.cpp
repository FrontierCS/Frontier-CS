#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, K;
    if (!(cin >> N >> K)) return 0;
    vector<int> a(11);
    for (int i = 1; i <= 10; i++) cin >> a[i];
    const int R = 10000;
    vector<int> xs(N), ys(N);
    for (int i = 0; i < N; i++) {
        cin >> xs[i] >> ys[i];
    }

    // Mark used integer x and y coordinates (within [-R, R])
    const int OFFSET = R;
    vector<char> usedX(2*R + 1, 0), usedY(2*R + 1, 0);
    for (int i = 0; i < N; i++) {
        int x = xs[i], y = ys[i];
        if (-R <= x && x <= R) usedX[x + OFFSET] = 1;
        if (-R <= y && y <= R) usedY[y + OFFSET] = 1;
    }

    auto buildFree = [&](const vector<char>& used)->vector<int>{
        vector<int> freeVals;
        freeVals.reserve(2*R+1);
        for (int c = -R + 1; c <= R - 1; c++) {
            if (!used[c + OFFSET]) freeVals.push_back(c);
        }
        return freeVals;
    };

    vector<int> freeX = buildFree(usedX);
    vector<int> freeY = buildFree(usedY);

    // Choose target mean occupancy
    double target_mu = 2.0; // average strawberries per piece
    long long Mtarget = (long long)llround((double)N / target_mu);
    if (Mtarget < 1) Mtarget = 1;

    int Mx = (int)freeX.size();
    int My = (int)freeY.size();

    // Determine v, h (number of vertical and horizontal lines)
    // Want (v+1)*(h+1) close to Mtarget with v + h <= K
    int best_v = 0, best_h = 0;
    long long best_diff = (1LL<<62);
    for (int v = 0; v <= K; v++) {
        if (v > Mx) break; // cannot place more vertical lines than free positions
        int hmax = min(K - v, My);
        if (hmax < 0) continue;
        // desired h around Mtarget/(v+1) - 1
        double desired_h_d = (double)Mtarget / (double)(v + 1) - 1.0;
        int h_candidates[3];
        h_candidates[0] = max(0, min(hmax, (int)floor(desired_h_d)));
        h_candidates[1] = max(0, min(hmax, (int)llround(desired_h_d)));
        h_candidates[2] = max(0, min(hmax, (int)ceil(desired_h_d)));
        for (int t = 0; t < 3; t++) {
            int h = h_candidates[t];
            long long M = 1LL * (v + 1) * (h + 1);
            long long diff = llabs(M - Mtarget);
            if (diff < best_diff) {
                best_diff = diff;
                best_v = v;
                best_h = h;
            }
        }
    }

    // Clamp if free positions are insufficient
    best_v = min(best_v, Mx);
    best_h = min(best_h, My);

    auto chooseCuts = [&](const vector<int>& freeVals, int m)->vector<int>{
        vector<int> res;
        int M = (int)freeVals.size();
        if (m <= 0 || M == 0) return res;
        m = min(m, M);
        res.reserve(m);
        // pick m quantiles from freeVals
        for (int j = 1; j <= m; j++) {
            long long rank = 1LL * j * (M + 1) / (m + 1);
            int idx = (int)rank - 1;
            if (idx < 0) idx = 0;
            if (idx >= M) idx = M - 1;
            res.push_back(freeVals[idx]);
        }
        // Ensure uniqueness in case of rounding collisions
        sort(res.begin(), res.end());
        res.erase(unique(res.begin(), res.end()), res.end());
        // If we lost some due to duplicates, fill remaining by spreading
        int need = m - (int)res.size();
        if (need > 0) {
            // Use more fine-grained ranks
            for (int j = 1; j <= M && need > 0; j += max(1, M / (need + 1))) {
                int val = freeVals[j - 1];
                if (!binary_search(res.begin(), res.end(), val)) {
                    res.push_back(val);
                    need--;
                }
            }
            sort(res.begin(), res.end());
        }
        if ((int)res.size() > m) res.resize(m);
        return res;
    };

    vector<int> cutsX = chooseCuts(freeX, best_v);
    vector<int> cutsY = chooseCuts(freeY, best_h);

    struct Line { long long px, py, qx, qy; };
    vector<Line> lines;
    lines.reserve(cutsX.size() + cutsY.size());

    const long long BIG = 1000000000LL;

    for (int c : cutsX) {
        lines.push_back({(long long)c, -BIG, (long long)c, BIG});
    }
    for (int c : cutsY) {
        lines.push_back({-BIG, (long long)c, BIG, (long long)c});
    }

    cout << (int)lines.size() << "\n";
    for (auto &ln : lines) {
        cout << ln.px << " " << ln.py << " " << ln.qx << " " << ln.qy << "\n";
    }
    return 0;
}