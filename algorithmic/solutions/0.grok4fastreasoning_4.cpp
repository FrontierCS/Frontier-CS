#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<vector<pair<int, int>>> polys(n);
    long long total_area = 0;
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        polys[i].resize(k);
        for (int j = 0; j < k; j++) {
            cin >> polys[i][j].first >> polys[i][j].second;
        }
        total_area += k;
    }
    int S_min = 0;
    while (1LL * S_min * S_min < total_area) S_min++;
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    vector<int> chosen_X(n), chosen_Y(n), chosen_R(n), chosen_F(n);
    int final_S = -1;
    const int MAX_EXTRA = 100;
    bool found = false;
    for (int extra = 0; extra <= MAX_EXTRA && !found; extra++) {
        int S = S_min + extra;
        vector<bitset<1024>> empty_rows(S);
        for (int i = 0; i < S; i++) empty_rows[i].set();
        // sort idx by decreasing k
        sort(idx.begin(), idx.end(), [&](int a, int b) {
            return (int)polys[a].size() > (int)polys[b].size();
        });
        bool success = true;
        for (int ii = 0; ii < n; ii++) {
            int i = idx[ii];
            int k = polys[i].size();
            int best_py = INT_MAX;
            int best_px = INT_MAX;
            int best_f = -1, best_r = -1;
            int best_minx = 0, best_miny = 0;
            for (int f = 0; f < 2; f++) {
                for (int r = 0; r < 4; r++) {
                    // compute trans
                    vector<pair<int, int>> trans(k);
                    int min_tx = INT_MAX, min_ty = INT_MAX;
                    int max_tx = INT_MIN, max_ty = INT_MIN;
                    for (int j = 0; j < k; j++) {
                        int ox = polys[i][j].first;
                        int oy = polys[i][j].second;
                        int tx = ox, ty = oy;
                        if (f == 1) tx = -tx;
                        for (int rr = 0; rr < r; rr++) {
                            int ntx = ty;
                            int nty = -tx;
                            tx = ntx;
                            ty = nty;
                        }
                        trans[j] = {tx, ty};
                        min_tx = min(min_tx, tx);
                        min_ty = min(min_ty, ty);
                        max_tx = max(max_tx, tx);
                        max_ty = max(max_ty, ty);
                    }
                    int rel_w = max_tx - min_tx + 1;
                    int rel_h = max_ty - min_ty + 1;
                    if (rel_w > S || rel_h > S) continue;
                    vector<int> rel_dx(k), rel_dy(k);
                    for (int j = 0; j < k; j++) {
                        rel_dx[j] = trans[j].first - min_tx;
                        rel_dy[j] = trans[j].second - min_ty;
                    }
                    // now search for smallest py
                    bool orient_found = false;
                    for (int py = 0; py <= S - rel_h; py++) {
                        bitset<1024> feasible;
                        feasible.set();
                        bool can = true;
                        for (int j = 0; j < k; j++) {
                            int rr = py + rel_dy[j];
                            if (rr >= S) {
                                can = false;
                                break;
                            }
                            bitset<1024> temp = (empty_rows[rr] >> rel_dx[j]);
                            feasible &= temp;
                        }
                        if (!can) continue;
                        size_t pxx = feasible._Find_first();
                        if (pxx != bitset<1024>::npos && (int)pxx <= S - rel_w) {
                            int cand_py = py;
                            int cand_px = (int)pxx;
                            if (cand_py < best_py || (cand_py == best_py && cand_px < best_px)) {
                                best_py = cand_py;
                                best_px = cand_px;
                                best_f = f;
                                best_r = r;
                                best_minx = min_tx;
                                best_miny = min_ty;
                            }
                            orient_found = true;
                            break;  // smallest py for this orient
                        }
                    }
                }
            }
            if (best_py == INT_MAX) {
                success = false;
                break;
            }
            // now place using best_f, best_r, best_py, best_px, best_minx, best_miny
            int X = best_px - best_minx;
            int Y = best_py - best_miny;
            chosen_X[i] = X;
            chosen_Y[i] = Y;
            chosen_R[i] = best_r;
            chosen_F[i] = best_f;
            // mark the cells
            for (int j = 0; j < k; j++) {
                int ox = polys[i][j].first;
                int oy = polys[i][j].second;
                int tx = ox, ty = oy;
                if (best_f == 1) tx = -tx;
                for (int rr = 0; rr < best_r; rr++) {
                    int ntx = ty;
                    int nty = -tx;
                    tx = ntx;
                    ty = nty;
                }
                int fx = tx + X;
                int fy = ty + Y;
                empty_rows[fy].reset(fx);
            }
        }
        if (success) {
            final_S = S;
            found = true;
        }
    }
    // assume found
    cout << final_S << " " << final_S << "\n";
    for (int i = 0; i < n; i++) {
        cout << chosen_X[i] << " " << chosen_Y[i] << " " << chosen_R[i] << " " << chosen_F[i] << "\n";
    }
    return 0;
}